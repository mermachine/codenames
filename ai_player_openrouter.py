"""
AI Player for Codenames using OpenRouter API
Supports multiple model providers (Claude, GPT, Llama, etc.)
"""

import os
import json
import re
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from codenames_core import CodenamesGame, Team, Clue

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class AIPlayer:
    model: str  # OpenRouter model string like "anthropic/claude-3.5-sonnet"
    name: str   # Display name like "Claude Sonnet 3.6"
    api_key: Optional[str] = None
    temperature: float = 0.7
    provider: str = "openrouter"  # Can be "openrouter" or "anthropic"

    def __post_init__(self):
        if self.provider == "openrouter":
            self.api_key = self.api_key or os.getenv("OPENROUTER_API_KEY")
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            # Fallback to Anthropic for testing
            self.api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")

        # Conversation memory for persistent context
        self.conversation_history = [
            {
                "role": "system",
                "content": f"You are {self.name}, an AI playing Codenames. Maintain a consistent personality throughout the game. Learn from your successes and mistakes. Be authentic in your reactions and strategic thinking."
            }
        ]

        self.personality_traits = {
            "clues_given": [],
            "reasoning_style": [],
            "risk_level": [],
            "recovery_attempts": []
        }

    def _make_api_call(self, user_message: str) -> str:
        """Make API call with conversation history"""

        # Limit conversation history to prevent token overflow
        MAX_HISTORY = 10  # Keep last 10 messages + system prompt
        if len(self.conversation_history) > MAX_HISTORY + 1:
            # Keep system prompt (first message) + last N messages
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-(MAX_HISTORY):]

        # Add user message to conversation
        self.conversation_history.append({"role": "user", "content": user_message})

        if self.provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/delight-nexus/codenames",  # Optional
                "X-Title": "Codenames Delight Nexus"  # Optional
            }

            data = {
                "model": self.model,
                "messages": self.conversation_history,
                "temperature": self.temperature,
                "max_tokens": 500
            }

            response = requests.post(self.base_url, json=data, headers=headers)

            if response.status_code == 200:
                assistant_response = response.json()['choices'][0]['message']['content']
                # Add assistant response to conversation history
                self.conversation_history.append({"role": "assistant", "content": assistant_response})
                return assistant_response
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
        else:
            # Use Anthropic SDK as fallback
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=self.temperature,
                messages=self.conversation_history
            )
            assistant_response = response.content[0].text
            # Add assistant response to conversation history
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            return assistant_response

    def generate_clue(self, game: CodenamesGame, team: Team) -> Tuple[Clue, str]:
        """Generate a clue as spymaster"""

        # Get the board state
        my_words = game.get_remaining_words(team)
        opponent_team = Team.BLUE if team == Team.RED else Team.RED
        opponent_words = game.get_remaining_words(opponent_team)
        neutral_words = game.get_remaining_words(Team.NEUTRAL)
        assassin_word = game.get_remaining_words(Team.ASSASSIN)

        # Build contextual game state message
        board_display = "\n".join([" | ".join(row) for row in game.get_board_display(spymaster=True)])

        context_message = f"""**TURN: Generate clue as spymaster**

Current board (S=spymaster view):
{board_display}

Your team's remaining words: {', '.join(my_words)}
Opponent's remaining words: {', '.join(opponent_words)}
Neutral words remaining: {', '.join(neutral_words)}
Assassin word: {assassin_word[0] if assassin_word else 'None'}

Score: Your team has {len(my_words)} words left, opponent has {len(opponent_words)} left.

Generate a one-word clue and number. Consider your previous strategies and what's worked before.

Respond in JSON format:
{{
    "clue_word": "your_clue",
    "number": 2,
    "target_words": ["word1", "word2"],
    "reasoning": "Explain your thought process and why this clue connects these words",
    "risk_assessment": "What could go wrong with this clue?",
    "confidence": 7  // 1-10 scale
}}"""

        response_text = self._make_api_call(context_message)

        # Parse response
        try:
            # Try to find JSON in the response (might be wrapped in markdown)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)

            clue = Clue(
                word=result["clue_word"],
                number=result["number"],
                reasoning=result["reasoning"]
            )

            # Track personality
            self.personality_traits["clues_given"].append(result["clue_word"])
            self.personality_traits["risk_level"].append(result.get("confidence", 5))

            full_reasoning = f"Targeting: {', '.join(result['target_words'])}\n"
            full_reasoning += f"Reasoning: {result['reasoning']}\n"
            full_reasoning += f"Risk: {result['risk_assessment']}\n"
            full_reasoning += f"Confidence: {result['confidence']}/10"

            return clue, full_reasoning

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to simple clue
            clue = Clue(word="CONNECT", number=1, reasoning="Error parsing response")
            return clue, f"Error: {str(e)}"

    def make_guess(self, game: CodenamesGame, clue: Clue, team: Team) -> Tuple[List[str], str]:
        """Make guesses as operative based on spymaster's clue"""

        # Get available words to guess from
        unrevealed_words = [w.text for w in game.board if not w.revealed]

        # Build contextual game state for guessing
        board_display = "\n".join([" | ".join(row) for row in game.get_board_display(spymaster=False)])

        context_message = f"""**TURN: Make guesses as operative**

Current board (operative view):
{board_display}

Your spymaster's clue: "{clue.word}" for {clue.number} word(s)

Unrevealed words: {', '.join(unrevealed_words)}

You can guess up to {clue.number + 1} words total. Think about your spymaster's style and what connections they might be making based on your previous interactions.

Respond in JSON format:
{{
    "guesses": ["word1", "word2"],  // In order of confidence
    "reasoning": "Explain why you think these words connect to the clue",
    "confidence_scores": {{"word1": 9, "word2": 7}},  // 1-10 for each guess
    "considered_but_rejected": ["word3", "word4"],  // Other words you considered
    "interpretation": "What you think the spymaster meant"
}}"""

        response_text = self._make_api_call(context_message)

        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)

            guesses = result["guesses"][:clue.number + 1]  # Limit to allowed number

            reasoning = f"Interpretation: {result['interpretation']}\n"
            reasoning += f"Reasoning: {result['reasoning']}\n"
            reasoning += f"Confidence: {', '.join([f'{w}:{result["confidence_scores"].get(w, "?")}' for w in guesses])}\n"
            reasoning += f"Also considered: {', '.join(result.get('considered_but_rejected', []))}"

            return guesses, reasoning

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to first unrevealed word
            return [unrevealed_words[0]] if unrevealed_words else [], f"Error: {str(e)}"

    def react_to_outcome(self, outcome_description: str) -> str:
        """Generate natural reaction to any game outcome with full context"""

        context_message = f"""**GAME OUTCOME**

{outcome_description}

React naturally to this situation in your characteristic style. Keep it conversational and under 40 words."""

        reaction = self._make_api_call(context_message)
        self.personality_traits["recovery_attempts"].append(reaction)  # Store all reactions for personality analysis
        return reaction

    def get_personality_summary(self) -> Dict:
        """Summarize the player's personality based on game history"""
        return {
            "name": self.name,
            "model": self.model,
            "total_clues": len(self.personality_traits["clues_given"]),
            "unique_clues": len(set(self.personality_traits["clues_given"])),
            "avg_risk_level": sum(self.personality_traits["risk_level"]) / len(self.personality_traits["risk_level"]) if self.personality_traits["risk_level"] else 0,
            "sample_recovery": self.personality_traits["recovery_attempts"][-1] if self.personality_traits["recovery_attempts"] else None
        }


# Model configurations for OpenRouter
MODEL_CONFIGS = {
    # Claude models
    "claude-sonnet-3.5": {
        "model": "anthropic/claude-3.5-sonnet",
        "name": "Claude Sonnet 3.5",
        "temperature": 0.7
    },
    "claude-opus": {
        "model": "anthropic/claude-3-opus",
        "name": "Claude Opus",
        "temperature": 0.8
    },
    "claude-haiku": {
        "model": "anthropic/claude-3-haiku",
        "name": "Claude Haiku",
        "temperature": 0.6
    },

    # OpenAI models
    "gpt-4": {
        "model": "openai/gpt-4-turbo-preview",
        "name": "GPT-4 Turbo",
        "temperature": 0.7
    },
    "gpt-3.5": {
        "model": "openai/gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "temperature": 0.7
    },

    # Open source models
    "llama-70b": {
        "model": "meta-llama/llama-3-70b-instruct",
        "name": "Llama 3 70B",
        "temperature": 0.7
    },
    "mixtral": {
        "model": "mistralai/mixtral-8x7b-instruct",
        "name": "Mixtral 8x7B",
        "temperature": 0.7
    },
    "qwen": {
        "model": "qwen/qwen-2-72b-instruct",
        "name": "Qwen 2 72B",
        "temperature": 0.7
    }
}

def create_player(model_key: str, provider: str = "openrouter") -> AIPlayer:
    """Factory function to create AI players"""
    config = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["claude-sonnet-3.5"])
    return AIPlayer(
        model=config["model"],
        name=config["name"],
        temperature=config["temperature"],
        provider=provider
    )

def create_spymaster(model_key: str, team_color: str, provider: str = "openrouter") -> AIPlayer:
    """Create an AI player specifically for spymaster role"""
    config = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["claude-sonnet-3.5"])
    player = AIPlayer(
        model=config["model"],
        name=f"{config['name']} ({team_color} Spymaster)",
        temperature=config["temperature"],
        provider=provider
    )
    # Override system prompt for spymaster
    player.conversation_history[0] = {
        "role": "system",
        "content": f"You are the {team_color} team spymaster in Codenames. You can see all words and their teams. Give strategic clues to help your operative guess your team's words while avoiding opponent words and the assassin. Be creative and strategic with your clues."
    }
    return player

def create_guesser(model_key: str, team_color: str, provider: str = "openrouter") -> AIPlayer:
    """Create an AI player specifically for guesser role"""
    config = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["claude-sonnet-3.5"])
    player = AIPlayer(
        model=config["model"],
        name=f"{config['name']} ({team_color} Guesser)",
        temperature=config["temperature"],
        provider=provider
    )
    # Override system prompt for guesser
    player.conversation_history[0] = {
        "role": "system",
        "content": f"You are the {team_color} team operative in Codenames. You cannot see which words belong to which team. Interpret your spymaster's clues to guess the correct words. Think carefully about word associations and be strategic with your guesses."
    }
    return player
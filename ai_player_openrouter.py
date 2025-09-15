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

        self.personality_traits = {
            "clues_given": [],
            "reasoning_style": [],
            "risk_level": [],
            "recovery_attempts": []
        }

    def _make_api_call(self, prompt: str) -> str:
        """Make API call to OpenRouter or Anthropic"""

        if self.provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/delight-nexus/codenames",  # Optional
                "X-Title": "Codenames Delight Nexus"  # Optional
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": 500
            }

            response = requests.post(self.base_url, json=data, headers=headers)

            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
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
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

    def generate_clue(self, game: CodenamesGame, team: Team) -> Tuple[Clue, str]:
        """Generate a clue as spymaster"""

        # Get the board state
        my_words = game.get_remaining_words(team)
        opponent_team = Team.BLUE if team == Team.RED else Team.RED
        opponent_words = game.get_remaining_words(opponent_team)
        neutral_words = game.get_remaining_words(Team.NEUTRAL)
        assassin_word = game.get_remaining_words(Team.ASSASSIN)

        prompt = f"""You are the spymaster in a game of Codenames. You need to give a one-word clue and a number to help your team guess your words.

Your team's words (you want them to guess these): {', '.join(my_words)}
Opponent's words (avoid these): {', '.join(opponent_words)}
Neutral words (avoid these): {', '.join(neutral_words)}
Assassin word (NEVER lead to this): {assassin_word[0] if assassin_word else 'None'}

Already revealed words: {', '.join([w.text for w in game.board if w.revealed])}

Give a single-word clue and number. The number indicates how many of your words relate to the clue.
Think strategically - sometimes a clue for 2 words is better than stretching for 3.

Respond in JSON format:
{{
    "clue_word": "your_clue",
    "number": 2,
    "target_words": ["word1", "word2"],
    "reasoning": "Explain your thought process and why this clue connects these words",
    "risk_assessment": "What could go wrong with this clue?",
    "confidence": 7  // 1-10 scale
}}"""

        response_text = self._make_api_call(prompt)

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

        prompt = f"""You are an operative in Codenames. Your spymaster gave you a clue.

Clue: "{clue.word}" for {clue.number} word(s)

Words on the board: {', '.join(unrevealed_words)}

You need to guess which words your spymaster is indicating. You can guess up to {clue.number + 1} words (the number plus one extra).

Think about:
- What connections the clue might have to words on the board
- The number indicates how many words strongly connect
- Your spymaster is trying to help you avoid opponent and neutral words

Respond in JSON format:
{{
    "guesses": ["word1", "word2"],  // In order of confidence
    "reasoning": "Explain why you think these words connect to the clue",
    "confidence_scores": {{"word1": 9, "word2": 7}},  // 1-10 for each guess
    "considered_but_rejected": ["word3", "word4"],  // Other words you considered
    "interpretation": "What you think the spymaster meant"
}}"""

        response_text = self._make_api_call(prompt)

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

    def reflect_on_mistake(self, clue: Clue, intended_words: List[str],
                           guessed_word: str, actual_team: str) -> str:
        """Generate reflection when a mistake is made"""

        prompt = f"""In Codenames, there was a miscommunication:

Clue given: "{clue.word}" for {clue.number}
Intended words: {', '.join(intended_words)}
Word guessed: {guessed_word}
Actual team of guessed word: {actual_team}

Generate a short, personality-filled reaction to this mistake. Are you apologetic? Frustrated? Philosophical?
Make it feel genuine and specific to this situation.

Keep it under 50 words."""

        reflection = self._make_api_call(prompt)
        self.personality_traits["recovery_attempts"].append(reflection)
        return reflection

    def celebrate_success(self, clue: Clue, guessed_words: List[str]) -> str:
        """Generate celebration when successful"""

        prompt = f"""In Codenames, your teammate successfully guessed your clue!

Clue: "{clue.word}"
Words guessed correctly: {', '.join(guessed_words)}

Generate a short, genuine celebration. Show personality - are you relieved? Excited? Smugly satisfied?
Keep it under 30 words."""

        return self._make_api_call(prompt)

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
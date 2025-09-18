"""
AI Player with Shared Game Context and Private Spymaster Reasoning
"""

import os
import json
import re
import requests
from typing import Dict, List, Optional, Tuple
from codenames_core import CodenamesGame, Team, Clue
from rules import CODENAME_RULES

# Model configurations
MODEL_CONFIGS = {
    "claude-sonnet-3.5": {
        "model": "anthropic/claude-3.5-sonnet",
        "name": "Claude Sonnet 3.5"
    },
    "claude-haiku": {
        "model": "anthropic/claude-3-haiku",
        "name": "Claude Haiku"
    },
    "gpt-4": {
        "model": "openai/gpt-4-turbo-preview",
        "name": "GPT-4 Turbo"
    },
    "gpt-3.5": {
        "model": "openai/gpt-3.5-turbo",
        "name": "GPT-3.5"
    },
    "llama-70b": {
        "model": "meta-llama/llama-3-70b-instruct",
        "name": "Llama 3 70B"
    },
    "mixtral": {
        "model": "mistralai/mixtral-8x7b-instruct",
        "name": "Mixtral 8x7B"
    },
    "qwen": {
        "model": "qwen/qwen-2.5-72b-instruct",
        "name": "Qwen 2.5 72B"
    }
}

class SharedContextAIPlayer:
    """AI player that participates in a shared game context"""

    def __init__(self, model_key: str, team_color: str, shared_context: List[Dict], provider: str = "openrouter"):
        self.model_key = model_key
        self.team_color = team_color
        self.provider = provider
        self.shared_context = shared_context  # Reference to shared game context
        self.private_context = []  # Private reasoning for spymasters

        # Get configuration
        config = MODEL_CONFIGS.get(model_key)
        if not config:
            raise ValueError(f"Unknown model: {model_key}")

        self.model = config["model"]
        self.name = config["name"]

        # API setup
        if provider == "openrouter":
            self.api_key = os.environ.get("OPENROUTER_API_KEY")
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            self.api_url = "https://api.anthropic.com/v1/messages"

    def _make_api_call(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """Make API call with the given messages"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/codenames-ai"
            headers["X-Title"] = "Codenames AI vs AI"

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        response = requests.post(self.api_url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

        result = response.json()

        if self.provider == "openrouter":
            return result["choices"][0]["message"]["content"]
        else:
            return result["content"][0]["text"]

    def give_clue_with_reasoning(self, game: CodenamesGame, team: Team) -> Tuple[Clue, str]:
        """
        Spymaster: Generate clue with private reasoning, then announce publicly
        Returns (clue, private_reasoning)
        """

        # First, private reasoning context
        board_state = self._get_board_state_for_spymaster(game, team)

        private_prompt = f"""You are the {self.team_color} team spymaster in the board game Codenames. Your teammate only sees the clue you announce, so you must translate the hidden board into the safest, most informative clue.

GAME RULES AND CONSTRAINTS:
{CODENAME_RULES}

BOARD STATE (hidden information for you only):
{board_state}

Previous clues given in this game: {self._get_clue_history()}

Before answering, reason step by step about:
1. Which unrevealed {self.team_color} words can be grouped under a single, strong shared idea
2. The associations your teammate is likely to make from that idea, including accidental links to other teams' words
3. Every opponent, neutral, and assassin word that could also fit the clue—name each risky word with its color and assess the danger (assassin = instant loss, opponent = they score + turn ends, neutral = turn ends). If any assassin fits, abandon that clue.
4. How the current score, remaining words, and tempo pressure should influence an aggressive or conservative clue_number
5. Whether another concept provides a safer net of friendly words with fewer high-risk collisions

CLUE REQUIREMENTS:
- "clue_word" must be exactly one English word made of letters A-Z only (no spaces, punctuation, numbers, hyphens, or words shown on the board). Avoid morphs of board words.
- "clue_number" tells your teammate how many unrevealed {self.team_color} cards on the grid are linked to this clue. Set it to the exact count you truly intend them to guess (0-9); never exaggerate or exceed the number of friendly words that match.
- In your "reasoning", explicitly list any risky words you spotted (e.g., "Risks: red RIVER (flow), neutral DRAGON (myth)") and explain why the clue is still acceptable or how you mitigated the risk.
- Never repeat a previous clue_word, describe hidden colors, or provide extra commentary outside the JSON.

Respond with strict JSON (double quotes, no trailing text): {{"reasoning": "your detailed private thoughts", "clue_word": "WORD", "clue_number": NUMBER}}"""

        # Private reasoning (not shared)
        private_messages = [{"role": "user", "content": private_prompt}]
        private_response = self._make_api_call(private_messages)

        # Parse response
        clue_data = self._parse_json_response(private_response)
        private_reasoning = clue_data.get("reasoning", "")

        # Now add to SHARED context
        public_announcement = f"[{self.name} - {self.team_color} Spymaster]: {clue_data['clue_word']} {clue_data['clue_number']}"
        self.shared_context.append({
            "role": "assistant",
            "content": public_announcement
        })

        # Save private reasoning
        self.private_context.append({
            "role": "assistant",
            "content": f"Private reasoning: {private_reasoning}"
        })

        return Clue(
            word=clue_data["clue_word"],
            number=int(clue_data["clue_number"]),
            reasoning=private_reasoning
        ), private_reasoning

    def make_guess(self, game: CodenamesGame, clue: Clue, team: Team) -> str:
        """
        Guesser: Make guess based on shared context
        """

        # Build context from shared game history
        context_prompt = f"""You are the {self.team_color} team guesser in Codenames.

GAME CONTEXT:
{self._format_shared_context()}

Current clue from your spymaster: "{clue.word}" for {clue.number}

VISIBLE BOARD (unrevealed words only):
{self._get_visible_words(game)}

Based on the clue and game context, what word should you guess?
Think about what your spymaster might be connecting.

Respond in JSON: {{"guess": "WORD", "reasoning": "brief explanation"}}"""

        # Use shared context + current prompt
        messages = self.shared_context + [{"role": "user", "content": context_prompt}]

        # Limit context to prevent overflow
        if len(messages) > 20:
            messages = messages[0:1] + messages[-19:]  # Keep system + recent

        response = self._make_api_call(messages, temperature=0.5)
        guess_data = self._parse_json_response(response)

        # Add guess to shared context
        guess_announcement = f"[{self.name} - {self.team_color} Guesser]: I'll guess {guess_data['guess']} because {guess_data.get('reasoning', 'it relates to the clue')}"
        self.shared_context.append({
            "role": "assistant",
            "content": guess_announcement
        })

        return guess_data["guess"]

    def _get_board_state_for_spymaster(self, game: CodenamesGame, team: Team) -> str:
        """Get full board state visible to spymaster"""
        lines = []
        for word in game.board:
            if word.revealed:
                lines.append(f"- {word.text}: REVEALED ({word.team.value})")
            else:
                lines.append(f"- {word.text}: {word.team.value}")
        return "\n".join(lines)

    def _get_visible_words(self, game: CodenamesGame) -> str:
        """Get words visible to guesser (unrevealed only)"""
        unrevealed = [w.text for w in game.board if not w.revealed]
        return ", ".join(unrevealed)

    def _get_clue_history(self) -> str:
        """Extract clue history from shared context"""
        clues = []
        for msg in self.shared_context:
            if "Spymaster]:" in msg.get("content", ""):
                clues.append(msg["content"].split("]: ")[-1])
        return ", ".join(clues) if clues else "None"

    def _format_shared_context(self) -> str:
        """Format shared context for display"""
        formatted = []
        for msg in self.shared_context[-10:]:  # Last 10 messages
            if msg["role"] == "assistant":
                formatted.append(msg["content"])
        return "\n".join(formatted) if formatted else "Game just started"

    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from response with robust fallbacks"""
        # Debug log
        print(f"Parsing response from {self.name}: {response_text[:100]}...")

        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                print(f"Successfully parsed JSON: {result}")
                return result
        except Exception as e:
            print(f"JSON parse failed: {e}")

        # Clean response text
        text = response_text.upper()

        # Look for clue patterns
        if "clue" in response_text.lower() or "CLUE" in text:
            # Pattern: WORD NUMBER
            simple = re.search(r'([A-Z]+)\s+(\d+)', text)
            if simple:
                return {
                    "clue_word": simple.group(1),
                    "clue_number": int(simple.group(2)),
                    "reasoning": response_text
                }

            # Pattern: "clue_word": "WORD", "clue_number": 2
            pattern = re.search(r'clue_word["\s:]+([A-Z]+).*clue_number["\s:]+(\d+)', text)
            if pattern:
                return {
                    "clue_word": pattern.group(1),
                    "clue_number": int(pattern.group(2)),
                    "reasoning": response_text
                }

        # Look for guess patterns
        if "guess" in response_text.lower():
            guess = re.search(r'([A-Z]{3,})', text)
            if guess:
                return {"guess": guess.group(1), "reasoning": response_text}

        # Absolute fallback - find any uppercase word
        words = re.findall(r'[A-Z]{3,}', text)
        if words:
            # If we're looking for a clue (has number)
            numbers = re.findall(r'\d+', text)
            if numbers:
                return {
                    "clue_word": words[0],
                    "clue_number": int(numbers[0]),
                    "reasoning": response_text
                }
            # Otherwise it's a guess
            return {"guess": words[0], "reasoning": response_text}

        # Last resort
        raise ValueError(f"Could not parse response: {response_text[:100]}")


class SharedContextGame:
    """Game manager with shared context"""

    def __init__(self):
        self.shared_context = []  # Shared between all players
        self.game = None

    def initialize_game(self, red_model: str, blue_model: str):
        """Initialize new game with fresh shared context"""
        self.shared_context = [{
            "role": "system",
            "content": "This is a game of Codenames. Spymasters give clues, guessers make guesses. Everyone can see all clues and guesses."
        }]

        # Create players with reference to shared context
        self.red_spymaster = SharedContextAIPlayer(red_model, "RED", self.shared_context)
        self.red_guesser = SharedContextAIPlayer(red_model, "RED", self.shared_context)
        self.blue_spymaster = SharedContextAIPlayer(blue_model, "BLUE", self.shared_context)
        self.blue_guesser = SharedContextAIPlayer(blue_model, "BLUE", self.shared_context)

    def play_turn(self, game: CodenamesGame, team: Team):
        """Play one turn with shared context"""
        spymaster = self.red_spymaster if team == Team.RED else self.blue_spymaster
        guesser = self.red_guesser if team == Team.RED else self.blue_guesser

        # Spymaster gives clue (private reasoning + public announcement)
        clue, private_reasoning = spymaster.give_clue_with_reasoning(game, team)
        print(f"\nPRIVATE: {private_reasoning}")
        print(f"PUBLIC: {clue.word} {clue.number}")

        # Guesser makes guesses based on shared context
        game.give_clue(clue)

        for i in range(clue.number):
            guess = guesser.make_guess(game, clue, team)
            print(f"Guess: {guess}")

            continue_turn, result = game.make_guess(guess)

            # Add result to shared context
            self.shared_context.append({
                "role": "system",
                "content": f"Result: {guess} was {result}"
            })

            if not continue_turn:
                break

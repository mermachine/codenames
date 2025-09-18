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

        missing_keys = [key for key in ("clue_word", "clue_number") if key not in clue_data]
        if missing_keys:
            raise ValueError(f"Missing {', '.join(missing_keys)} in spymaster response: {private_response}")

        clue_word = str(clue_data["clue_word"]).strip()
        if not clue_word:
            raise ValueError(f"Empty clue_word in spymaster response: {private_response}")

        try:
            clue_number = int(str(clue_data["clue_number"]).strip())
        except (ValueError, TypeError):
            raise ValueError(f"Invalid clue_number in spymaster response: {private_response}")

        clue_data["clue_word"] = clue_word
        clue_data["clue_number"] = clue_number
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

    def make_guess(self, game: CodenamesGame, clue: Clue, team: Team) -> Tuple[str, str]:
        """
        Guesser: Return the chosen board word and a chat-ready explanation
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

Before you answer, reason explicitly about:
1. The top {self.team_color} candidate words from the VISIBLE BOARD that relate to the clue and why they fit.
2. Every risky word (opponent, neutral, assassin) that shares the clue's idea—name each and explain the danger.
3. Confirm that your final choice appears exactly in the VISIBLE BOARD list (the clue itself is not automatically a board word).

Choose exactly one word from the VISIBLE BOARD and reproduce it verbatim.
If you realize you mentioned a word that is not in the VISIBLE BOARD, correct yourself before answering.

Respond in JSON: {{"guess": "WORD", "reasoning": "Concise summary of steps 1-3"}}"""

        print(f"Guesser visible board: {self._get_visible_words(game)}")

        # Use shared context + current prompt
        messages = self.shared_context + [{"role": "user", "content": context_prompt}]

        # Limit context to prevent overflow
        if len(messages) > 20:
            messages = messages[0:1] + messages[-19:]  # Keep system + recent

        response = self._make_api_call(messages, temperature=0.5)
        guess_data = self._parse_json_response(response)

        if "guess" not in guess_data or not str(guess_data["guess"]).strip():
            raise ValueError(f"Missing guess in model response: {response}")

        raw_guess = str(guess_data["guess"]).strip()
        normalized_guess = self._normalize_guess_word(raw_guess, game)

        reasoning = str(guess_data.get("reasoning", "")).strip()
        if not reasoning:
            reasoning = "it relates to the clue"

        guess_message = f"I'll guess {normalized_guess} because {reasoning}"

        return normalized_guess, guess_message

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

    def _normalize_guess_word(self, raw_guess: str, game: CodenamesGame) -> str:
        """Normalize model guess to match an unrevealed board word when possible"""
        if not raw_guess:
            return ""

        guess = raw_guess.strip()
        if not guess:
            return ""

        unrevealed_words = [w.text for w in game.board if not w.revealed]

        # Direct case-insensitive match
        for word in unrevealed_words:
            if word.lower() == guess.lower():
                return word

        # Strip non-letter characters and try again
        cleaned_guess = re.sub(r'[^a-z]', '', guess.lower())
        if cleaned_guess:
            for word in unrevealed_words:
                if re.sub(r'[^a-z]', '', word.lower()) == cleaned_guess:
                    return word

        raise ValueError(
            f"'{raw_guess}' is not in the visible board: {', '.join(unrevealed_words)}"
        )

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

                if isinstance(result, list):
                    result = result[0] if result else {}
                if not isinstance(result, dict):
                    result = {}

                normalized: Dict[str, object] = {}
                for key, value in result.items():
                    normalized_key = key.strip().lower().replace("-", "_")
                    normalized[normalized_key] = value

                if "clueword" in normalized and "clue_word" not in normalized:
                    normalized["clue_word"] = normalized["clueword"]
                if "cluenumber" in normalized and "clue_number" not in normalized:
                    normalized["clue_number"] = normalized["cluenumber"]
                if "clue" in normalized and "clue_word" not in normalized:
                    normalized["clue_word"] = normalized["clue"]
                if "number" in normalized and "clue_number" not in normalized:
                    normalized["clue_number"] = normalized["number"]

                if "clue_number" in normalized:
                    try:
                        normalized["clue_number"] = int(str(normalized["clue_number"]).strip())
                    except (ValueError, TypeError):
                        pass

                if "guess" in normalized and isinstance(normalized["guess"], str):
                    normalized["guess"] = normalized["guess"].strip()

                if "clue_word" in normalized and isinstance(normalized["clue_word"], str):
                    normalized["clue_word"] = normalized["clue_word"].strip()

                if "reasoning" in normalized and isinstance(normalized["reasoning"], str):
                    normalized["reasoning"] = normalized["reasoning"].strip()

                print(f"Successfully parsed JSON: {normalized}")
                return normalized
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
            attempts = 0
            guess_word = None
            guess_message = ""

            while attempts < 3 and guess_word is None:
                try:
                    guess_word, guess_message = guesser.make_guess(game, clue, team)
                except ValueError as err:
                    attempts += 1
                    warning = (
                        f"Invalid guess attempt ({attempts}/3): {err}. "
                        "Choose a word exactly from the visible board."
                    )
                    print(warning)
                    self.shared_context.append({
                        "role": "assistant",
                        "content": f"[System]: {warning}"
                    })
                    if attempts >= 3:
                        break

            if guess_word is None:
                print("Guesser failed to provide a valid board word. Turn ends.")
                self.shared_context.append({
                    "role": "assistant",
                    "content": "[System]: Guesser failed to provide a valid board word. Turn ends."
                })
                break

            print(f"Guess: {guess_message}")

            self.shared_context.append({
                "role": "assistant",
                "content": f"[{guesser.name} - {team.value.upper()} Guesser]: {guess_message}"
            })

            continue_turn, result = game.make_guess(guess_word)

            # Add result to shared context
            self.shared_context.append({
                "role": "system",
                "content": f"Result: {guess} was {result}"
            })

            if not continue_turn:
                break

"""
Game loop with shared context for WebSocket streaming
"""

import asyncio
import json
import os
from typing import Dict, List, Callable
from codenames_core import CodenamesGame, Team
from ai_player_shared_context import SharedContextAIPlayer, MODEL_CONFIGS
from words import DEFAULT_WORDS

class SharedContextGameLoop:
    """Game loop that manages shared context and WebSocket updates"""

    def __init__(self):
        self.shared_context = []
        self.chat_messages = []  # Frontend-formatted messages
        self.visualization_callbacks = []
        self.game = None
        self.players = {}
        self.total_games = 0

    def add_visualization_callback(self, callback: Callable):
        """Add callback for game state updates"""
        self.visualization_callbacks.append(callback)

    def notify_visualizers(self, state: Dict):
        """Send state update to all visualizers"""
        for callback in self.visualization_callbacks:
            try:
                callback(state)
            except Exception as e:
                print(f"Visualization error: {e}")

    def format_chat_message(self, speaker: str, team: str, message: str, is_private: bool = False) -> Dict:
        """Format message for frontend chat display"""
        return {
            "speaker": speaker,
            "team": team.upper() if team else "SYSTEM",
            "message": message,
            "isPrivate": is_private
        }

    def add_to_chat(self, speaker: str, team: str, message: str, is_private: bool = False):
        """Add message to chat history"""
        chat_msg = self.format_chat_message(speaker, team, message, is_private)
        self.chat_messages.append(chat_msg)

        # Also add to shared context if not private
        if not is_private:
            self.shared_context.append({
                "role": "assistant",
                "content": f"[{speaker}]: {message}"
            })

    async def initialize_game(self, red_model: str, blue_model: str):
        """Initialize new game with fresh shared context"""
        self.total_games += 1

        # Reset contexts
        self.shared_context = [{
            "role": "system",
            "content": "You are playing Codenames. Spymasters give clues, guessers interpret them. Everyone sees all public clues and guesses."
        }]
        self.chat_messages = []

        # Create new game
        self.game = CodenamesGame(DEFAULT_WORDS)

        # Create players with shared context reference
        self.players = {
            "red_spymaster": SharedContextAIPlayer(red_model, "RED", self.shared_context),
            "red_guesser": SharedContextAIPlayer(red_model, "RED", self.shared_context),
            "blue_spymaster": SharedContextAIPlayer(blue_model, "BLUE", self.shared_context),
            "blue_guesser": SharedContextAIPlayer(blue_model, "BLUE", self.shared_context)
        }

        # Announce game start
        self.add_to_chat("System", "SYSTEM", f"Game {self.total_games} starting!")
        self.add_to_chat("System", "SYSTEM",
                        f"Red Team: {MODEL_CONFIGS[red_model]['name']} vs Blue Team: {MODEL_CONFIGS[blue_model]['name']}")

        # Send initial state
        await self.send_game_state("STARTING")
        await asyncio.sleep(2)

    async def send_game_state(self, phase: str):
        """Send current game state via callbacks"""
        state = {
            "phase": phase,
            "total_games": self.total_games,
            "current_team": self.game.current_team.value if self.game.current_team else None,
            "board": [{"text": w.text, "team": w.team.value, "revealed": w.revealed} for w in self.game.board],
            "game_state": {
                "red_remaining": len([w for w in self.game.board if w.team == Team.RED and not w.revealed]),
                "blue_remaining": len([w for w in self.game.board if w.team == Team.BLUE and not w.revealed]),
                "turn_count": len(self.game.turn_history)
            },
            "red_team": self.players["red_spymaster"].name,
            "blue_team": self.players["blue_spymaster"].name,
            "shared_context": self.chat_messages,
            "last_action": self.chat_messages[-1]["message"] if self.chat_messages else "",
            "last_reasoning": ""
        }
        self.notify_visualizers(state)

    async def play_turn(self):
        """Play one complete turn"""
        team = self.game.current_team
        team_name = "RED" if team == Team.RED else "BLUE"

        spymaster = self.players[f"{team_name.lower()}_spymaster"]
        guesser = self.players[f"{team_name.lower()}_guesser"]

        try:
            # Phase: Thinking
            self.add_to_chat(f"{spymaster.name} (Spymaster)", team_name, "Let me analyze the board...")
            await self.send_game_state("THINKING")
            await asyncio.sleep(1)

            # Spymaster gives clue
            clue = spymaster.give_clue_with_reasoning(self.game, team)

            # Add private thoughts
            self.add_to_chat(f"{spymaster.name} (Spymaster)", team_name,
                           f"{clue.reasoning}; {clue.word}; {clue.number}", is_private=True)

            # Add public clue
            self.add_to_chat(f"{spymaster.name} (Spymaster)", team_name,
                           f"{clue.word} {clue.number}")
            self.game.give_clue(clue)

            self.add_to_chat(f"{guesser.name} (Guesser)", team_name, "Let me consider the clue...")
            await self.send_game_state("GUESSING")
            await asyncio.sleep(2)

            # Guessing phase
            for i in range(clue.number):
                attempts = 0
                guess_word = None
                guess_message = ""

                while attempts < 3 and guess_word is None:
                    try:
                        guess_word, guess_message = guesser.make_guess(self.game, clue, team)
                    except ValueError as err:
                        attempts += 1
                        warning = (
                            f"Invalid guess attempt ({attempts}/3): {err}. "
                            "Choose a word exactly from the visible board."
                        )
                        self.add_to_chat("System", "SYSTEM", warning)
                        await self.send_game_state("GUESSING")
                        await asyncio.sleep(1)
                        continue

                if guess_word is None:
                    self.add_to_chat(
                        "System",
                        "SYSTEM",
                        "Guesser failed to provide a valid board word. Turn ends."
                    )
                    break

                self.add_to_chat(f"{guesser.name} (Guesser)", team_name, guess_message)
                await self.send_game_state("GUESSING")
                await asyncio.sleep(1)

                continue_turn, result = self.game.make_guess(guess_word)

                # Announce result
                self.add_to_chat("System", "SYSTEM", result)

                await self.send_game_state("GUESSING")
                await asyncio.sleep(2)

                if not continue_turn:
                    break

                if self.game.game_over:
                    break

            # End turn
            self.game.end_turn()

        except Exception as e:
            print(f"Error during turn: {e}")
            self.add_to_chat("System", "SYSTEM", f"Error: {str(e)[:100]}")
            self.game.end_turn()

    async def play_game(self):
        """Play one complete game"""
        # Choose random models
        import random
        model_pairs = [
            ("claude-sonnet-3.5", "claude-haiku"),
            ("claude-haiku", "gpt-3.5"),
            ("gpt-3.5", "llama-70b"),
        ]
        red_model, blue_model = random.choice(model_pairs)

        await self.initialize_game(red_model, blue_model)

        # Play turns until game over
        turn_count = 0
        max_turns = 30

        while not self.game.game_over and turn_count < max_turns:
            await self.play_turn()
            turn_count += 1

            if self.game.game_over:
                break

        # Game over
        if self.game.winner:
            winner_name = self.players["red_spymaster"].name if self.game.winner == Team.RED else self.players["blue_spymaster"].name
            self.add_to_chat("System", "SYSTEM",
                           f"🎉 Game Over! {winner_name} ({self.game.winner.value}) wins!")
        else:
            self.add_to_chat("System", "SYSTEM", "Game ended (turn limit)")

        await self.send_game_state("ENDED")

        # Show final stats
        stats = self.game.get_game_state()
        self.add_to_chat("System", "SYSTEM",
                       f"Final: Red {9 - stats['red_remaining']}/9, Blue {8 - stats['blue_remaining']}/8")

        await self.send_game_state("ENDED")


async def test_shared_context_game():
    """Test the shared context game loop"""
    game_loop = SharedContextGameLoop()

    # Add debug callback
    def debug_callback(state):
        print(f"\nPhase: {state['phase']}")
        if state['shared_context']:
            latest = state['shared_context'][-1]
            print(f"Latest: [{latest['speaker']}] {latest['message'][:50]}...")

    game_loop.add_visualization_callback(debug_callback)

    # Run one game
    await game_loop.play_game()


if __name__ == "__main__":
    # Test with API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Set OPENROUTER_API_KEY to test with real AI")
    else:
        asyncio.run(test_shared_context_game())
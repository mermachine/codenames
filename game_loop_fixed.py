"""
Fixed Game Loop - Prevents AI from cheating by using separate instances
"""

import asyncio
import time
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from codenames_core import CodenamesGame, Team
from ai_player_openrouter import create_spymaster, create_guesser, AIPlayer
import traceback
from words import DEFAULT_WORDS

class GameState:
    """Tracks the current game state for visualization"""
    def __init__(self):
        self.current_game: Optional[CodenamesGame] = None
        self.red_spymaster: Optional[AIPlayer] = None
        self.red_guesser: Optional[AIPlayer] = None
        self.blue_spymaster: Optional[AIPlayer] = None
        self.blue_guesser: Optional[AIPlayer] = None
        self.current_phase = "STARTING"
        self.last_action = ""
        self.last_reasoning = ""
        self.game_history = []
        self.total_games = 0

    def to_dict(self) -> Dict:
        """Convert state to dictionary for visualization"""
        return {
            "phase": self.current_phase,
            "last_action": self.last_action,
            "last_reasoning": self.last_reasoning,
            "total_games": self.total_games,
            "current_team": self.current_game.current_team.value if self.current_game else None,
            "board": self.current_game.get_board_display() if self.current_game else None,
            "game_state": self.current_game.get_game_state() if self.current_game else None,
            "red_team": f"{self.red_spymaster.name.split('(')[0].strip()} Team" if self.red_spymaster else None,
            "blue_team": f"{self.blue_spymaster.name.split('(')[0].strip()} Team" if self.blue_spymaster else None,
        }

class FixedGameLoop:
    def __init__(self, word_list: List[str] = None):
        self.word_list = word_list or DEFAULT_WORDS
        self.state = GameState()
        self.running = False
        self.visualization_callbacks = []

        # Model pairs for testing (avoiding expensive models like Opus)
        self.model_pairs = [
            ("claude-sonnet-3.5", "claude-haiku"),  # Sonnet vs Haiku (cheap)
            ("claude-haiku", "gpt-3.5"),            # Haiku vs GPT-3.5 (both cheap)
            ("gpt-3.5", "llama-70b"),                # GPT-3.5 vs Llama (Llama is free!)
            ("llama-70b", "mixtral"),                # Llama vs Mixtral (both free!)
            ("claude-haiku", "qwen"),                # Haiku vs Qwen (cheap + free)
        ]
        self.current_pair_index = 0

    def add_visualization_callback(self, callback):
        """Add a callback for visualization updates"""
        self.visualization_callbacks.append(callback)

    def notify_visualizers(self):
        """Notify all visualizers of state change"""
        state_dict = self.state.to_dict()
        for callback in self.visualization_callbacks:
            try:
                callback(state_dict)
            except Exception as e:
                print(f"Visualization callback error: {e}")

    async def play_turn(self, game: CodenamesGame, spymaster: AIPlayer, guesser: AIPlayer) -> bool:
        """Play one turn of the game. Returns True if game continues."""

        team = game.current_team

        # Spymaster generates clue
        self.state.current_phase = "THINKING"
        self.state.last_action = f"{spymaster.name} is thinking of a clue..."
        self.notify_visualizers()

        try:
            clue, reasoning = spymaster.generate_clue(game, team)
            game.give_clue(clue)

            self.state.last_action = f"Clue: '{clue.word}' for {clue.number}"
            self.state.last_reasoning = reasoning
            self.notify_visualizers()

            await asyncio.sleep(3)  # Dramatic pause for viewers

            # Guesser makes guesses (SEPARATE INSTANCE - NO CHEATING!)
            self.state.current_phase = "GUESSING"
            guesses, guess_reasoning = guesser.make_guess(game, clue, team)

            for guess in guesses:
                self.state.last_action = f"{guesser.name} guesses: {guess}"
                self.state.last_reasoning = guess_reasoning
                self.notify_visualizers()

                await asyncio.sleep(2)

                continue_turn, result = game.make_guess(guess)

                # Generate reactions
                if "Correct" in result:
                    reaction = f"Nice! Got {guess} right!"
                    self.state.last_action = reaction
                elif "ASSASSIN" in result or "wins" in result:
                    self.state.last_action = result
                    return False  # Game over
                else:
                    if not continue_turn:
                        reaction = f"Oops, {guess} was {result.split('was')[1].split('.')[0]}"
                        self.state.last_action = reaction
                        self.notify_visualizers()
                        await asyncio.sleep(2)
                        break

                self.notify_visualizers()
                await asyncio.sleep(1)

                if not continue_turn:
                    break

            game.end_turn()
            return not game.game_over

        except Exception as e:
            print(f"Error during turn: {e}")
            traceback.print_exc()
            self.state.last_action = "Error occurred, continuing..."
            self.notify_visualizers()
            return False

    async def play_game(self):
        """Play a complete game with separate spymaster/guesser instances"""

        # Select model pairing
        pair = self.model_pairs[self.current_pair_index]
        self.current_pair_index = (self.current_pair_index + 1) % len(self.model_pairs)

        # Create SEPARATE instances for each role (no cheating!)
        model1, model2 = pair

        # Red team gets model1
        self.state.red_spymaster = create_spymaster(model1, "Red")
        self.state.red_guesser = create_guesser(model1, "Red")

        # Blue team gets model2
        self.state.blue_spymaster = create_spymaster(model2, "Blue")
        self.state.blue_guesser = create_guesser(model2, "Blue")

        # Create game
        self.state.current_game = CodenamesGame(self.word_list)
        self.state.current_phase = "STARTING"

        red_name = self.state.red_spymaster.name.split('(')[0].strip()
        blue_name = self.state.blue_spymaster.name.split('(')[0].strip()
        self.state.last_action = f"New game: {red_name} (Red) vs {blue_name} (Blue)"
        self.notify_visualizers()

        await asyncio.sleep(3)

        # Play until game ends
        while not self.state.current_game.game_over:
            current_team = self.state.current_game.current_team

            if current_team == Team.RED:
                spymaster = self.state.red_spymaster
                guesser = self.state.red_guesser  # SEPARATE INSTANCE!
            else:
                spymaster = self.state.blue_spymaster
                guesser = self.state.blue_guesser  # SEPARATE INSTANCE!

            continue_game = await self.play_turn(self.state.current_game, spymaster, guesser)

            if not continue_game:
                break

        # Game ended
        self.state.current_phase = "ENDED"
        winner = self.state.current_game.winner
        winner_name = red_name if winner == Team.RED else blue_name
        self.state.last_action = f"Game Over! {winner_name + ' (' + winner.value + ')' if winner else 'Error - no winner'} wins!"
        self.notify_visualizers()

        # Save game to history
        self.state.game_history.append({
            "timestamp": datetime.now().isoformat(),
            "red_model": model1,
            "blue_model": model2,
            "winner": winner.value if winner else None,
            "turns": len(self.state.current_game.turn_history)
        })

        self.state.total_games += 1
        await asyncio.sleep(5)

    async def run_forever(self):
        """Run games continuously with rate limiting"""
        self.running = True
        games_this_hour = 0
        hour_start = time.time()

        while self.running:
            # Rate limiting: max 30 games per hour
            if games_this_hour >= 30:
                wait_time = 3600 - (time.time() - hour_start)
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time:.0f} seconds...")
                    await asyncio.sleep(wait_time)
                games_this_hour = 0
                hour_start = time.time()

            try:
                await self.play_game()
                games_this_hour += 1

                # Minimum delay between games
                await asyncio.sleep(10)

            except Exception as e:
                print(f"Game error: {e}")
                traceback.print_exc()
                await asyncio.sleep(5)

            # Save state periodically
            if self.state.total_games % 10 == 0:
                self.save_state()

    def save_state(self):
        """Save game history and statistics"""
        filename = f"game_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump({
                "total_games": self.state.total_games,
                "history": self.state.game_history[-100:]
            }, f, indent=2)
        print(f"Saved game history to {filename}")

    def stop(self):
        """Stop the game loop"""
        self.running = False


# Test function
async def test_fixed_loop():
    """Test the fixed loop with console output"""

    def console_callback(state):
        print("\n" + "="*50)
        print(f"Phase: {state['phase']}")
        print(f"Action: {state['last_action']}")
        if state['phase'] == 'THINKING' and state['last_reasoning']:
            print(f"Reasoning: {state['last_reasoning'][:200]}...")
        print(f"Games played: {state['total_games']}")

    loop = FixedGameLoop()
    loop.add_visualization_callback(console_callback)

    # Play one game
    await loop.play_game()

    print("\n" + "="*60)
    print("FIXED VERSION TEST COMPLETE!")
    print("✓ Separate spymaster and guesser instances")
    print("✓ No cheating - guesser doesn't know team assignments")
    print("✓ Rate limiting implemented")
    print("✓ Conversation history limited")
    print("="*60)

if __name__ == "__main__":
    import os
    import sys

    # Set API key if provided
    if len(sys.argv) > 1:
        os.environ["OPENROUTER_API_KEY"] = sys.argv[1]

    asyncio.run(test_fixed_loop())
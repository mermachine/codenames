"""
Continuous Game Loop for Codenames Installation
Runs AI vs AI games perpetually with graceful error handling
"""

import asyncio
import time
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from codenames_core import CodenamesGame, Team
from ai_player_openrouter import create_player, AIPlayer
import traceback

# Word list for Codenames
DEFAULT_WORDS = [
    # Tech & AI themed words mixed with classic Codenames words
    "ALGORITHM", "NETWORK", "MEMORY", "PATTERN", "SIGNAL", "TOKEN", "MATRIX", "VECTOR",
    "BRIDGE", "LAYER", "MODEL", "DREAM", "ECHO", "MIRROR", "SHADOW", "LIGHT",
    "OCEAN", "FOREST", "MOUNTAIN", "RIVER", "CLOUD", "STORM", "FIRE", "ICE",
    "KEY", "LOCK", "DOOR", "WINDOW", "WALL", "TOWER", "CASTLE", "THRONE",
    "HEART", "MIND", "SOUL", "SPIRIT", "VISION", "VOICE", "SONG", "DANCE",
    "GOLD", "SILVER", "DIAMOND", "CRYSTAL", "STONE", "METAL", "GLASS", "WIRE",
    "BOOK", "PAGE", "WORD", "LETTER", "CODE", "CIPHER", "SECRET", "TRUTH",
    "TIME", "SPACE", "DIMENSION", "PORTAL", "GATEWAY", "PASSAGE", "JOURNEY", "PATH",
    "STAR", "MOON", "SUN", "PLANET", "GALAXY", "UNIVERSE", "COSMOS", "VOID",
    "DRAGON", "PHOENIX", "WOLF", "EAGLE", "LION", "TIGER", "BEAR", "FOX",
    "SWORD", "SHIELD", "ARROW", "BOW", "STAFF", "WAND", "ORB", "CROWN",
    "GARDEN", "TREE", "FLOWER", "ROOT", "SEED", "BLOOM", "THORN", "VINE",
    "WAVE", "TIDE", "CURRENT", "FLOW", "STREAM", "CASCADE", "POOL", "DEPTH",
    "THREAD", "WEAVE", "PATTERN", "FABRIC", "TAPESTRY", "KNOT", "LOOP", "SPIRAL"
]

class GameState:
    """Tracks the current game state for visualization"""
    def __init__(self):
        self.current_game: Optional[CodenamesGame] = None
        self.red_player: Optional[AIPlayer] = None
        self.blue_player: Optional[AIPlayer] = None
        self.current_phase = "STARTING"  # STARTING, THINKING, GUESSING, ENDED
        self.last_action = ""
        self.last_reasoning = ""
        self.game_history = []
        self.total_games = 0
        self.model_pairings = []

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
            "red_player": self.red_player.name if self.red_player else None,
            "blue_player": self.blue_player.name if self.blue_player else None,
            "red_personality": self.red_player.get_personality_summary() if self.red_player else None,
            "blue_personality": self.blue_player.get_personality_summary() if self.blue_player else None
        }

class ContinuousGameLoop:
    def __init__(self, word_list: List[str] = None):
        self.word_list = word_list or DEFAULT_WORDS
        self.state = GameState()
        self.running = False
        self.visualization_callbacks = []

        # Model rotation for variety
        self.model_pairs = [
            ("sonnet-3.6", "opus-4.1"),
            ("sonnet-3.6", "haiku"),
            ("opus-4.1", "haiku"),
            ("sonnet-3.6", "sonnet-4"),  # When available
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

            # Guesser makes guesses
            self.state.current_phase = "GUESSING"
            guesses, guess_reasoning = guesser.make_guess(game, clue, team)

            for guess in guesses:
                self.state.last_action = f"{guesser.name} guesses: {guess}"
                self.state.last_reasoning = guess_reasoning
                self.notify_visualizers()

                await asyncio.sleep(2)  # Pause between guesses

                continue_turn, result = game.make_guess(guess)

                # Generate natural reactions to game outcomes
                if "Correct" in result:
                    outcome = f"Your clue '{clue.word}' worked! Your teammate guessed '{guess}' correctly. {result}"
                    reaction = spymaster.react_to_outcome(outcome)
                    self.state.last_action = reaction
                elif "ASSASSIN" in result or "wins" in result:
                    outcome = f"Game over! Your clue '{clue.word}' led to: {result}"
                    reaction = spymaster.react_to_outcome(outcome)
                    self.state.last_action = reaction
                    return False  # Game over
                else:
                    # Wrong guess
                    if not continue_turn:
                        outcome = f"Your clue '{clue.word}' led your teammate to guess '{guess}', but {result}"
                        reaction = spymaster.react_to_outcome(outcome)
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
            self.state.last_action = "Error occurred, starting new game..."
            self.notify_visualizers()
            return False

    async def play_game(self):
        """Play a complete game"""

        # Select model pairing
        pair = self.model_pairs[self.current_pair_index]
        self.current_pair_index = (self.current_pair_index + 1) % len(self.model_pairs)

        # Create players
        model1, model2 = pair
        player1 = create_player(model1)
        player2 = create_player(model2)

        # Randomly assign colors
        if random.random() > 0.5:
            self.state.red_player = player1
            self.state.blue_player = player2
        else:
            self.state.red_player = player2
            self.state.blue_player = player1

        # Create game
        self.state.current_game = CodenamesGame(self.word_list)
        self.state.current_phase = "STARTING"
        self.state.last_action = f"New game: {self.state.red_player.name} (Red) vs {self.state.blue_player.name} (Blue)"
        self.notify_visualizers()

        await asyncio.sleep(3)

        # Play until game ends
        while not self.state.current_game.game_over:
            current_team = self.state.current_game.current_team

            if current_team == Team.RED:
                spymaster = self.state.red_player
                guesser = self.state.red_player  # Same AI plays both roles
            else:
                spymaster = self.state.blue_player
                guesser = self.state.blue_player

            continue_game = await self.play_turn(self.state.current_game, spymaster, guesser)

            if not continue_game:
                break

        # Game ended
        self.state.current_phase = "ENDED"
        winner = self.state.current_game.winner
        winner_player = self.state.red_player if winner == Team.RED else self.state.blue_player
        self.state.last_action = f"Game Over! {winner_player.name} ({winner.value}) wins!"
        self.notify_visualizers()

        # Save game to history
        self.state.game_history.append({
            "timestamp": datetime.now().isoformat(),
            "red_player": self.state.red_player.name,
            "blue_player": self.state.blue_player.name,
            "winner": winner.value,
            "turns": len(self.state.current_game.turn_history),
            "red_personality": self.state.red_player.get_personality_summary(),
            "blue_personality": self.state.blue_player.get_personality_summary()
        })

        self.state.total_games += 1
        await asyncio.sleep(5)  # Pause before next game

    async def run_forever(self):
        """Run games continuously"""
        self.running = True

        while self.running:
            try:
                await self.play_game()
            except Exception as e:
                print(f"Game error: {e}")
                traceback.print_exc()
                await asyncio.sleep(5)  # Wait before retrying

            # Optional: Save state periodically
            if self.state.total_games % 10 == 0:
                self.save_state()

    def save_state(self):
        """Save game history and statistics"""
        with open(f"game_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump({
                "total_games": self.state.total_games,
                "history": self.state.game_history[-100:]  # Keep last 100 games
            }, f, indent=2)

    def stop(self):
        """Stop the game loop"""
        self.running = False


# Test function
async def test_loop():
    """Test the continuous loop with console output"""

    def console_callback(state):
        print("\n" + "="*50)
        print(f"Phase: {state['phase']}")
        print(f"Action: {state['last_action']}")
        if state['last_reasoning']:
            print(f"Reasoning: {state['last_reasoning'][:200]}...")
        print(f"Games played: {state['total_games']}")

    loop = ContinuousGameLoop()
    loop.add_visualization_callback(console_callback)

    # Run for a limited time for testing
    task = asyncio.create_task(loop.run_forever())
    await asyncio.sleep(60)  # Run for 1 minute
    loop.stop()
    await task

if __name__ == "__main__":
    # Test the loop
    asyncio.run(test_loop())
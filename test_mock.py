"""
Test the game structure without API calls
"""

from codenames_core import CodenamesGame, Team, Clue

def test_game_logic():
    """Test basic game mechanics"""
    print("Testing Codenames game logic...")
    print("=" * 50)

    # Create a game
    words = ["APPLE", "BANK", "CARD", "DOOR", "EAGLE",
             "FIRE", "GOLD", "HEART", "ICE", "JUNGLE",
             "KEY", "LION", "MOON", "NIGHT", "OCEAN",
             "PAPER", "QUEEN", "RIVER", "STAR", "TREE",
             "UMBRELLA", "VOICE", "WATER", "XRAY", "YELLOW"]

    game = CodenamesGame(words, seed=42)

    # Display initial board
    print("\nInitial board (Spymaster view):")
    board = game.get_board_display(spymaster=True)
    for row in board:
        print(" | ".join(row))

    print(f"\nStarting team: {game.starting_team.value}")
    print(f"Red words: {len(game.get_remaining_words(Team.RED))}")
    print(f"Blue words: {len(game.get_remaining_words(Team.BLUE))}")

    # Simulate a turn
    print("\n" + "-" * 50)
    clue = Clue("NATURE", 2, "Connecting TREE and OCEAN")
    game.give_clue(clue)
    print(f"Clue given: {clue.word} for {clue.number}")

    # Make some guesses
    test_word = game.get_remaining_words(game.current_team)[0] if game.get_remaining_words(game.current_team) else "TREE"

    print(f"Guessing: {test_word}")
    continue_turn, result = game.make_guess(test_word)
    print(f"Result: {result}")

    # Check game state
    state = game.get_game_state()
    print(f"\nGame state after guess:")
    print(f"  Current team: {state['current_team']}")
    print(f"  Red remaining: {state['remaining_red']}")
    print(f"  Blue remaining: {state['remaining_blue']}")
    print(f"  Game over: {state['game_over']}")

    print("\n" + "=" * 50)
    print("Basic game logic test complete!")
    return True

if __name__ == "__main__":
    test_game_logic()
    print("\nTo test with real AI players, you need to:")
    print("1. Set your ANTHROPIC_API_KEY environment variable")
    print("2. Run: python test_game.py")
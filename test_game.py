"""
Test script for Codenames AI vs AI
Run this to see if the basic game loop works
"""

import asyncio
import os
from game_loop import ContinuousGameLoop

async def test_single_game():
    """Test just one game with detailed output"""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        print("You can set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return

    print("Starting Codenames AI vs AI test...")
    print("=" * 50)

    def detailed_callback(state):
        """Print detailed game state"""
        print(f"\n📍 Phase: {state['phase']}")
        print(f"🎮 Players: {state['red_player']} (Red) vs {state['blue_player']} (Blue)")
        print(f"💭 Action: {state['last_action']}")

        if state['last_reasoning'] and state['phase'] in ['THINKING', 'GUESSING']:
            print(f"🧠 Reasoning: {state['last_reasoning'][:300]}...")

        if state['game_state']:
            gs = state['game_state']
            print(f"📊 Score: Red {gs['remaining_red']} | Blue {gs['remaining_blue']}")

        print("-" * 40)

    # Create loop with callback
    loop = ContinuousGameLoop()
    loop.add_visualization_callback(detailed_callback)

    # Run just one game
    await loop.play_game()

    print("\n" + "=" * 50)
    print("Test complete!")
    print(f"Total games played: {loop.state.total_games}")

    # Show personality summaries if available
    if loop.state.red_player:
        print(f"\n{loop.state.red_player.name} personality:")
        print(loop.state.red_player.get_personality_summary())

    if loop.state.blue_player:
        print(f"\n{loop.state.blue_player.name} personality:")
        print(loop.state.blue_player.get_personality_summary())

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_single_game())
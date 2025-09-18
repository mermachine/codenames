import asyncio
import json
import websockets
import random

async def mock_game(websocket):
    """Send mock game states to frontend"""
    
    # Initial connection
    await websocket.send(json.dumps({
        "phase": "STARTING",
        "last_action": "Welcome to Codenames AI vs AI!",
        "last_reasoning": "",
        "total_games": 1,
        "current_team": "RED",
        "red_team": "Mock Claude (Red)",
        "blue_team": "Mock GPT (Blue)",
        "board": [
            ["ROBOT", "OCEAN", "MOON", "FIRE", "TREE"],
            ["STAR", "RIVER", "COMPUTER", "MOUNTAIN", "BOOK"],
            ["CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD"],
            ["FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE"],
            ["PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]
        ],
        "game_state": {}
    }))
    
    await asyncio.sleep(2)
    
    # Mock some turns
    for turn in range(5):
        team = "RED" if turn % 2 == 0 else "BLUE"
        
        # Thinking phase
        await websocket.send(json.dumps({
            "phase": "THINKING",
            "last_action": f"{team} spymaster is thinking...",
            "last_reasoning": "Analyzing the board for connections...",
            "current_team": team,
            "board": [
                ["ROBOT", "OCEAN", "MOON", "FIRE", "TREE"],
                ["STAR", "RIVER", "COMPUTER", "MOUNTAIN", "BOOK"],
                ["CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD"],
                ["FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE"],
                ["PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]
            ]
        }))
        await asyncio.sleep(2)
        
        # Give clue
        clues = ["TECH", "NATURE", "MYTH", "SPACE", "WATER"]
        clue = random.choice(clues)
        await websocket.send(json.dumps({
            "phase": "GUESSING",
            "last_action": f"Clue: {clue} for 2",
            "last_reasoning": f"I see connections with {clue}",
            "current_team": team,
            "board": [
                ["ROBOT", "OCEAN", "MOON", "FIRE", "TREE"],
                ["STAR", "RIVER", "COMPUTER", "MOUNTAIN", "BOOK"],
                ["CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD"],
                ["FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE"],
                ["PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]
            ]
        }))
        await asyncio.sleep(2)
        
        # Make guess
        words = ["ROBOT", "OCEAN", "STAR", "COMPUTER", "DRAGON"]
        word = random.choice(words)
        await websocket.send(json.dumps({
            "phase": "GUESSING", 
            "last_action": f"{team} guesses: {word}",
            "last_reasoning": f"{word} relates to {clue}",
            "current_team": team,
            "board": [
                [f"{word} [{team}]" if w == word else w for w in ["ROBOT", "OCEAN", "MOON", "FIRE", "TREE"]],
                ["STAR", "RIVER", "COMPUTER", "MOUNTAIN", "BOOK"],
                ["CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD"],
                ["FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE"],
                ["PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]
            ]
        }))
        await asyncio.sleep(2)
    
    # Game over
    await websocket.send(json.dumps({
        "phase": "ENDED",
        "last_action": "Game Over! RED team wins!",
        "last_reasoning": "Thanks for watching!",
        "current_team": "RED",
        "board": [
            ["ROBOT [RED]", "OCEAN", "MOON", "FIRE", "TREE"],
            ["STAR", "RIVER", "COMPUTER [RED]", "MOUNTAIN", "BOOK"],
            ["CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD"],
            ["FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE"],
            ["PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]
        ]
    }))

async def handle_client(websocket):
    """Handle a client connection"""
    print(f"Client connected")
    try:
        # Start mock game
        await mock_game(websocket)
        
        # Keep connection alive
        async for message in websocket:
            data = json.loads(message)
            if data.get("command") == "start":
                await mock_game(websocket)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        print("Connection closed")

async def main():
    print("Starting simple mock server on ws://localhost:8765")
    async with websockets.serve(handle_client, "localhost", 8765):
        print("Server ready! Open http://localhost:5173")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())

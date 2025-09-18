import asyncio
import json
import websockets
import random

async def mock_game_with_chat(websocket):
    """Send mock game states with chat history"""
    
    # Initialize chat
    chat_history = [
        {"speaker": "System", "team": "SYSTEM", "message": "New game starting!"}
    ]
    
    # Initial connection - create flat board
    initial_words = ["ROBOT", "OCEAN", "MOON", "FIRE", "TREE",
                    "STAR", "RIVER", "COMPUTER", "MOUNTAIN", "BOOK",
                    "CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD",
                    "FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE",
                    "PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]

    initial_board = []
    for i, word in enumerate(initial_words):
        # Assign teams for initial display
        if i < 9:
            team_type = "red" if i % 2 == 0 else "blue"
        elif i < 17:
            team_type = "blue" if i % 2 == 0 else "red"
        elif i == 24:
            team_type = "assassin"
        else:
            team_type = "neutral"

        initial_board.append({
            "text": word,
            "team": team_type,
            "revealed": False
        })

    await websocket.send(json.dumps({
        "phase": "STARTING",
        "last_action": "Welcome to Codenames AI vs AI!",
        "last_reasoning": "",
        "total_games": 1,
        "current_team": "RED",
        "red_team": "Claude (Red)",
        "blue_team": "GPT-4 (Blue)",
        "board": initial_board,
        "shared_context": chat_history
    }))
    
    await asyncio.sleep(2)
    
    # Mock some turns with chat
    for turn in range(4):
        team = "RED" if turn % 2 == 0 else "BLUE"
        team_name = "Claude" if team == "RED" else "GPT-4"
        
        # Spymaster thinking (with private thoughts)
        chat_history.append({
            "speaker": f"{team_name} Spymaster",
            "team": team,
            "message": "I see OCEAN, RIVER, and STORM - all water related. But STORM might be assassin...",
            "isPrivate": True
        })
        
        # Create flat board array
        words = ["ROBOT", "OCEAN", "MOON", "FIRE", "TREE",
                "STAR", "RIVER", "COMPUTER", "MOUNTAIN", "BOOK",
                "CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD",
                "FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE",
                "PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]

        board = []
        for i, word in enumerate(words):
            # Assign some teams for testing
            if i < 9:
                team_type = "red" if i % 2 == 0 else "blue"
            elif i < 17:
                team_type = "blue" if i % 2 == 0 else "red"
            elif i == 24:
                team_type = "assassin"
            else:
                team_type = "neutral"

            board.append({
                "text": word,
                "team": team_type,
                "revealed": False
            })

        await websocket.send(json.dumps({
            "phase": "THINKING",
            "last_action": f"{team} spymaster is thinking...",
            "current_team": team,
            "board": board,
            "shared_context": chat_history
        }))
        await asyncio.sleep(2)
        
        # Give clue (public)
        clues = ["WATER", "TECH", "MYTH", "NATURE", "SKY"]
        clue = random.choice(clues)
        
        chat_history.append({
            "speaker": f"{team_name} Spymaster",
            "team": team,
            "message": f"{clue} 2"
        })
        
        await websocket.send(json.dumps({
            "phase": "GUESSING",
            "last_action": f"Clue: {clue} for 2",
            "current_team": team,
            "board": board,  # Use the same flat board
            "shared_context": chat_history
        }))
        await asyncio.sleep(2)
        
        # Guesser thinking (public)
        words = ["OCEAN", "RIVER", "ROBOT", "COMPUTER", "DRAGON"]
        word = random.choice(words)
        
        chat_history.append({
            "speaker": f"{team_name} Guesser",
            "team": team,
            "message": f"I think {word} relates to {clue}, let me try that"
        })
        
        # Make guess
        result = random.choice([team.lower(), "neutral", "blue" if team == "RED" else "red"])

        # Update board to mark word as revealed
        for card in board:
            if card["text"] == word:
                card["revealed"] = True
                card["team"] = result  # Update team to match actual
                break

        chat_history.append({
            "speaker": "System",
            "team": "SYSTEM",
            "message": f"{word} was {result}!"
        })

        await websocket.send(json.dumps({
            "phase": "GUESSING",
            "last_action": f"Revealed: {word} was {result}",
            "current_team": team,
            "board": board,
            "shared_context": chat_history
        }))
        await asyncio.sleep(2)
    
    # Game over
    chat_history.append({
        "speaker": "System",
        "team": "SYSTEM",
        "message": "Game Over! Red team wins with superior word associations!"
    })
    
    await websocket.send(json.dumps({
        "phase": "ENDED",
        "last_action": "Game Over!",
        "current_team": "RED",
        "board": [
            ["ROBOT [RED]", "OCEAN [RED]", "MOON", "FIRE", "TREE"],
            ["STAR", "RIVER [BLUE]", "COMPUTER [RED]", "MOUNTAIN", "BOOK"],
            ["CLOUD", "BRIDGE", "DRAGON", "CASTLE", "SWORD"],
            ["FOREST", "TEMPLE", "CRYSTAL", "TOWER", "MAZE"],
            ["PORTAL", "SHADOW", "PHOENIX", "GARDEN", "STORM"]
        ],
        "shared_context": chat_history
    }))

async def handle_client(websocket):
    print("Client connected")
    try:
        await mock_game_with_chat(websocket)
        async for message in websocket:
            data = json.loads(message)
            if data.get("command") == "start":
                await mock_game_with_chat(websocket)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    print("Starting chat-enabled mock server on ws://localhost:8765")
    async with websockets.serve(handle_client, "localhost", 8765):
        print("Server ready! Open http://localhost:5173")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

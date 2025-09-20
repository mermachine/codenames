#!/usr/bin/env python3

import asyncio
import websockets
import json

connected_clients = set()
paused = False

async def handle_client(websocket):
    """Handle WebSocket client connections"""
    global paused
    connected_clients.add(websocket)
    print(f"[OK] Client connected! Total: {len(connected_clients)}")

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "phase": "CONNECTED",
            "paused": paused,
            "message": "Connected to working WebSocket server!"
        }))

        # Listen for messages
        async for message in websocket:
            print(f"[MSG] Received: {message}")

            try:
                data = json.loads(message)
                command = data.get("command", "unknown")

                if command == "pause":
                    paused = True
                    print("[PAUSE] Game paused")
                    response = {"paused": True, "last_action": "Game paused"}

                elif command == "resume":
                    paused = False
                    print("[RESUME] Game resumed")
                    response = {"paused": False, "last_action": "Game resumed"}

                elif command == "start":
                    print("[START] Start game requested")
                    response = {"phase": "STARTING", "last_action": "Starting game..."}

                elif command == "human_question":
                    if not paused:
                        print("[DEBUG] Game not paused, ignoring human question")
                        continue

                    target = data.get("target_ai", "unknown")
                    question = data.get("message", "")
                    print(f"[HUMAN] Question to {target}: {question}")

                    # Mock AI response
                    ai_response = f"Mock response from {target}: Thanks for asking '{question}'! This is a test response."

                    response = {
                        "shared_context": [
                            {
                                "speaker": f"Human → {target}",
                                "team": "HUMAN",
                                "message": f"Q: {question}",
                                "timestamp": "now"
                            },
                            {
                                "speaker": target,
                                "team": target.split('_')[0].upper() if '_' in target else "AI",
                                "message": f"A: {ai_response}",
                                "timestamp": "now"
                            }
                        ]
                    }
                else:
                    response = {
                        "echo": data,
                        "response": f"Server received command: {command}"
                    }

                # Broadcast to all clients
                broadcast_message = json.dumps(response)
                for client in connected_clients.copy():
                    try:
                        await client.send(broadcast_message)
                    except websockets.exceptions.ConnectionClosed:
                        connected_clients.discard(client)

                print(f"[SENT] Broadcasted response for command: {command}")

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "error": "Invalid JSON"
                }))

    except websockets.exceptions.ConnectionClosed:
        print("[INFO] Client disconnected normally")
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
    finally:
        connected_clients.discard(websocket)
        print(f"[INFO] Client removed. Total: {len(connected_clients)}")

async def main():
    print("[START] Starting working WebSocket server...")
    async with websockets.serve(handle_client, "localhost", 8765):
        print("[OK] Server running on ws://localhost:8765")
        print("[INFO] Commands: pause, resume, start, human_question")
        print("[INFO] Open http://localhost:5173 to test")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
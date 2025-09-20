#!/usr/bin/env python3

import asyncio
import websockets
import json

connected_clients = set()

async def handle_client(websocket):
    """Handle WebSocket client connections - websockets v15+ style"""
    connected_clients.add(websocket)
    print(f"[OK] Client connected! Total: {len(connected_clients)}")

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "phase": "CONNECTED",
            "message": "Welcome to websockets v15 server!"
        }))

        # Listen for messages
        async for message in websocket:
            print(f"[MSG] Received: {message}")

            try:
                data = json.loads(message)
                command = data.get("command", "unknown")

                if command == "pause":
                    response = {"paused": True, "message": "Game paused"}
                elif command == "resume":
                    response = {"paused": False, "message": "Game resumed"}
                elif command == "start":
                    response = {"phase": "STARTING", "message": "Starting game..."}
                elif command == "human_question":
                    target = data.get("target_ai", "unknown")
                    question = data.get("message", "")
                    response = {
                        "shared_context": [
                            {"speaker": f"Human → {target}", "message": f"Q: {question}"},
                            {"speaker": target, "message": f"A: Test response to '{question}'"}
                        ]
                    }
                else:
                    response = {
                        "echo": data,
                        "response": f"Server received command: {command}"
                    }

                await websocket.send(json.dumps(response))
                print(f"[SENT] Response sent for command: {command}")

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
    print("[START] Starting websockets v15 server...")
    # Use the newer API without the path parameter
    async with websockets.serve(handle_client, "localhost", 8765):
        print("[OK] Server running on ws://localhost:8765")
        print("[INFO] Open http://localhost:5173 to test connection")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
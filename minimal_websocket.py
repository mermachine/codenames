#!/usr/bin/env python3

import asyncio
import websockets
import json

connected_clients = set()

async def handle_client(websocket, path):
    connected_clients.add(websocket)
    print(f"[OK] Client connected! Total: {len(connected_clients)}")

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "phase": "CONNECTED",
            "message": "Welcome to minimal WebSocket server!"
        }))

        # Listen for messages
        async for message in websocket:
            print(f"[MSG] Received: {message}")

            try:
                data = json.loads(message)
                command = data.get("command", "unknown")

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
    print("[START] Starting minimal WebSocket server...")
    async with websockets.serve(handle_client, "localhost", 8765):
        print("[OK] Server running on ws://localhost:8765")
        print("[INFO] Open http://localhost:5173 to test connection")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
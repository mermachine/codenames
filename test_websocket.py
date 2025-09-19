"""
Test WebSocket server - minimal version to check connectivity
"""

import asyncio
import json
import websockets
from typing import Set

class TestWebSocketServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.paused = False

    async def broadcast(self, message):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return

        clients_copy = self.clients.copy()
        disconnected = []

        for client in clients_copy:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client)

        for client in disconnected:
            self.clients.discard(client)

    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        self.clients.add(websocket)
        print(f"Client connected. Total: {len(self.clients)}")

        try:
            # Send initial state
            await websocket.send(json.dumps({
                "phase": "WAITING",
                "paused": self.paused,
                "last_action": "Test server ready"
            }))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"Received: {data}")

                    if data.get("command") == "pause":
                        self.paused = True
                        print("Game paused")
                        await self.broadcast({"paused": True, "last_action": "Game paused"})

                    elif data.get("command") == "resume":
                        self.paused = False
                        print("Game resumed")
                        await self.broadcast({"paused": False, "last_action": "Game resumed"})

                    elif data.get("command") == "start":
                        print("Start game requested")
                        await self.broadcast({"phase": "STARTING", "last_action": "Starting game..."})

                    elif data.get("command") == "human_question":
                        target = data.get("target_ai", "unknown")
                        question = data.get("message", "")
                        print(f"Human question to {target}: {question}")

                        response = f"Test response to: {question}"
                        await self.broadcast({
                            "shared_context": [
                                {"speaker": f"Human → {target}", "message": f"Q: {question}"},
                                {"speaker": target, "message": f"A: {response}"}
                            ]
                        })

                except json.JSONDecodeError:
                    print(f"Invalid JSON: {message}")

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"Client disconnected. Total: {len(self.clients)}")

    async def start_server(self):
        """Start the test server"""
        print(f"[OK] Starting Test WebSocket server on port {self.port}")

        async with websockets.serve(self.handle_client, "localhost", self.port):
            print(f"Test server running at ws://localhost:{self.port}")
            print("Commands: pause, resume, start, human_question")
            await asyncio.Future()

async def main():
    server = TestWebSocketServer()
    await server.start_server()

if __name__ == "__main__":
    asyncio.run(main())
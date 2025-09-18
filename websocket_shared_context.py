"""
WebSocket server with real AI players using shared context
"""

import asyncio
import json
import websockets
import os
from typing import Set
from game_loop_shared_context import SharedContextGameLoop

class SharedContextWebSocketServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.game_loop = None
        self.current_state = {}
        self.game_running = False

    async def register(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        if self.current_state:
            await websocket.send(json.dumps(self.current_state))
        print(f"Client connected. Total: {len(self.clients)}")

    async def unregister(self, websocket):
        """Remove a client"""
        self.clients.remove(websocket)
        print(f"Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, message):
        """Broadcast to all clients"""
        if self.clients:
            message_json = json.dumps(message)
            dead_clients = set()
            for client in self.clients:
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    dead_clients.add(client)
            self.clients -= dead_clients

    async def game_state_callback(self, state):
        """Callback from game loop"""
        self.current_state = state
        await self.broadcast(state)

    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("command") == "start" and not self.game_running:
                    asyncio.create_task(self.run_game())
                elif data.get("command") == "stop":
                    self.game_running = False
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def run_game(self):
        """Run a game with shared context"""
        if self.game_running:
            return

        self.game_running = True
        self.game_loop = SharedContextGameLoop()

        # Add callback for WebSocket updates
        self.game_loop.add_visualization_callback(
            lambda state: asyncio.create_task(self.game_state_callback(state))
        )

        try:
            # Play one game
            await self.game_loop.play_game()
        except Exception as e:
            print(f"Game error: {e}")
            await self.broadcast({
                "phase": "ERROR",
                "last_action": f"Error: {str(e)[:100]}",
                "shared_context": [{
                    "speaker": "System",
                    "team": "SYSTEM",
                    "message": f"Game error: {str(e)[:100]}"
                }]
            })
        finally:
            self.game_running = False

        # Wait a bit before allowing new game
        await asyncio.sleep(5)

    async def start_server(self):
        """Start the WebSocket server"""
        print(f"Starting Shared Context WebSocket server on port {self.port}")
        print("This version uses the shared context AI system!")
        async with websockets.serve(self.handle_client, "localhost", self.port):
            print(f"Server running at ws://localhost:{self.port}")
            print(f"Open http://localhost:5173 to see the game")
            await asyncio.Future()  # Run forever


async def main():
    """Run the server"""
    server = SharedContextWebSocketServer()
    await server.start_server()


if __name__ == "__main__":
    import sys

    # Check for API key
    if len(sys.argv) > 1:
        os.environ["OPENROUTER_API_KEY"] = sys.argv[1]

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\nWARNING:  No API key found!")
        print("Usage: python websocket_shared_context.py YOUR_API_KEY")
        print("Or set OPENROUTER_API_KEY environment variable")
        print("\nStarting in MOCK mode instead...")

        # Fall back to mock server
        import subprocess
        subprocess.run(["python", "simple_mock_with_chat.py"])
    else:
        print(f"[OK] API key found (ending in ...{api_key[-4:]})")
        asyncio.run(main())
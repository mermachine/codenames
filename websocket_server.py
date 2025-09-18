"""
WebSocket server for broadcasting Codenames game state to frontend
"""

import asyncio
import json
import websockets
from typing import Set, Dict, Any
from game_loop_fixed import FixedGameLoop

class CodenamesWebSocketServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.game_loop = FixedGameLoop()
        self.current_state: Dict[str, Any] = {}

    async def register(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        # Send current game state to new client
        if self.current_state:
            await websocket.send(json.dumps(self.current_state))
        print(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        """Remove a client"""
        self.clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if self.clients:
            message_json = json.dumps(message)
            # Send to all clients, removing dead connections
            dead_clients = set()
            for client in self.clients:
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    dead_clients.add(client)

            # Clean up dead connections
            self.clients -= dead_clients

    async def game_state_callback(self, state: Dict[str, Any]):
        """Callback for game loop to send state updates"""
        self.current_state = state
        await self.broadcast(state)

    async def handle_client(self, websocket):
        """Handle a client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # For now, just echo back or handle control commands
                data = json.loads(message)
                if data.get("command") == "start":
                    # Start a new game if not running
                    if not self.game_loop.running:
                        asyncio.create_task(self.run_game())
                elif data.get("command") == "stop":
                    self.game_loop.stop()
        finally:
            await self.unregister(websocket)

    async def run_game(self):
        """Run a single game with WebSocket updates"""
        # Add our callback to the game loop
        self.game_loop.add_visualization_callback(
            lambda state: asyncio.create_task(self.game_state_callback(state))
        )

        # Run one game
        await self.game_loop.play_game()

    async def start_server(self):
        """Start the WebSocket server"""
        print(f"Starting WebSocket server on port {self.port}")
        async with websockets.serve(self.handle_client, "localhost", self.port):
            print(f"Server running at ws://localhost:{self.port}")
            # Keep server running
            await asyncio.Future()  # Run forever

async def main():
    """Run the WebSocket server with the game"""
    server = CodenamesWebSocketServer()

    # Start the server
    server_task = asyncio.create_task(server.start_server())

    # Wait a moment for server to start
    await asyncio.sleep(1)

    # Start the game loop
    await server.run_game()

if __name__ == "__main__":
    import sys
    import os

    # Set API key if provided
    if len(sys.argv) > 1:
        os.environ["OPENROUTER_API_KEY"] = sys.argv[1]

    asyncio.run(main())
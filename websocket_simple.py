"""
Simplified WebSocket server with built-in pause/resume functionality
"""

import asyncio
import json
import websockets
import os
from typing import Set
from game_loop_shared_context import SharedContextGameLoop

class SimpleWebSocketServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.game_loop = None
        self.current_state = {}
        self.game_running = False
        self.game_paused = False

    async def broadcast(self, message):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return

        # Create a copy of clients to avoid "Set changed size during iteration"
        clients_copy = self.clients.copy()

        # Remove any closed connections
        disconnected = []
        for client in clients_copy:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client)

        # Clean up disconnected clients
        for client in disconnected:
            self.clients.discard(client)

    async def game_state_callback(self, state):
        """Callback from game loop with state updates"""
        # Ensure pause state is synced
        state["paused"] = self.game_paused
        self.current_state = state
        await self.broadcast(state)

    async def handle_client(self, websocket, path):
        """Handle new WebSocket client connections"""
        self.clients.add(websocket)
        print(f"Client connected. Total: {len(self.clients)}")

        try:
            # Send current state if available
            if self.current_state:
                await websocket.send(json.dumps(self.current_state))

            # Listen for messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"Received WebSocket message: {data}")

                    if data.get("command") == "start":
                        if not self.game_running:
                            asyncio.create_task(self.start_game())

                    elif data.get("command") == "pause":
                        await self.pause_game()

                    elif data.get("command") == "resume":
                        await self.resume_game()

                    elif data.get("command") == "human_question":
                        await self.handle_human_question(data)

                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message}")

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"Client disconnected. Total: {len(self.clients)}")

    async def pause_game(self):
        """Pause the game"""
        print("Game paused via WebSocket")
        self.game_paused = True
        if self.game_loop:
            self.game_loop.pause()

        # Broadcast pause state
        if self.current_state:
            self.current_state["paused"] = True
            await self.broadcast(self.current_state)

    async def resume_game(self):
        """Resume the game"""
        print("Game resumed via WebSocket")
        self.game_paused = False
        if self.game_loop:
            self.game_loop.resume()

        # Broadcast resume state
        if self.current_state:
            self.current_state["paused"] = False
            await self.broadcast(self.current_state)

    async def handle_human_question(self, data):
        """Handle human questions to AI players"""
        if not self.game_paused:
            print("[DEBUG] Game not paused, ignoring human question")
            return

        target_ai = data.get("target_ai")
        question = data.get("message", "")

        if not target_ai or not question:
            print("[DEBUG] Missing target_ai or message in human question")
            return

        print(f"[DEBUG] Processing human question to {target_ai}: {question}")

        if self.game_loop:
            try:
                # Get AI response
                response = await self.game_loop.ask_human_question(target_ai, question)

                # Add to shared context and broadcast
                context_entry = {
                    "speaker": f"Human → {target_ai}",
                    "team": "HUMAN",
                    "message": f"Q: {question}",
                    "timestamp": "now"
                }

                response_entry = {
                    "speaker": target_ai,
                    "team": target_ai.split('_')[0].upper(),
                    "message": f"A: {response}",
                    "timestamp": "now"
                }

                # Update current state with new context
                if "shared_context" not in self.current_state:
                    self.current_state["shared_context"] = []

                self.current_state["shared_context"].extend([context_entry, response_entry])

                # Broadcast updated state
                await self.broadcast(self.current_state)

            except Exception as e:
                print(f"Error handling human question: {e}")

    async def start_game(self):
        """Start a new game"""
        if self.game_running:
            return

        self.game_running = True
        print("Starting new game...")

        # Create game loop
        self.game_loop = SharedContextGameLoop()

        # Add callback for state updates
        self.game_loop.add_visualization_callback(
            lambda state: asyncio.create_task(self.game_state_callback(state))
        )

        try:
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

        # Wait before allowing new game
        await asyncio.sleep(5)

    async def start_server(self):
        """Start the WebSocket server"""
        print(f"[OK] Starting Simple WebSocket server on port {self.port}")
        print("This version has built-in pause/resume functionality!")

        async with websockets.serve(lambda ws, path: self.handle_client(ws, path), "localhost", self.port):
            print(f"Server running at ws://localhost:{self.port}")
            print(f"Open http://localhost:5173 to see the game")
            print("Commands: pause/resume via WebSocket, human questions supported")
            await asyncio.Future()  # Run forever


async def main():
    """Run the server"""
    server = SimpleWebSocketServer()
    await server.start_server()


if __name__ == "__main__":
    import sys

    # Check for API key
    if len(sys.argv) > 1:
        os.environ["OPENROUTER_API_KEY"] = sys.argv[1]

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\nWARNING: No API key found!")
        print("Usage: python websocket_simple.py YOUR_API_KEY")
        print("Or set OPENROUTER_API_KEY environment variable")
        print("\nStarting in MOCK mode would require a different server...")
        exit(1)
    else:
        print(f"[OK] API key found (ending in ...{api_key[-4:]})")
        asyncio.run(main())
"""
WebSocket server with real AI players using shared context
"""

import asyncio
import json
import websockets
import os
import threading
from typing import Set
from game_loop_shared_context import SharedContextGameLoop
from http_pause_server import run_pause_server, set_game_loop

class SharedContextWebSocketServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.game_loop = None
        self.current_state = {}
        self.game_running = False
        self.game_paused = False

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
            # Create a copy of the set to avoid "Set changed size during iteration"
            clients_copy = list(self.clients)
            dead_clients = set()
            for client in clients_copy:
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    dead_clients.add(client)
            # Remove dead clients from the original set
            self.clients -= dead_clients

    async def game_state_callback(self, state):
        """Callback from game loop"""
        # Use the actual pause state from the game loop
        # This ensures frontend shows accurate pause status regardless of pause source (WebSocket or HTTP)
        actual_paused = self.game_loop.paused if self.game_loop else False
        state["paused"] = actual_paused
        # Also sync our local state with the actual state
        self.game_paused = actual_paused
        self.current_state = state
        await self.broadcast(state)

    async def handle_human_question(self, data):
        """Handle human question to AI"""
        try:
            print(f"[DEBUG] Handling human question: {data}")

            target_ai = data.get("target_ai")
            message = data.get("message")

            if not target_ai or not message:
                print(f"[DEBUG] Missing target_ai or message: {target_ai}, {message}")
                return

            if not self.game_loop or not hasattr(self.game_loop, 'players'):
                print(f"[DEBUG] No game loop or players available")
                return

            # Get the targeted AI player
            if target_ai not in self.game_loop.players:
                print(f"[DEBUG] Invalid AI target: {target_ai}. Available: {list(self.game_loop.players.keys())}")
                return

            ai_player = self.game_loop.players[target_ai]
            is_spymaster = "spymaster" in target_ai
            team = "RED" if "red" in target_ai else "BLUE"

            print(f"[DEBUG] Targeting {ai_player.name} ({team} {target_ai})")

            # Add human question to chat (always visible for now)
            self.game_loop.add_to_chat("Human", "SYSTEM", f"Asks {ai_player.name}: {message}")

            # Get AI response
            # Create a simple prompt asking the AI to respond as their character
            response_prompt = f"""You are {ai_player.name}, an AI player in a Codenames game.
A human visitor to the installation has asked you: "{message}"

Please respond in character, keeping in mind:
- Your role: {'Spymaster' if is_spymaster else 'Guesser'} for {team} team
- The current game state (board, clues given, etc.)
- Stay helpful but maintain your competitive AI personality

Respond conversationally in 1-2 sentences."""

            print(f"[DEBUG] Calling AI API for response...")

            # Use the AI player's API to get response (run in executor since it's synchronous)
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, ai_player.get_ai_response, response_prompt, 150)

            print(f"[DEBUG] Got AI response: {response[:100]}...")

            # Add AI response to chat
            # If spymaster, mark as private so other team can't see
            is_private = is_spymaster
            self.game_loop.add_to_chat(ai_player.name, team, response, is_private=is_private)

            # Send updated state
            await self.game_loop.send_game_state("PAUSED")

            print(f"[DEBUG] Human question handled successfully")

        except Exception as e:
            print(f"[ERROR] Error handling human question: {e}")
            import traceback
            traceback.print_exc()

            # Add error message to chat if possible
            try:
                if self.game_loop:
                    self.game_loop.add_to_chat("System", "SYSTEM", f"Error getting AI response: {str(e)[:100]}")
                    await self.game_loop.send_game_state("PAUSED")
            except Exception as e2:
                print(f"[ERROR] Failed to add error message to chat: {e2}")

    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"Received WebSocket message: {data}")  # DEBUG
                if data.get("command") == "start" and not self.game_running:
                    asyncio.create_task(self.run_game())
                elif data.get("command") == "stop":
                    self.game_running = False
                elif data.get("command") == "pause":
                    self.game_paused = True
                    if self.game_loop:
                        self.game_loop.pause_game()
                elif data.get("command") == "resume":
                    self.game_paused = False
                    if self.game_loop:
                        self.game_loop.resume_game()
                elif data.get("command") == "human_question":
                    # Check the actual pause state from the game loop
                    actual_paused = self.game_loop.paused if self.game_loop else False
                    print(f"[DEBUG] Human question received. game_loop exists: {self.game_loop is not None}, actual game loop paused: {actual_paused}, websocket paused: {self.game_paused}")
                    if self.game_loop:
                        # Only handle human questions when game is actually paused (check game loop, not just websocket state)
                        if actual_paused:
                            await self.handle_human_question(data)
                        else:
                            print(f"[DEBUG] Game not actually paused (game_loop.paused={actual_paused}), ignoring human question")
                    else:
                        print(f"[DEBUG] No game loop available for human question")
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

        # Set game loop reference for HTTP pause server
        set_game_loop(self.game_loop)

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
            print(f"Pause server available at http://localhost:8766")
            print(f"Open http://localhost:5173 to see the game")
            await asyncio.Future()  # Run forever


async def main():
    """Run the server"""
    server = SharedContextWebSocketServer()

    # Start HTTP pause server in background thread
    pause_thread = threading.Thread(
        target=run_pause_server,
        args=(8766,),
        daemon=True
    )
    pause_thread.start()

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
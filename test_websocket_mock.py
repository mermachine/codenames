"""
Test WebSocket server with mock AI players (no API calls needed)
"""

import asyncio
import json
import websockets
import random
from typing import Set, Dict, Any
from codenames_core import CodenamesGame, Team, Clue
from words import DEFAULT_WORDS

class MockGameLoop:
    def __init__(self):
        self.running = False
        self.visualization_callbacks = []
        self.game = None

    def add_visualization_callback(self, callback):
        self.visualization_callbacks.append(callback)

    def notify_visualizers(self, state):
        for callback in self.visualization_callbacks:
            try:
                callback(state)
            except Exception as e:
                print(f"Visualization error: {e}")

    async def play_mock_game(self):
        """Play a mock game with simulated AI moves"""
        self.game = CodenamesGame(DEFAULT_WORDS)

        # Initial state
        state = {
            "phase": "STARTING",
            "last_action": "Starting new mock game!",
            "last_reasoning": "",
            "total_games": 1,
            "current_team": "RED",
            "board": self.game.get_board_display(),
            "game_state": self.game.get_game_state(),
            "red_team": "Mock Claude (Red)",
            "blue_team": "Mock GPT (Blue)"
        }
        self.notify_visualizers(state)
        await asyncio.sleep(2)

        # Play some mock turns
        turn_count = 0
        while not self.game.game_over and turn_count < 20:
            team = self.game.current_team
            team_name = "Red" if team == Team.RED else "Blue"

            # Mock spymaster thinking
            state["phase"] = "THINKING"
            state["last_action"] = f"{team_name} spymaster is thinking..."
            state["current_team"] = team.value if hasattr(team, 'value') else str(team)
            self.notify_visualizers(state)
            await asyncio.sleep(2)

            # Mock clue
            mock_clues = ["CONNECT", "WATER", "TECH", "NATURE", "SPACE"]
            clue = Clue(word=random.choice(mock_clues), number=2, reasoning="Mock reasoning")
            self.game.give_clue(clue)

            state["last_action"] = f"Clue: '{clue.word}' for {clue.number}"
            state["last_reasoning"] = f"Mock reasoning: Looking for words related to {clue.word}"
            self.notify_visualizers(state)
            await asyncio.sleep(2)

            # Mock guesses
            state["phase"] = "GUESSING"
            unrevealed = [w.text for w in self.game.board if not w.revealed]
            if unrevealed:
                # Make 1-2 guesses
                num_guesses = min(clue.number, len(unrevealed), 2)
                for i in range(num_guesses):
                    if unrevealed:
                        guess = random.choice(unrevealed)
                        unrevealed.remove(guess)

                        state["last_action"] = f"{team_name} guesses: {guess}"
                        self.notify_visualizers(state)
                        await asyncio.sleep(2)

                        continue_turn, result = self.game.make_guess(guess)
                        state["board"] = self.game.get_board_display()
                        state["game_state"] = self.game.get_game_state()

                        if "ASSASSIN" in result or "wins" in result:
                            state["phase"] = "ENDED"
                            state["last_action"] = result
                            self.notify_visualizers(state)
                            return

                        if not continue_turn:
                            state["last_action"] = f"Wrong! {guess} was {result}"
                            self.notify_visualizers(state)
                            await asyncio.sleep(2)
                            break

            self.game.end_turn()
            turn_count += 1

        # Game over
        state["phase"] = "ENDED"
        winner = self.game.winner
        if winner:
            winner_name = "Mock Claude" if winner == Team.RED else "Mock GPT"
            state["last_action"] = f"Game Over! {winner_name} wins!"
        else:
            state["last_action"] = "Game ended (turn limit)"
        self.notify_visualizers(state)

class MockWebSocketServer:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.game_loop = MockGameLoop()
        self.current_state: Dict[str, Any] = {}

    async def register(self, websocket):
        self.clients.add(websocket)
        if self.current_state:
            await websocket.send(json.dumps(self.current_state))
        print(f"Client connected. Total: {len(self.clients)}")

    async def unregister(self, websocket):
        self.clients.remove(websocket)
        print(f"Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, message: Dict[str, Any]):
        if self.clients:
            message_json = json.dumps(message)
            dead_clients = set()
            for client in self.clients:
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    dead_clients.add(client)
            self.clients -= dead_clients

    async def game_state_callback(self, state: Dict[str, Any]):
        self.current_state = state
        await self.broadcast(state)

    async def handle_client(self, websocket):
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("command") == "start":
                    asyncio.create_task(self.run_game())
        finally:
            await self.unregister(websocket)

    async def run_game(self):
        self.game_loop.add_visualization_callback(
            lambda state: asyncio.create_task(self.game_state_callback(state))
        )
        await self.game_loop.play_mock_game()

    async def start_server(self):
        print(f"Starting MOCK WebSocket server on port {self.port}")
        print("This version doesn't need API keys!")
        async with websockets.serve(self.handle_client, "localhost", self.port):
            print(f"Server running at ws://localhost:{self.port}")
            print(f"Open http://localhost:5173 in your browser")
            await asyncio.Future()

async def main():
    server = MockWebSocketServer()
    await server.start_server()

if __name__ == "__main__":
    asyncio.run(main())
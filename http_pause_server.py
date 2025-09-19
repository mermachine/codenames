"""
Simple HTTP server for pause/resume functionality
"""

import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from game_loop_shared_context import SharedContextGameLoop

# Global reference to game loop
GAME_LOOP = None

def set_game_loop(game_loop):
    global GAME_LOOP
    GAME_LOOP = game_loop

class PauseHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global GAME_LOOP
        if self.path == '/pause':
            if GAME_LOOP:
                GAME_LOOP.pause_game()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "paused"}).encode())
                print("Game paused via HTTP")
            else:
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Game loop not available"}).encode())

        elif self.path == '/resume':
            if GAME_LOOP:
                GAME_LOOP.resume_game()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "resumed"}).encode())
                print("Game resumed via HTTP")
            else:
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Game loop not available"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_pause_server(port=8766):
    """Run HTTP pause server in a separate thread"""
    server = HTTPServer(('localhost', port), PauseHandler)
    print(f"Pause server running on http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    # Test server
    print("Testing pause server...")
    server = HTTPServer(('localhost', 8766), PauseHandler)
    server.serve_forever()
# Codenames AI vs AI - Project Structure

## Core Files

### Game Engine
- `codenames_core.py` - Core game logic (board, teams, scoring)
- `words.py` - Curated word lists for the game
- `ai_player_openrouter.py` - AI player implementation with OpenRouter API support

### Game Execution
- `game_loop_fixed.py` - Main game loop with all fixes applied (anti-cheating, rate limiting, etc.)
- `websocket_server.py` - WebSocket server for real-time frontend updates
- `test_websocket_mock.py` - Mock server for testing without API calls

### Testing
- `test_mock.py` - Test game mechanics without API calls
- `test_game.py` - Test with real API calls

## Frontend (codenames-site/)

React + TypeScript + Vite application for visualization:
- `src/CodenamesGame.tsx` - Main game component with WebSocket connection
- `src/components/` - Card components for game board
- Real-time updates via WebSocket

## Running the Installation

### For Testing (No API needed)
```bash
# Terminal 1: Start mock WebSocket server
python test_websocket_mock.py

# Terminal 2: Start frontend
cd codenames-site
npm run dev
```

### For Production (With API)
```bash
# Terminal 1: Start WebSocket server with API key
OPENROUTER_API_KEY='your-key' python websocket_server.py

# Terminal 2: Start frontend
cd codenames-site
npm run dev
```

Open http://localhost:5173 to view the game!

## Key Features
- ✅ Separate AI instances for spymaster/guesser (no cheating!)
- ✅ Rate limiting (30 games/hour)
- ✅ Conversation history management (prevents token overflow)
- ✅ Multiple model support via OpenRouter
- ✅ Real-time WebSocket updates
- ✅ Mock mode for testing without API costs
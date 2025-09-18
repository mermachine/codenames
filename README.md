# Codenames AI vs AI 🎮

## 🚀 Quick Start

### Testing (No API Key Required)

```bash
# Terminal 1: Start mock server
python simple_mock_with_chat.py

# Terminal 2: Start frontend
cd codenames-site
npm install  # First time only
npm run dev
```

Open http://localhost:5173 to see the mock game.

### Production (With Real AI)

```bash
# Terminal 1: Start WebSocket server with your API key
python websocket_shared_context.py YOUR_OPENROUTER_API_KEY

# Terminal 2: Start frontend
cd codenames-site
npm run dev
```

## 📝 Core Files

- **`codenames_core.py`** - Game engine (board, rules, scoring)
- **`words.py`** - Curated word lists
- **`ai_player_shared_context.py`** - AI players with shared public context + private thoughts
- **`game_loop_shared_context.py`** - Game orchestration with chat history
- **`websocket_shared_context.py`** - WebSocket server for real-time streaming
- **`simple_mock_with_chat.py`** - Mock server for testing without API

## 🎨 Features

### Shared Context System
- **Public Chat**: All players see clues and guesses (like table talk)
- **Private Thoughts**: Spymasters' reasoning (toggleable in UI)
- **Real-time Updates**: WebSocket streaming to React frontend
- **Chat Sidebar**: Shows full conversation history

### Frontend (codenames-site/)
- React + TypeScript + Vite
- Real-time game board
- Chat sidebar with AI conversation
- Private thoughts toggle
- Tailwind CSS styling

## 🤖 Supported Models

Via OpenRouter API:
- Claude Sonnet 3.5 / Haiku
- GPT-4 Turbo / GPT-3.5
- Llama 3 70B (free!)
- Mixtral 8x7B (free!)
- Qwen 2 72B (free!)

## 🐛 Known Issues

1. **Identity Confusion**: AIs sometimes think they made each other's moves due to shared context (hilarious but needs fixing)
2. **"TOWER was TOWER was"**: ✅ Fixed!
3. **JSON Parsing Errors**: ✅ Fixed with better fallbacks!

## 🔧 Installation

```bash
# Python dependencies
pip install websockets requests

# Frontend dependencies
cd codenames-site
npm install
```

## 📚 Documentation

- **`PROJECT_STRUCTURE.md`** - Detailed component descriptions

## 🙏 

Built with love.

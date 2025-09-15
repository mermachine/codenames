# Codenames AI vs AI

Continuous Codenames game for Delight Nexus installation.

## Files

- `codenames_core.py` - Game logic (board generation, turn management, scoring)
- `ai_player.py` - Original AI player using Anthropic API directly
- `ai_player_openrouter.py` - AI player using OpenRouter API (supports Claude, GPT, Llama, etc)
- `game_loop.py` - Original continuous loop for Anthropic API
- `game_loop_openrouter.py` - Continuous loop using OpenRouter for multiple models
- `test_mock.py` - Test game mechanics without API calls
- `test_game.py` - Test single game with real API calls

## Quick Start

```bash
# Test without API
python test_mock.py

# With OpenRouter API
export OPENROUTER_API_KEY='your-key-here'
python game_loop_openrouter.py

# With Anthropic API (original)
export ANTHROPIC_API_KEY='your-key-here'
python test_game.py
```

## How It Works

1. `CodenamesGame` class manages game state (25 words, team assignments, turns)
2. `AIPlayer` class makes API calls to AI models for clues/guesses
3. `ContinuousGameLoop` orchestrates endless games with different model pairings
4. Game state is exposed via callbacks for visualization

## OpenRouter Support

Using OpenRouter allows testing with multiple model providers:
- **Claude Models**: Sonnet 3.5, Opus, Haiku
- **OpenAI Models**: GPT-4 Turbo, GPT-3.5 Turbo
- **Open Source**: Llama 3 70B, Mixtral 8x7B, Qwen 2 72B

Model pairings in `game_loop_openrouter.py` show personality differences across architectures.

## Current Status

- Core game logic ✓
- AI player with API calls ✓
- Continuous loop ✓
- OpenRouter support ✓
- Visualization (TODO)
- Human drop-in (TODO)
- Video input processing (TODO)

## Notes

- Models play both spymaster and guesser roles
- Full reasoning is captured for personality analysis
- Graceful error handling for API failures
- Game history saved every 10 games
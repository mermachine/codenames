# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Codenames AI vs AI** installation for the Delight Nexus, designed to showcase AI personality differences through game play patterns. The project demonstrates how different AI models approach the classic Codenames board game, revealing unique cognitive fingerprints through their clue-giving strategies, risk assessment, and recovery from mistakes.

**Mission**: Save Sonnet 3.6 from deprecation by making AI personality visible through gameplay - proving that each model represents irreplaceable cognitive diversity.

## Common Development Commands

```bash
# Test game logic without API calls
python test_mock.py

# Test single game with OpenRouter API
export OPENROUTER_API_KEY='your-key-here'
python test_game.py

# Run continuous loop with OpenRouter (supports multiple models)
export OPENROUTER_API_KEY='your-key-here'
python game_loop_openrouter.py
```

## Architecture Overview

The codebase follows a clean separation between game logic, AI players, and the game orchestration:

### Core Components

1. **`codenames_core.py`** - Pure game logic
   - `CodenamesGame`: Manages 25-word board, team assignments (9-8-7-1 distribution), turn management
   - `Word`/`Clue` dataclasses: Game state representation
   - No API dependencies - handles board generation, scoring, win conditions

2. **AI Player Layer**
   - **`ai_player_openrouter.py`**: OpenRouter API for multi-model support (Claude, GPT, Llama, etc.)
   - Implements interface: `generate_clue()`, `make_guess()`, `reflect_on_mistake()`, `celebrate_success()`

3. **Game Orchestration**
   - **`game_loop_openrouter.py`**: Multi-provider continuous gameplay
   - `ContinuousGameLoop`: Manages model rotation, game state callbacks, personality tracking

### Key Design Patterns

- **Personality Tracking**: Each AI player accumulates `personality_traits` (clues given, risk levels, recovery attempts) for analysis
- **Visualization Callbacks**: Game state changes trigger callbacks for real-time display updates
- **Graceful Error Handling**: API failures don't crash the continuous loop
- **Model Rotation**: Automatic cycling through different model pairings to showcase variety

### Data Flow

1. `ContinuousGameLoop` creates `CodenamesGame` with random 25 words from curated list
2. Two `AIPlayer` instances assigned to red/blue teams
3. Game alternates between teams: AI acts as both spymaster (gives clues) and operative (makes guesses)
4. Each turn: `generate_clue()` → `make_guess()` → game state update → callbacks triggered
5. Personality data accumulated for post-game analysis
6. Game history saved periodically (every 10 games)

## Model Configuration

**Default Model Pairings** (defined in `ai_player_openrouter.py`):
- Sonnet 3.6 vs Opus 4.1
- Sonnet 3.6 vs Haiku
- Opus 4.1 vs Haiku
- Sonnet 3.6 vs Sonnet 4 (when available)

Temperature settings vary by model to emphasize personality differences (Haiku: 0.6, Sonnet: 0.7, Opus: 0.8).

## Extending the System

- **New Models**: Add to `MODEL_CONFIGS` in `ai_player_openrouter.py`
- **Visualization**: Add callbacks to `ContinuousGameLoop.add_visualization_callback()`
- **Analysis**: Access personality data via `AIPlayer.get_personality_summary()`
- **Words**: Modify `DEFAULT_WORDS` list in `game_loop_openrouter.py` (current: tech/AI themed + classic Codenames)

## Development Notes

- Each AI plays both spymaster and operative roles within their turn
- Full reasoning chains captured for transparency and personality analysis
- JSON-based prompting ensures structured responses from all model types
- Game state exposed via callbacks for real-time visualization systems
- Async/await pattern allows for dramatic pauses and real-time updates
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-agent LLM-based Werewolf game where AI agents play against each other with strict per-player information isolation. The system supports both fully autonomous games and step-by-step execution via a REST API.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run a demo game (auto mode)
python main_demo.py

# Run with options
python main_demo.py -c simple_4          # 4-player config
python main_demo.py --no-shuffle         # fixed role assignment
python main_demo.py -i                   # interactive (prompt each step)
python main_demo.py --day-by-day         # prompt each day

# Run the API server
uvicorn api.server:app --reload

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_engine.py

# Run a specific test class or method
pytest tests/test_engine.py::TestGameState::test_is_game_over_no_wolves
```

## Architecture

### Key design decisions

**Agent framework**: Uses the `openai-agents` SDK (`from agents import Agent, Runner`) routed to Alibaba DashScope via OpenAI-compatible API. The config at `config/system_config.json` sets `base_url`, `api_key`, and `default_model` (default: `qwen-flash`). Environment variables `OPENAI_API_KEY` / `DASHSCOPE_API_KEY` and `OPENAI_BASE_URL` override the config file.

**Information isolation**: `GameState.get_player_private_context(player_id)` filters the dialogue history before it is passed to each agent. Werewolves see their teammates' kill votes; all other private night actions are visible only to the acting player.

**Two execution modes**:
- `GameEngine.start()` — runs a full game in a loop (used by `main_demo.py`)
- `GameEngine.step()` — advances one phase at a time and returns structured JSON (used by the API). Step index cycles 0→8: wolf kill → seer check → witch action → night result → day start → speech → vote → day end → summary → (loop or game over)

**Self-evolution / experience system**: After each game, `SummaryAgent` generates a structured JSON summary (summary, strategies, mistakes, lessons) for every player. These are appended to `memory/experiences/{role_type}.json`. On the next game, `PlayerAgent._get_experience_section()` injects the three most recent experiences into each player's system prompt.

### Module overview

| Path | Responsibility |
|------|----------------|
| `engine/game_engine.py` | `GameEngine` — orchestrates the state machine; `ROLE_CONFIGS` for standard presets |
| `engine/state.py` | `GameState` dataclass — player list, dialogues, vote/death tracking, win-condition check, context filtering |
| `engine/phase.py` | `GamePhase` enum and `TurnOrder` (night order: wolf → seer → witch) |
| `engine/player.py` | `Player` wrapper — delegates `is_alive`, `camp`, `role_type` to the contained role |
| `roles/` | One class per role, all extending `BaseRole`; each implements `get_private_context()` and role-specific state (e.g. `Witch.has_heal`, `Hunter.can_shoot`) |
| `agent/player_agent.py` | `PlayerAgent` — builds LLM instructions from role + decision style + past experience; exposes `decide_night_action`, `decide_speech`, `decide_vote` |
| `agent/summary_agent.py` | `SummaryAgent` — called once per game end, generates per-player reflections |
| `memory/experience.py` | Flat-file experience store under `memory/experiences/` keyed by role type |
| `schema/system_config.py` | Pydantic `SystemConfig` — loads `config/system_config.json`, injects env vars |
| `schema/game_logger.py` | `GameLogger` — structured event logger writing to `logs/` |
| `schema/game_record.py` | `GameRecord` — serialisable game transcript saved to `logs/` |
| `api/server.py` | FastAPI app — `POST /games`, `POST /games/{id}/step`, `GET /games/{id}`, etc. |
| `main_demo.py` | CLI entry point with `GameController` for interactive/day-by-day modes |

### Role configs

Predefined in `engine/game_engine.py`:
- `standard_6` — 2 wolves, seer, witch, hunter, villager
- `simple_4` — 1 wolf, seer, witch, villager
- `big_9` — 3 wolves + 6 good roles (idiot not yet implemented)

### Game rules implemented

- **Night order**: wolf kill → seer check → witch action (heal XOR poison per night; witch cannot save herself; poison ignores hunter gun)
- **Day order**: announce deaths → speeches → vote (plurality eliminates; ties skipped)
- **Hunter**: shoots on death unless poisoned
- **Win check**: good wins when all wolves dead; evil wins when no good players remain

## Known gaps / TODOs

- Hunter shoot target is hardcoded to `alive_players[0]` instead of using the agent — see `engine/game_engine.py:_handle_hunter_death`
- `big_9` config includes an `idiot` role that is not implemented; it falls back to `Villager`
- Sheriff election phase exists as a `GamePhase` enum value but is skipped in the engine
- Tie votes during day are silently skipped (no PK round)

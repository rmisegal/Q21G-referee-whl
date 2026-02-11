# CLAUDE.md

**IMPORTANT: Read this entire file before making ANY code changes.**

Version: 2.0.0

## Project Overview

Q21 Referee SDK — A Python SDK for implementing Q21 League referee AI. Students implement 4 callback methods to create their referee logic. The SDK handles all protocol communication, email management, and game lifecycle.

## Terminology

| Term | Full Name | Description |
|------|-----------|-------------|
| **RLGM** | Referee League Game Manager | Season orchestration layer. Handles League Manager communication, assignment tracking, and multi-game coordination. |
| **GMC** | Game Management Cycle | Single-game execution layer. Manages one game's lifecycle from warmup to scoring. |
| **GPRM** | Game Parameters | Immutable data passed from RLGM to GMC when starting a game. Contains player info, game_id, round info. |
| **LM** | League Manager | External system that broadcasts season events and receives match results. |
| **game_id** | Game Identifier | 7-digit format `SSRRGGG` — SS=season, RR=round, GGG=game number. Created by League Manager. |

## Architecture Layers

```
Student Code (RefereeAI implementation)
    ↓
RLGMRunner (rlgm_runner.py) — Entry point, email polling
    ↓
RLGM Layer (_rlgm/) — Season orchestration, LM protocol
    ↓
GMC Layer (_gmc/) — Single game management
    ↓
SHARED Layer (_shared/) — Email, logging, protocol utilities
    ↓
Gmail API (OAuth-based communication)
```

## Development Principles

1. **Ask clarifying questions** — Always ask as many questions as needed before implementing. Never assume.
2. **Check existing code first** — Before implementing any function or system, search the current codebase to see if it already exists.
3. **Reuse existing code above all else** — Prefer wiring into existing functions and modules. This ensures easy integration.
4. **Recommend session splits** — If a task is too large for one session, recommend splitting it up.
5. **Modularity** — The project must be as modular as possible. Small, focused modules with clear responsibilities.
6. **TDD** — Follow Test-Driven Development. Write tests first, then implement to make them pass.
7. **150-line file limit** — All Python files must stay under 150 lines. If a file exceeds this, refactor or split it.
8. **No hardcoded secrets or paths** — Never hardcode secrets, credentials, file paths, URLs, or environment-specific values in source code. All such values must come from `config.json` or environment variables.

## Documentation & Versioning

1. **Document versioning** — All documentation files (README, PRDs, plans) must have a semantic version (e.g., `1.0.0`) at the top.

2. **Code-to-PRD mapping** — Every source file must have a header comment indicating its area/system and corresponding PRD:
   ```python
   # Area: <Feature Name>
   # PRD: docs/<prd-filename>.md
   ```

3. **Sync requirement** — When code changes, update the corresponding PRD:
   - Increment the PRD version
   - Update the PRD content to match the implementation
   - Update any affected README sections

4. **PRD location** — All PRD documents live in the `docs/` folder.

5. **Feature PRDs** — Each feature has its own PRD document. Features map to one or more modules:

   | Feature | PRD | Modules |
   |---------|-----|---------|
   | RLGM (Season Management) | `docs/prd-rlgm.md` | `_rlgm/` |
   | GMC (Game Lifecycle) | `docs/prd-rlgm.md` | `_gmc/` |
   | Protocol & Email | `docs/prd-rlgm.md` | `_shared/` |
   | Student Callbacks | — | `callbacks.py`, `types.py` |
   | Demo Mode | — | `demo_ai.py`, `demo_data/` |

## Project Structure

```
src/q21_referee/
├── __init__.py              # Public API exports
├── callbacks.py             # RefereeAI abstract class (student implements)
├── types.py                 # TypedDict definitions for callbacks
├── runner.py                # RefereeRunner (single-game mode)
├── rlgm_runner.py           # RLGMRunner (season mode, default)
├── demo_ai.py               # Pre-built DemoAI implementation
├── cli.py                   # Command-line interface
├── errors.py                # Custom exception classes
├── _runner_config.py        # Configuration validation
│
├── _rlgm/                   # RLGM Layer (season orchestration)
│   ├── orchestrator.py      # Main orchestrator
│   ├── state_machine.py     # RLGM lifecycle states
│   ├── gprm.py              # Game Parameters dataclass
│   ├── game_result.py       # GameResult dataclass
│   ├── broadcast_router.py  # Routes LM broadcasts
│   ├── response_builder.py  # Builds LM responses
│   ├── database.py          # SQLite persistence
│   ├── handler_*.py         # Message handlers (9 files)
│   └── repo_*.py            # Data repositories (3 files)
│
├── _gmc/                    # GMC Layer (single game)
│   ├── gmc.py               # GameManagementCycle wrapper
│   ├── state.py             # GameState, GamePhase, PlayerState
│   ├── router.py            # Player message router
│   ├── envelope_builder.py  # Protocol message construction
│   ├── context_builder.py   # Callback context building
│   ├── callback_executor.py # Callback execution with timeouts
│   ├── validator.py         # Protocol validation
│   └── handlers/            # Player message handlers
│       ├── warmup.py
│       ├── questions.py
│       └── scoring.py
│
└── _shared/                 # Shared utilities
    ├── email_client.py      # Gmail OAuth client (IMAP/SMTP)
    ├── logging_config.py    # Colored logging setup
    ├── protocol.py          # Protocol constants, envelope building
    └── protocol_logger.py   # Structured protocol message logging
```

## The 4 Callback Methods (Student API)

Students implement these in a `RefereeAI` subclass:

1. **`get_warmup_question(ctx)`** — Return connectivity verification question
2. **`get_round_start_info(ctx)`** — Select book, create hint and association word
3. **`get_answers(ctx)`** — Answer 20 questions about the chosen book
4. **`get_score_feedback(ctx)`** — Score player's guess, provide feedback

## Key Data Flow

```
League Manager
    ↓ BROADCAST_ASSIGNMENT_TABLE
handler_assignment.py → stores assignments with game_id
    ↓ BROADCAST_NEW_LEAGUE_ROUND
handler_new_round.py → creates GPRM with game_id
    ↓
GMC.gprm.game_id → GameState.game_id
    ↓
All player messages include game_id
    ↓
GameResult.game_id → MATCH_RESULT_REPORT
    ↓
League Manager
```

## Testing

- Tests live in `tests/` directory
- Run with: `pytest tests/`
- Each module should have corresponding test file: `test_<module>.py`

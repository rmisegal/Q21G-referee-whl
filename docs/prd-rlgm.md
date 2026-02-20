# PRD: RLGM - Referee League Game Manager

**Version:** 2.3.0
**Area:** Season & Game Orchestration
**PRD:** docs/prd-rlgm.md

---

## 1. Overview

The **RLGM (Referee League Game Manager)** is an interface layer that sits between the League Manager and the GMC (Game Management Cycle). It handles all League Manager protocol communications and orchestrates individual games by calling the GMC with game-specific parameters (GPRM).

### Terminology
| Term | Definition |
|------|------------|
| **RLGM** | Referee League Game Manager - new orchestration layer |
| **GMC** | Game Management Cycle - existing single-game implementation |
| **GPRM** | Game Parameters - config values passed to GMC per game |
| **LM** | League Manager - external system managing the league |

---

## 2. Problem Statement

The current GMC implementation:
- Handles only ONE game at a time
- Requires hardcoded GPRM values at startup
- Lacks handlers for season lifecycle messages (BROADCAST_START_SEASON, BROADCAST_ASSIGNMENT_TABLE, etc.)
- Cannot dynamically receive game assignments from League Manager

**Gap Analysis (post-reform):**

| Message | Layer | Handler |
|---------|-------|---------|
| BROADCAST_START_SEASON | RLGM | `handler_start_season.py` |
| SEASON_REGISTRATION_RESPONSE | RLGM | `handler_registration_response.py` |
| BROADCAST_ASSIGNMENT_TABLE | RLGM | `handler_assignment.py` |
| BROADCAST_NEW_LEAGUE_ROUND | RLGM | `handler_new_round.py` |
| BROADCAST_END_LEAGUE_ROUND | RLGM | `handler_end_round.py` |
| BROADCAST_END_SEASON | RLGM | `handler_end_season.py` |
| LEAGUE_COMPLETED | Runner | Accepted and logged; no active handler (terminal signal) |
| Q21WARMUPRESPONSE | GMC | `handlers/warmup.py` |
| Q21QUESTIONSBATCH | GMC | `handlers/questions.py` |
| Q21GUESSSUBMISSION | GMC | `handlers/scoring.py` |

---

## 3. Solution Architecture

```
+-------------------------------------------------------------------------+
|                           STUDENT CODE                                  |
|  class MyRefereeAI(RefereeAI):                                         |
|      def get_warmup_question(ctx): ...                                 |
|      def get_round_start_info(ctx): ...                                |
|      def get_answers(ctx): ...                                         |
|      def get_score_feedback(ctx): ...                                  |
+--------------------------------+----------------------------------------+
                                 | (4 callbacks)
                                 v
+-------------------------------------------------------------------------+
|                    GMC (Game Management Cycle)                          |
|  +---------------------------------------------------------------------+|
|  | Input: GPRM (Game Parameters)                                       ||
|  |   - player1_email, player1_id                                       ||
|  |   - player2_email, player2_id                                       ||
|  |   - season_id, game_id, match_id                                    ||
|  |                                                                     ||
|  | Manages: Single game lifecycle                                      ||
|  |   - Q21WARMUPCALL -> Q21WARMUPRESPONSE                              ||
|  |   - Q21ROUNDSTART -> Q21QUESTIONSBATCH -> Q21ANSWERSBATCH           ||
|  |   - Q21GUESSSUBMISSION -> Q21SCOREFEEDBACK                          ||
|  |                                                                     ||
|  | Output: GameResult                                                  ||
|  |   - player1: PlayerScore, player2: PlayerScore                      ||
|  |   - winner_id, is_draw, status, player_states                       ||
|  +---------------------------------------------------------------------+|
|                                 ^                                       |
|                                 | (GPRM input, GameResult output)       |
+---------------------------------+---------------------------------------+
                                  |
+---------------------------------+---------------------------------------+
|                    RLGM (Referee League Game Manager)                   |
|  +---------------------------------------------------------------------+|
|  | Season State Machine:                                               ||
|  |   INIT -> WAITING_FOR_CONFIRMATION -> WAITING_FOR_ASSIGNMENT        ||
|  |        -> RUNNING -> IN_GAME -> RUNNING -> ...                      ||
|  |                                                                     ||
|  | Responsibilities:                                                   ||
|  |   1. Handle all LM broadcasts (register, assign, start/end)         ||
|  |   2. Store game assignments in database                             ||
|  |   3. Call GMC for each game with GPRM                               ||
|  |   4. Collect GameResults from GMC                                   ||
|  |   5. Send MATCH_RESULT_REPORT to League Manager                     ||
|  |   6. Track season/round lifecycle                                   ||
|  +---------------------------------------------------------------------+|
|                                 ^                                       |
|                                 | (Gmail protocol)                      |
+---------------------------------+---------------------------------------+
                                  |
                    +-------------+-------------+
                    |      LEAGUE MANAGER       |
                    |  (External Gmail System)  |
                    +---------------------------+
```

---

## 4. GPRM (Game Parameters) Specification

```python
@dataclass(frozen=True)
class GPRM:
    """Game Parameters passed from RLGM to GMC for each game (immutable)."""

    # Player 1
    player1_email: str      # e.g., "alice@gmail.com"
    player1_id: str         # e.g., "P001"

    # Player 2
    player2_email: str      # e.g., "bob@gmail.com"
    player2_id: str         # e.g., "P002"

    # Game identifiers
    season_id: str          # e.g., "SEASON_2026_Q1"
    game_id: str            # e.g., "0101001" (7-digit: SSRRGGG)
    match_id: str           # e.g., "R1M1"

    # Round info (from BROADCAST_NEW_LEAGUE_ROUND)
    round_id: str           # e.g., "ROUND_1"
    round_number: int       # e.g., 1
```

---

## 5. GameResult Specification

```python
@dataclass
class PlayerScore:
    """Individual player's score and statistics from a game."""
    player_id: str
    player_email: str
    score: int
    questions_answered: int
    correct_answers: int

@dataclass
class GameResult:
    """Result returned from GMC to RLGM after game completion."""

    game_id: str
    match_id: str
    round_id: str
    season_id: str
    player1: PlayerScore
    player2: PlayerScore
    winner_id: Optional[str]
    is_draw: bool
    status: str = "completed"              # "completed" | "aborted"
    abort_reason: Optional[str] = None     # "new_round_started" | "end_round_received"
    player_states: Optional[dict] = None   # per-player phase snapshot with last_actor
```

---

## 6. RLGM Message Flow

### 6.1 Season Registration Flow

```
LEAGUE MANAGER                    RLGM                              GMC
      |                            |                                 |
      | BROADCAST_START_SEASON     |                                 |
      |--------------------------->|                                 |
      |                            | [Save broadcast]                |
      |                            | [Transition: WAITING_FOR_CONF]  |
      |                            |                                 |
      |<---------------------------|                                 |
      | SEASON_REGISTRATION_REQUEST|                                 |
      |                            |                                 |
      | SEASON_REGISTRATION_RESPONSE                                 |
      |--------------------------->|                                 |
      |                            | [If accepted: -> WAITING_FOR_   |
      |                            |  ASSIGNMENT]                    |
```

### 6.2 Assignment Flow

```
LEAGUE MANAGER                    RLGM                              GMC
      |                            |                                 |
      | BROADCAST_ASSIGNMENT_TABLE |                                 |
      |--------------------------->|                                 |
      |                            | [Extract assignments where      |
      |                            |  referee_email matches]         |
      |                            | [Store in round_assignments DB] |
      |                            |                                 |
      |<---------------------------|                                 |
      | RESPONSE_GROUP_ASSIGNMENT  |                                 |
```

### 6.3 Game Execution Flow (Reformed)

The orchestrator owns the round lifecycle with three operations:

**start_round(gprm)**
1. If same round already active -> skip (idempotent)
2. If different game active -> abort_current_game("new_round_started")
3. Create new GMC with GPRM
4. Call AI warmup callback, build Q21WARMUPCALL envelopes
5. Advance GMC phase to WARMUP_SENT

**abort_current_game(reason)**
1. Snapshot per-player state via get_state_snapshot()
2. Score eligible players (who submitted guesses but not yet scored)
3. Build MATCH_RESULT_REPORT with status="aborted", player_states, last_actor
4. Clear current_game, transition state machine GAME_ABORTED -> RUNNING

**complete_game()**
1. Called when GMC reports is_complete() after routing a player message
2. Build GameResult with status="completed"
3. Clear current_game, transition GAME_COMPLETE -> RUNNING

GMC is a pure game engine -- it only routes player messages (Q21WARMUPRESPONSE, Q21QUESTIONSBATCH, Q21GUESSSUBMISSION). Round initiation is handled by the orchestrator via warmup_initiator.py.

---

## 7. RLGM State Machine

```
+-----------------+
| INIT_START_STATE|<---------- REGISTRATION_REJECTED
+--------+--------+<---------- RESET (from any state)
         | SEASON_START
         v
+-------------------------+
| WAITING_FOR_CONFIRMATION| --> Send SEASON_REGISTRATION_REQUEST
+--------+----------------+
         | REGISTRATION_ACCEPTED
         v
+------------------------+
| WAITING_FOR_ASSIGNMENT |
+--------+---------------+
         | ASSIGNMENT_RECEIVED
         v
+-----------------+
|     RUNNING     |<---------------------+
+--------+--------+                      |
         | ROUND_START                   |
         v                               |
+-----------------+                      |
|     IN_GAME     | (GMC executing)      |
+--------+--------+                      |
         | GAME_COMPLETE | GAME_ABORTED  |
         | (Send MATCH_RESULT_REPORT)    |
         +-------------------------------+
         |
         | SEASON_END (from RUNNING)
         v
+-----------------+
|    COMPLETED    |
+-----------------+

Special transitions (not shown above):
- PAUSE: Any state → PAUSED (saves current state)
- CONTINUE: PAUSED → saved state (resume)
- RESET: Any state → INIT_START_STATE
```

---

## 8. Database Schema

SQLite schema defined in `_rlgm/schema.sql`:

```sql
-- Season registration tracking
CREATE TABLE IF NOT EXISTS referee_seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL UNIQUE,
    league_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending, registered, active, completed, rejected
    registered_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Match assignments per round
CREATE TABLE IF NOT EXISTS round_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    round_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    player1_id TEXT NOT NULL,
    player1_email TEXT NOT NULL,
    player2_id TEXT NOT NULL,
    player2_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending, in_progress, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(season_id, round_number, match_id)
);

-- Completed game results
CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL,
    round_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    winner_id TEXT,
    is_draw INTEGER NOT NULL DEFAULT 0,
    player1_id TEXT NOT NULL,
    player1_score INTEGER NOT NULL,
    player2_id TEXT NOT NULL,
    player2_score INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reported_at TIMESTAMP,
    UNIQUE(season_id, match_id)
);

-- Broadcast deduplication
CREATE TABLE IF NOT EXISTS broadcasts_received (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broadcast_id TEXT NOT NULL UNIQUE,
    message_type TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed INTEGER NOT NULL DEFAULT 1
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_assignments_season
    ON round_assignments(season_id);
CREATE INDEX IF NOT EXISTS idx_assignments_round
    ON round_assignments(season_id, round_number);
CREATE INDEX IF NOT EXISTS idx_results_season
    ON match_results(season_id);
CREATE INDEX IF NOT EXISTS idx_broadcasts_type
    ON broadcasts_received(message_type);
```

---

## 9. Change History

### 9.1 New Files (Message System Reform v2.0.0)

| File | Purpose |
|------|---------|
| `_rlgm/warmup_initiator.py` | Builds warmup calls for new rounds (extracted from orchestrator) |
| `_rlgm/abort_handler.py` | Abort scoring, winner determination, score building |
| `_gmc/snapshot.py` | Per-player state snapshot builder for abort reporting |

### Removed Code
| What | Where |
|------|-------|
| `handle_new_round()` function | Deleted from `_gmc/handlers/warmup.py` |
| `initiate_game()` method | Deleted from `_gmc/gmc.py` |
| `BROADCAST_NEW_LEAGUE_ROUND` route | Removed from `_gmc/router.py` |

### Audit Fixes (v2.1.0)

| Fix | File(s) | Description |
|-----|---------|-------------|
| Resilient abort callback | `abort_handler.py` | Uses `execute_callback_safe` with try/except; callback failures produce zero-score defaults |
| None guards | `snapshot.py`, `abort_handler.py`, `warmup_initiator.py` | All player access points guard against `None` players |
| Phase tracking accuracy | `questions.py`, `scoring.py`, `state.py` | Phase advances correctly: `QUESTIONS_COLLECTING` after first player, `ANSWERS_SENT` after both; `GUESSES_COLLECTING` after first score |
| Context type docs | `types.py` | TypedDicts updated to document wrapped `{dynamic, service}` context structure |
| Assignment validation | `handler_new_round.py` | Required fields validated before GPRM creation; missing fields prevent round start |

---

## 10. Interface Between RLGM and GMC

### Orchestrator Round Lifecycle

The orchestrator owns round lifecycle with three operations:

```python
class RLGMOrchestrator:
    def start_round(self, gprm: GPRM) -> List[Tuple[dict, str, str]]:
        """Start a new round: create GMC, send warmup calls.

        1. Skip if same round already active (idempotent)
        2. Abort current game if different round active
        3. Create new GMC with GPRM
        4. Call warmup_initiator to build Q21WARMUPCALL envelopes
        """

    def abort_current_game(self, reason: str) -> List[Tuple[dict, str, str]]:
        """Force-complete current game with abort status.

        1. Snapshot per-player state via get_state_snapshot()
        2. Score players who submitted guesses (via abort_handler)
           - Uses execute_callback_safe (resilient: callback failures
             produce zero-score defaults instead of crashing)
        3. Build MATCH_RESULT_REPORT with status="aborted"
        4. Transition state machine GAME_ABORTED → RUNNING
        """

    def complete_game(self) -> None:
        """Handle natural game completion.

        Called when GMC reports is_complete() after routing a player message.
        Transitions state machine GAME_COMPLETE → RUNNING.
        """
```

### GMC as Pure Game Engine

GMC only routes player messages — it does not initiate rounds or send warmup calls:

```python
class GameManagementCycle:
    def __init__(self, gprm: GPRM, ai: RefereeAI, config: dict): ...

    def route_message(self, message_type, body, sender_email) -> List[Tuple]:
        """Route player messages: Q21WARMUPRESPONSE, Q21QUESTIONSBATCH, Q21GUESSSUBMISSION."""

    def is_complete(self) -> bool:
        """True when game reaches MATCH_REPORTED phase."""

    def get_result(self) -> Optional[GameResult]:
        """Build GameResult from current state."""

    def get_state_snapshot(self) -> dict:
        """Per-player state snapshot for abort reporting.
        Returns: {game_id, phase, player1: {...}, player2: {...}}
        """
```

### GMC builds GameResult:

```python
# In GMC (gmc.py)
def _build_game_result(self) -> GameResult:
    p1, p2 = self.state.player1, self.state.player2

    return GameResult(
        game_id=self.gprm.game_id,
        match_id=self.gprm.match_id,
        round_id=self.gprm.round_id,
        season_id=self.gprm.season_id,
        player1=PlayerScore(
            player_id=p1.participant_id,
            player_email=p1.email,
            score=p1.league_points,
            questions_answered=len(p1.questions) if p1.questions else 0,
            correct_answers=0,
        ),
        player2=PlayerScore(...),
        winner_id=winner_id,
        is_draw=is_draw,
    )
```

---

## 10.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **LM Communication** | RLGM handles all | Clean separation - GMC only handles player messages |
| **Email Client** | Single shared instance | Simpler architecture, one connection to Gmail |
| **PRD Location** | `q21-referee-sdk/docs/` | Keep documentation with the SDK source |

---

## 11. Student-Facing API (Unchanged)

Students continue to use the same API:

```python
from q21_referee import RLGMRunner, RefereeAI

class MyRefereeAI(RefereeAI):
    def get_warmup_question(self, ctx): ...
    def get_round_start_info(self, ctx): ...
    def get_answers(self, ctx): ...
    def get_score_feedback(self, ctx): ...

# Required config (OAuth credentials loaded from files)
config = {
    "referee_id": "R001",                            # Required
    "league_manager_email": "league@example.com",    # Required
    "credentials_path": "credentials.json",          # OAuth credentials
    "token_path": "token.json",                      # OAuth token (auto-created)
    "league_id": "LEAGUE001",
    "group_id": "my-group",                          # Optional metadata
    "poll_interval_seconds": 5,
}
# Note: referee_email is set automatically from OAuth credentials
# Assignment filtering uses referee_email (not group_id)

runner = RLGMRunner(config=config, ai=MyRefereeAI())
runner.run()  # RLGM handles everything else!
```

---

## 12. Hidden Implementation (RLGM Integration)

Inside `RLGMRunner` (`rlgm_runner.py`):

```python
class RLGMRunner:
    def __init__(self, config, ai):
        self.email_client = EmailClient(...)
        self.orchestrator = RLGMOrchestrator(config=config, ai=ai)

    def _route_message(self, message_type: str, body: dict,
                       sender: str) -> List[Tuple[dict, str, str]]:
        outgoing = []

        if is_lm_message(message_type):
            result = self.orchestrator.handle_lm_message(body)
            if result:
                lm_email = self.config.get("league_manager_email", "")
                response_type = result.get("message_type", "RESPONSE")
                subject = build_subject(
                    role="REFEREE", email=self.email_client.address,
                    message_type=response_type,
                    tx_id=result.get("message_id"),
                )
                outgoing.append((result, subject, lm_email))
            # Collect pending messages (warmup calls, abort reports)
            outgoing.extend(self.orchestrator.get_pending_outgoing())

        elif is_player_message(message_type):
            outgoing = self.orchestrator.route_player_message(
                message_type, body, sender)

        return outgoing
```

The runner also manages protocol logger context (game_id formatting per message type) and sends all outgoing messages via `EmailClient`.

---

## 13. Implementation Plan

### Phase 1: RLGM Core (Session 1)
1. Create `_rlgm/` directory structure
2. Copy and adapt state machine from GmailAsReferee
3. Implement GPRM and GameResult dataclasses
4. Create broadcast router skeleton

### Phase 2: Handlers (Session 2)
1. Implement BROADCAST_START_SEASON handler
2. Implement SEASON_REGISTRATION_RESPONSE handler
3. Implement BROADCAST_ASSIGNMENT_TABLE handler
4. Implement BROADCAST_NEW_LEAGUE_ROUND handler

### Phase 3: GMC Integration (Session 3)
1. Refactor GMC to accept GPRM input
2. Refactor GMC to return GameResult output
3. Integrate RLGM orchestrator with GMC

### Phase 4: Database (Session 4)
1. Add database tables
2. Implement repositories
3. Add persistence layer

### Phase 5: Testing (Session 5)
1. Unit tests for each handler
2. Integration tests for RLGM + GMC flow
3. End-to-end test with mock League Manager

---

## 14. File Structure

```
q21-referee-sdk/
├── src/q21_referee/
│   ├── __init__.py              # Public API exports
│   ├── __main__.py              # Entry point for `python -m q21_referee`
│   ├── callbacks.py             # RefereeAI abstract class (student implements)
│   ├── runner.py                # RefereeRunner (single-game mode)
│   ├── rlgm_runner.py           # RLGMRunner (season mode, default)
│   ├── types.py                 # TypedDict definitions for callbacks
│   ├── errors.py                # Custom exception classes
│   ├── cli.py                   # Command-line interface
│   ├── demo_ai.py               # Pre-built DemoAI implementation
│   ├── _runner_config.py        # Configuration validation
│   │
│   ├── _gmc/                    # GMC Layer (pure game engine)
│   │   ├── __init__.py
│   │   ├── gmc.py               # GameManagementCycle wrapper
│   │   ├── state.py             # GameState, GamePhase, PlayerState
│   │   ├── router.py            # Player message router (no broadcast routes)
│   │   ├── envelope_builder.py  # Protocol message construction
│   │   ├── context_builder.py   # Callback context building
│   │   ├── callback_executor.py # Callback execution with timeouts
│   │   ├── validator.py         # Protocol validation
│   │   ├── snapshot.py          # Per-player state snapshot (abort reporting)
│   │   └── handlers/
│   │       ├── __init__.py
│   │       ├── warmup.py        # handle_warmup_response only
│   │       ├── questions.py
│   │       └── scoring.py
│   │
│   ├── _rlgm/                   # RLGM Layer (season orchestration)
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Round lifecycle: start_round, abort, complete
│   │   ├── state_machine.py     # RLGM state machine (incl. pause/resume/reset)
│   │   ├── enums.py             # RLGMState, RLGMEvent (incl. GAME_ABORTED)
│   │   ├── gprm.py              # GPRM frozen dataclass
│   │   ├── game_result.py       # GameResult + PlayerScore dataclasses
│   │   ├── broadcast_router.py  # Route LM messages to handlers
│   │   ├── response_builder.py  # Build LM responses
│   │   ├── warmup_initiator.py  # Build warmup calls for new rounds
│   │   ├── abort_handler.py     # Abort scoring, winner determination
│   │   ├── schema.sql           # SQLite database schema
│   │   ├── handler_base.py      # Base handler class
│   │   ├── handler_start_season.py
│   │   ├── handler_registration_response.py
│   │   ├── handler_assignment.py
│   │   ├── handler_new_round.py # Builds GPRM from assignments (with validation)
│   │   ├── handler_end_round.py # Signals abort for active round
│   │   ├── handler_end_season.py
│   │   ├── handler_keep_alive.py
│   │   ├── handler_critical_pause.py
│   │   ├── handler_critical_reset.py
│   │   ├── handler_round_results.py
│   │   ├── database.py          # SQLite persistence
│   │   ├── repo_assignments.py
│   │   ├── repo_broadcasts.py
│   │   └── repo_seasons.py
│   │
│   └── _shared/                 # Shared utilities
│       ├── __init__.py
│       ├── email_client.py      # Gmail OAuth client
│       ├── logging_config.py    # Colored logging setup
│       ├── protocol.py          # Protocol constants, envelope building
│       └── protocol_logger.py   # Structured protocol message logging
│
├── docs/
│   └── prd-rlgm.md              # This PRD
│
└── examples/
```

---

## 15. Summary

The RLGM provides the missing link between the League Manager and the GMC:

| Component | Responsibility |
|-----------|----------------|
| **RLGM** | Season lifecycle, assignments, round management, LM communication |
| **GMC** | Single game execution, player communication, 4 callbacks |
| **Student** | Implement 4 callbacks in RefereeAI subclass |

This architecture:
- Keeps student API simple (4 callbacks)
- Hides season/league complexity in RLGM
- Reuses GmailAsReferee code with minimal changes
- Maintains full protocol compatibility with League Manager

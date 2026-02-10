# PRD: RLGM - Referee League Game Manager

**Version:** 1.0.0
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

**Gap Analysis:**

| Message | GMC Status | Required |
|---------|------------|----------|
| BROADCAST_START_SEASON | No handler | Yes |
| SEASON_REGISTRATION_RESPONSE | No handler | Yes |
| BROADCAST_ASSIGNMENT_TABLE | No handler | Yes |
| BROADCAST_NEW_LEAGUE_ROUND | Has handler | Yes |
| BROADCAST_END_LEAGUE_ROUND | No handler | Yes |
| BROADCAST_END_SEASON | No handler | Yes |
| LEAGUE_COMPLETED | No handler | Yes |
| Q21WARMUPRESPONSE | Has handler | Yes |
| Q21QUESTIONSBATCH | Has handler | Yes |
| Q21GUESSSUBMISSION | Has handler | Yes |

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
|  |   - winner_id, is_draw, scores[], feedback                          ||
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
@dataclass
class GPRM:
    """Game Parameters passed from RLGM to GMC for each game."""

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
class GameResult:
    """Result returned from GMC to RLGM after game completion."""

    game_id: str
    match_id: str
    status: str             # "completed" | "aborted" | "timeout"

    winner_id: Optional[str]  # None if draw
    is_draw: bool

    scores: List[PlayerScore]

@dataclass
class PlayerScore:
    participant_id: str
    email: str
    league_points: int      # 0-3
    private_score: float    # 0-100
    breakdown: ScoreBreakdown
    feedback: PlayerFeedback
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
      |                            |  group_id matches]              |
      |                            | [Store in round_assignments DB] |
      |                            |                                 |
      |<---------------------------|                                 |
      | RESPONSE_GROUP_ASSIGNMENT  |                                 |
```

### 6.3 Game Execution Flow

```
LEAGUE MANAGER                    RLGM                              GMC
      |                            |                                 |
      | BROADCAST_NEW_LEAGUE_ROUND |                                 |
      |--------------------------->|                                 |
      |                            | [Query assignments for round]   |
      |                            | [For each assigned game:]       |
      |                            |                                 |
      |                            | [Build GPRM from assignment]    |
      |                            |-------------------------------->|
      |                            |         start_game(GPRM)        |
      |                            |                                 |
      |                            |         [GMC manages game]      |
      |                            |         [Sends Q21 messages     |
      |                            |          to players directly]   |
      |                            |                                 |
      |                            |<--------------------------------|
      |                            |       GameResult                |
      |                            |                                 |
      |                            | [Store result in DB]            |
      |<---------------------------|                                 |
      |    MATCH_RESULT_REPORT     |                                 |
```

---

## 7. RLGM State Machine

```
+-----------------+
| INIT_START_STATE|
+--------+--------+
         | BROADCAST_START_SEASON
         v
+-------------------------+
| WAITING_FOR_CONFIRMATION| --> Send SEASON_REGISTRATION_REQUEST
+--------+----------------+
         | SEASON_REGISTRATION_RESPONSE (accepted)
         v
+------------------------+
| WAITING_FOR_ASSIGNMENT |
+--------+---------------+
         | BROADCAST_ASSIGNMENT_TABLE
         v
+-----------------+
|     RUNNING     |<---------------------+
+--------+--------+                      |
         | BROADCAST_NEW_LEAGUE_ROUND    |
         v                               |
+-----------------+                      |
|     IN_GAME     | (GMC executing)      |
+--------+--------+                      |
         | Game complete                 |
         | (Send MATCH_RESULT_REPORT)    |
         +-------------------------------+
```

---

## 8. Database Schema (from GmailAsReferee)

### Tables to Reuse:

```sql
-- Season registration tracking
CREATE TABLE referee_seasons (
    season_id VARCHAR PRIMARY KEY,
    league_id VARCHAR,
    registration_status VARCHAR,  -- PENDING, CONFIRMED, REJECTED
    broadcast_id VARCHAR,
    created_at TIMESTAMP
);

-- Game assignments per round
CREATE TABLE round_assignments (
    id SERIAL PRIMARY KEY,
    season_id VARCHAR,
    game_id VARCHAR,              -- 7-digit format
    round_number INTEGER,
    player1_email VARCHAR,
    player2_email VARCHAR,
    referee_email VARCHAR,
    assignment_status VARCHAR,    -- PENDING, IN_PROGRESS, COMPLETED
    UNIQUE(season_id, game_id)
);

-- Active matches being played
CREATE TABLE assigned_matches (
    match_id VARCHAR PRIMARY KEY,
    season_id VARCHAR,
    game_id VARCHAR,
    round_number INTEGER,
    player_a_email VARCHAR,
    player_b_email VARCHAR,
    status VARCHAR,               -- PENDING, IN_PROGRESS, COMPLETED
    created_at TIMESTAMP
);

-- Broadcast deduplication
CREATE TABLE broadcasts_received (
    broadcast_id VARCHAR PRIMARY KEY,
    message_type VARCHAR,
    payload JSONB,
    processed_at TIMESTAMP
);
```

---

## 9. Files to Copy from GmailAsReferee

### Core RLGM Components:

| Source File | Target Location | Purpose |
|-------------|-----------------|---------|
| `src/domain/services/broadcast_router.py` | `src/q21_referee/_rlgm/broadcast_router.py` | Route LM messages |
| `src/domain/services/broadcast_handlers_season.py` | `src/q21_referee/_rlgm/handlers_season.py` | Season handlers |
| `src/domain/services/broadcast_handlers_lifecycle.py` | `src/q21_referee/_rlgm/handlers_lifecycle.py` | Round handlers |
| `src/domain/services/broadcast_assignment_handler.py` | `src/q21_referee/_rlgm/handlers_assignment.py` | Assignment handler |
| `src/domain/services/assignment_handler.py` | `src/q21_referee/_rlgm/assignment_handler.py` | Parse assignments |
| `src/domain/services/referee_state_machine.py` | `src/q21_referee/_rlgm/state_machine.py` | RLGM state machine |
| `src/domain/services/round_start_service.py` | `src/q21_referee/_rlgm/round_start_service.py` | Start games |
| `src/domain/models/referee_state.py` | `src/q21_referee/_rlgm/models.py` | State enums |

### Shared Components:

| Source File | Target Location | Purpose |
|-------------|-----------------|---------|
| `sdk/protocol_sdk/messages_league.py` | Keep in `sdk/` | LM message schemas |
| `src/domain/models/envelope.py` | `src/q21_referee/_rlgm/envelope.py` | Message envelope |
| `src/domain/services/response_builder.py` | `src/q21_referee/_rlgm/response_builder.py` | Build responses |

---

## 10. Interface Between RLGM and GMC

### RLGM calls GMC:

```python
# In RLGM
class RLGMOrchestrator:
    def start_game(self, gprm: GPRM, ai: RefereeAI) -> GameResult:
        """
        Start a single game managed by GMC.

        RLGM passes:
          - GPRM (game parameters)
          - RefereeAI (student's callback implementation)

        GMC returns:
          - GameResult (winner, scores, feedback)
        """
        # Build GMC config from GPRM
        config = {
            "player1_email": gprm.player1_email,
            "player1_id": gprm.player1_id,
            "player2_email": gprm.player2_email,
            "player2_id": gprm.player2_id,
            "season_id": gprm.season_id,
            "game_id": gprm.game_id,
            "match_id": gprm.match_id,
            # ... other config from self.config
        }

        # Create GMC instance and run game
        gmc = GameManagementCycle(config=config, ai=ai)
        result = gmc.run_single_game()

        return result
```

### GMC returns GameResult:

```python
# In GMC (_message_router.py)
def _build_match_result(self) -> GameResult:
    """
    Build GameResult to return to RLGM.

    NOTE: GMC does NOT send MATCH_RESULT_REPORT.
    RLGM handles ALL League Manager communication.
    """
    p1, p2 = self.state.player1, self.state.player2

    winner_id = self._determine_winner(p1, p2)

    return GameResult(
        game_id=self.state.game_id,
        match_id=self.state.match_id,
        status="completed",
        winner_id=winner_id,
        is_draw=(winner_id is None),
        scores=[
            PlayerScore(
                participant_id=p1.participant_id,
                email=p1.email,
                league_points=p1.league_points,
                private_score=p1.private_score,
                breakdown=p1.breakdown,
                feedback=p1.feedback,
            ),
            PlayerScore(
                participant_id=p2.participant_id,
                email=p2.email,
                league_points=p2.league_points,
                private_score=p2.private_score,
                breakdown=p2.breakdown,
                feedback=p2.feedback,
            ),
        ],
    )
```

### RLGM sends MATCH_RESULT_REPORT:

```python
# In RLGM (orchestrator.py)
def _send_match_result(self, result: GameResult) -> None:
    """
    RLGM sends MATCH_RESULT_REPORT to League Manager.
    All LM communication is centralized in RLGM.
    """
    envelope = self.response_builder.build_match_result(
        game_id=result.game_id,
        match_id=result.match_id,
        winner_id=result.winner_id,
        is_draw=result.is_draw,
        scores=result.scores,
    )
    self.email_client.send(
        to=self.config["league_manager_email"],
        subject=envelope["subject"],
        body=envelope["body"],
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
from q21_referee import RefereeRunner, RefereeAI

class MyRefereeAI(RefereeAI):
    def get_warmup_question(self, ctx): ...
    def get_round_start_info(self, ctx): ...
    def get_answers(self, ctx): ...
    def get_score_feedback(self, ctx): ...

# Simple config (no more hardcoded player emails!)
config = {
    "referee_email": "my-referee@gmail.com",
    "referee_password": "app-password",
    "referee_id": "R001",
    "league_manager_email": "league@example.com",
    "league_id": "LEAGUE001",
    "group_id": "my-group",  # NEW: Used for assignment filtering
    "poll_interval_seconds": 5,
}

runner = RefereeRunner(config=config, ai=MyRefereeAI())
runner.run()  # RLGM handles everything else!
```

---

## 12. Hidden Implementation (RLGM Integration)

Inside `RefereeRunner.run()`:

```python
def run(self):
    """
    Main event loop (hidden from students).

    Internally uses RLGM for season management
    and GMC for individual game execution.
    """
    # Initialize RLGM
    self.rlgm = RLGMOrchestrator(
        config=self.config,
        ai=self.ai,
        email_client=self.email_client,
        db=self.database,
    )

    # Main loop
    while self._running:
        messages = self.email_client.poll()

        for msg in messages:
            message_type = msg.get("message_type")

            # RLGM handles League Manager messages
            if self._is_league_manager_message(message_type):
                self.rlgm.handle_message(msg)

            # GMC handles player messages (via current game instance)
            elif self._is_player_message(message_type):
                if self.rlgm.current_game:
                    self.rlgm.current_game.handle_message(msg)

        time.sleep(self.poll_interval)
```

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
│   ├── __init__.py              # Public API (unchanged)
│   ├── callbacks.py             # RefereeAI base class (unchanged)
│   ├── runner.py                # RefereeRunner (updated to use RLGM)
│   ├── types.py                 # TypedDict schemas (unchanged)
│   ├── errors.py                # Exceptions (unchanged)
│   │
│   ├── _gmc/                    # GMC (renamed from root)
│   │   ├── __init__.py
│   │   ├── message_router.py    # Current _message_router.py
│   │   ├── state.py             # Current _state.py
│   │   ├── envelope_builder.py  # Current _envelope_builder.py
│   │   ├── context_builder.py   # Current _context_builder.py
│   │   ├── callback_executor.py # Current _callback_executor.py
│   │   └── validator.py         # Current _validator.py
│   │
│   ├── _rlgm/                   # NEW: RLGM components
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Main RLGM logic
│   │   ├── state_machine.py     # Season state machine
│   │   ├── broadcast_router.py  # Route LM messages
│   │   ├── handlers_season.py   # Season handlers
│   │   ├── handlers_lifecycle.py# Round handlers
│   │   ├── handlers_assignment.py# Assignment handler
│   │   ├── response_builder.py  # Build LM responses
│   │   ├── models.py            # GPRM, GameResult, enums
│   │   └── database.py          # DB repositories
│   │
│   └── _shared/                 # Shared utilities
│       ├── email_client.py      # Current _email_client.py
│       └── logging_config.py    # Current _logging_config.py
│
├── docs/
│   ├── prd-rlgm.md              # This PRD
│   └── comparison-gmailasreferee-vs-rlgm-gmc.md
│
└── examples/                    # (unchanged)
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

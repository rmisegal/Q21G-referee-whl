# Message System Reform — Round Lifecycle & Orchestrator Refactor

Version: 1.0.0

## Pre-Implementation Checklist

**CRITICAL: Before writing any code, read and follow these:**
- [ ] Read `CLAUDE.md` in project root — all development principles apply
- [ ] Follow TDD: write tests first, then implement
- [ ] 150-line file limit: if a file exceeds this, split it
- [ ] Update `docs/prd-rlgm.md` after every module change (increment PRD version)
- [ ] Every source file must have `# Area:` and `# PRD:` header comments
- [ ] No hardcoded secrets or paths — all values from `config.json` or env vars

---

## Problem Statement

The current `BROADCAST_NEW_LEAGUE_ROUND` handling has five concrete bugs:

1. **No game cleanup.** `orchestrator.start_game()` silently overwrites `self.current_game`. In-flight games are garbage collected — no `GameResult`, no `MATCH_RESULT_REPORT`, no state machine transition.
2. **Duplicate round-start logic.** `_gmc/handlers/warmup.py:handle_new_round()` handles the broadcast inside GMC, but `orchestrator.handle_lm_message()` also has special-case logic for the same message. Round-start is split across two layers.
3. **No round awareness.** No idempotency guard — if the same round broadcast arrives twice, a new game is created both times. No out-of-order protection.
4. **`handle_new_round` in GMC resets wrong state.** It calls `reset_for_new_round()` on a freshly created GameState, and double-sets `round_id`/`round_number`/`auth_token`.
5. **`BROADCAST_END_LEAGUE_ROUND` does nothing.** The handler only logs. It doesn't check if a game is still active, doesn't abort, doesn't transition the state machine.

---

## Design Decisions (User-Approved)

| Decision | Choice |
|----------|--------|
| Game cleanup on new round | Force-complete with per-player state snapshots in MATCH_RESULT_REPORT |
| Round data source | Round broadcast + stored assignments (current approach, made robust) |
| RLGM-GMC boundary | Orchestrator owns lifecycle, GMC is pure game engine |
| Duplicate logic | Remove all duplicates |
| Player notification on abort | Send Q21SCOREFEEDBACK to eligible players + MATCH_RESULT_REPORT to LGM |
| Scope | Message handling reform only (gatekeeper/malfunction in follow-up session) |
| Deadline grace periods | Configurable in config.json (time-based, not message retries) — for future malfunction ticket system |

---

## Architecture Overview

### Before (current)

```
BROADCAST_NEW_LEAGUE_ROUND
    → orchestrator.handle_lm_message()
        → handler_new_round.handle() → builds GPRM
        → orchestrator.start_game(gprm) ← silently overwrites current_game
        → current_game.initiate_game() ← GMC builds warmup calls from synthetic broadcast
            → _gmc/handlers/warmup.handle_new_round() ← duplicate, resets blank state
```

### After (reformed)

```
BROADCAST_NEW_LEAGUE_ROUND
    → orchestrator.handle_lm_message()
        → handler_new_round.handle() → builds GPRM
        → orchestrator.abort_current_game() ← if game active: snapshot, score, report, clean up
        → orchestrator.start_round(gprm) ← creates GMC, calls AI warmup callback, builds envelopes
```

---

## Section 1: Orchestrator Round Lifecycle

The orchestrator becomes the single authority for round lifecycle with three operations:

### `start_round(gprm: GPRM) → List[outgoing]`

1. Call `abort_current_game()` if `self.current_game is not None`
2. Update `self.current_round_number` from GPRM
3. Create new `GameManagementCycle(gprm, ai, config)`
4. Call `ai.get_warmup_question(ctx)` — orchestrator builds the callback context
5. Use `EnvelopeBuilder` to build `Q21WARMUPCALL` for both players
6. Advance GMC's `GameState` phase to `WARMUP_SENT`
7. Queue warmup messages in `_pending_outgoing`
8. Transition state machine to `IN_GAME`

### `abort_current_game() → List[outgoing]`

1. Snapshot per-player state via `current_game.get_state_snapshot()`
2. For players who submitted guesses but haven't received scores:
   - Call `ai.get_score_feedback(ctx)`
   - Build `Q21SCOREFEEDBACK` envelope
   - Add to outgoing
3. Build partial `GameResult` with `status="aborted"`, `abort_reason`, `player_states`
4. Build `MATCH_RESULT_REPORT` including per-player state snapshots and `last_actor`
5. Add to outgoing
6. Set `self.current_game = None`
7. Transition state machine with `GAME_ABORTED` event
8. Return outgoing messages

### `complete_game()` (renamed from `_on_game_complete`)

- Invoked only when `current_game.is_complete()` returns True after routing a player message
- Builds `GameResult` with `status="completed"` (natural completion)
- Transitions state machine with `GAME_COMPLETE` event
- Sets `self.current_game = None`

---

## Section 2: GMC as Pure Game Engine

### Keeps
- `route_message(message_type, body, sender_email)` → processes player messages only
- `is_complete()` / `get_result()` → reports natural game completion
- `state` (GameState) — internal phase tracking
- Handlers: `handle_warmup_response`, `handle_questions`, `handle_guess`

### Loses
- `initiate_game()` — moves to orchestrator
- `handle_new_round()` in `_gmc/handlers/warmup.py` — deleted entirely

### Gains
- `get_state_snapshot() → dict` — serializable per-player state for abort reporting:

```python
{
    "game_id": "0101001",
    "phase": "questions_collecting",
    "player1": {
        "email": "player1@example.com",
        "participant_id": "P001",
        "phase_reached": "questions_submitted",
        "scored": False,
        "last_actor": "player1"    # player1 submitted questions, referee hadn't answered yet
    },
    "player2": {
        "email": "player2@example.com",
        "participant_id": "P002",
        "phase_reached": "warmup_answered",
        "scored": False,
        "last_actor": "referee"    # referee sent round start, player2 hasn't submitted questions
    }
}
```

### `last_actor` semantics
- `"referee"` — referee was the last to send a message to this player (player got stuck / didn't respond)
- `"player1"` / `"player2"` — the player was the last to act (referee/system hadn't processed their response yet)

---

## Section 3: GameResult Extensions

```python
@dataclass
class GameResult:
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

### MATCH_RESULT_REPORT payload additions

```json
{
    "status": "aborted",
    "abort_reason": "new_round_started",
    "player_states": {
        "player1": {
            "phase_reached": "warmup_answered",
            "scored": false,
            "last_actor": "referee"
        },
        "player2": {
            "phase_reached": "idle",
            "scored": false,
            "last_actor": "referee"
        }
    }
}
```

### Abort scoring rules
- Players who submitted guesses → run `get_score_feedback` callback, send `Q21SCOREFEEDBACK`
- Players who didn't reach guess phase → `league_points: 0`, `private_score: 0.0`
- Winner determination: same as normal (compare league_points), but `status="aborted"`

---

## Section 4: Handler Changes

### Deleted
- `_gmc/handlers/warmup.py` → `handle_new_round()` function

### Modified: `_gmc/handlers/warmup.py`
- Only keeps `handle_warmup_response()` (unchanged logic)

### Modified: `_gmc/router.py` (MessageRouter)
- Remove the `BROADCAST_NEW_LEAGUE_ROUND` route case
- GMC only routes: `Q21WARMUPRESPONSE`, `Q21QUESTIONSBATCH`, `Q21GUESSSUBMISSION`

### Modified: `_gmc/gmc.py`
- Remove `initiate_game()` method
- Add `get_state_snapshot()` method

### Modified: `_rlgm/orchestrator.py`
- Add `start_round()`, `abort_current_game()`
- Rename `_on_game_complete()` → `complete_game()`
- Add `current_round_number` tracking
- `handle_lm_message()`: abort-then-start logic for new round

### Modified: `_rlgm/handler_end_round.py`
- Returns signal to orchestrator when round ends while game is active → orchestrator calls `abort_current_game()`

### Modified: `_rlgm/enums.py`
- Add `RLGMEvent.GAME_ABORTED`

### Modified: `_rlgm/state_machine.py`
- Add transition: `IN_GAME → RUNNING` on `GAME_ABORTED`

### Modified: `_rlgm/game_result.py`
- Add `status`, `abort_reason`, `player_states` fields

### Modified: `_gmc/envelope_builder.py`
- `build_match_result()` accepts optional `status`, `abort_reason`, `player_states` params

### Unchanged
- `_runner_config.py` — message type filtering stays as-is
- `RLGMRunner` — polls, classifies, routes, sends (no structural changes)
- `_gmc/handlers/questions.py`, `_gmc/handlers/scoring.py`
- `BroadcastRouter`
- `_shared/` (email_client, protocol, logging)

---

## Section 5: State Machine Revision

### New event
```python
class RLGMEvent(Enum):
    # ... existing ...
    GAME_ABORTED = "GAME_ABORTED"
```

### Revised transitions
```python
TRANSITIONS = {
    # ... existing ...
    RLGMState.IN_GAME: {
        RLGMEvent.GAME_COMPLETE: RLGMState.RUNNING,   # natural completion
        RLGMEvent.GAME_ABORTED: RLGMState.RUNNING,    # force-complete on new round/end round
    },
}
```

### Round tracking
```python
# In orchestrator
self.current_round_number: Optional[int] = None
```
- Updated on every `BROADCAST_NEW_LEAGUE_ROUND`
- Idempotency: if incoming round_number == current_round_number, skip
- Logging: "Aborting round 2 game to start round 3"
- `BROADCAST_END_LEAGUE_ROUND`: if round matches current and game active → abort

---

## Section 6: Testing Strategy

### New test file: `test_orchestrator_lifecycle.py`

Tests for `start_round()`, `abort_current_game()`, `complete_game()`:

**Abort at each game phase:**
1. Abort during `WARMUP_SENT` (no player responded yet)
2. Abort during `WARMUP_SENT` (one player responded)
3. Abort during `ROUND_STARTED` (waiting for questions)
4. Abort during `QUESTIONS_COLLECTING` (one player submitted)
5. Abort during `GUESSES_COLLECTING` (one player submitted guess → needs scoring)
6. Abort during `SCORING_COMPLETE` (one scored, waiting for other's guess)
7. Game already `MATCH_REPORTED` → no-op

**Lifecycle tests:**
- Starting a new round while in-game aborts first
- Same round number arriving twice is idempotent (no duplicate game)
- `BROADCAST_END_LEAGUE_ROUND` aborts active game
- Abort produces correct `GameResult` with `status="aborted"`, `player_states`, `last_actor`
- Abort sends `Q21SCOREFEEDBACK` to players who submitted guesses
- Abort sends `MATCH_RESULT_REPORT` to LGM with full state

### Modified test files
- `test_orchestrator.py` — update for new lifecycle methods
- `test_gmc_wrapper.py` — remove `initiate_game()` tests, add `get_state_snapshot()` tests
- `test_handler_new_round.py` — update for handler no longer building warmup calls

---

## Post-Implementation Checklist

**CRITICAL: After implementation, verify these:**
- [ ] `docs/prd-rlgm.md` updated with all changes (version incremented)
- [ ] All modified source files have correct `# Area:` and `# PRD:` headers
- [ ] All Python files under 150 lines
- [ ] `pytest tests/` passes
- [ ] No hardcoded values introduced
- [ ] README sections updated if affected

---

## Future Work (Next Session)

This design creates a clean foundation for:
1. **Gatekeeper refactor** — consolidate scattered message filtering into a proper Gatekeeper module
2. **Malfunction detection** — lookup table routing, MALFUNCTION_REPORT filing, MALFUNCTION_DECISION handling
3. **Configurable deadline tracking** — time-based grace periods in config.json for malfunction ticket filing

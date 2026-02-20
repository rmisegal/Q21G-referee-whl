# Audit Issue Fixes Design

Version: 1.0.0

## Goal

Fix 7 real issues found during the wiring audit (1 critical, 2 high, 3 medium, 1 low). Issues span reform-introduced code and pre-existing patterns.

## Issue Summary

| # | File | Severity | Description |
|---|------|----------|-------------|
| 1 | abort_handler.py:33 | CRITICAL | Callback crash kills process during abort |
| 3 | snapshot.py:18 | HIGH | No None guard for players |
| 4 | abort_handler.py:63-74 | HIGH | No None guard for players |
| 5 | warmup_initiator.py:70 | MEDIUM | No None guard for players |
| 6 | types.py | MEDIUM | TypedDicts don't match wrapped context structure |
| 7 | questions.py:62, scoring.py:84 | MEDIUM | Phase advancement skips intermediate phases |
| 8 | handler_new_round.py:105-116 | LOW | Empty string defaults for missing fields |

Issue #2 was a false positive (orchestrator guards with `if player.guess is not None`).

## Design

### Issue #1: Resilient abort callback

**Problem:** `score_player_on_abort()` uses `execute_callback()` with default `terminate_on_error=True`. If `get_score_feedback` fails during abort, `log_and_terminate` kills the process and `MATCH_RESULT_REPORT` is never sent.

**Fix:** Replace `execute_callback()` with `execute_callback_safe()` (sets `terminate_on_error=False`). Wrap in try/except — on failure, log error and use default zero scores so abort completes gracefully.

```python
try:
    result = execute_callback_safe(
        callback_fn=ai.get_score_feedback,
        callback_name="score_feedback",
        ctx=callback_ctx,
        deadline_seconds=service["deadline_seconds"],
    )
except Exception as e:
    logger.error(f"Score callback failed during abort: {e}")
    result = {"league_points": 0, "private_score": 0.0, "breakdown": {}, "feedback": None}
```

### Issues #3-5: None guards for players

**Problem:** `snapshot.py`, `abort_handler.py`, and `warmup_initiator.py` access `state.player1`/`state.player2` without None checks. `GameState` types them as `Optional[PlayerState] = None`. Safe in current flow (GMC always initializes both from GPRM), but brittle.

**Fix (snapshot.py):** Return stub snapshot if player is None.
```python
def build_state_snapshot(game_id, state):
    return {
        "game_id": game_id,
        "phase": state.phase.value,
        "player1": _player_snapshot(state, state.player1) if state.player1 else _empty_snapshot(),
        "player2": _player_snapshot(state, state.player2) if state.player2 else _empty_snapshot(),
    }

def _empty_snapshot():
    return {"email": "", "participant_id": "", "phase_reached": "not_initialized", "scored": False, "last_actor": "none"}
```

**Fix (abort_handler.py):** Guard all three functions.
```python
def determine_abort_winner(gmc):
    p1, p2 = gmc.state.player1, gmc.state.player2
    if not p1 or not p2:
        return None
    ...

def is_abort_draw(gmc):
    p1, p2 = gmc.state.player1, gmc.state.player2
    if not p1 or not p2:
        return True  # No players = no winner = draw
    ...

def build_abort_scores(gmc):
    scores = []
    for player in [gmc.state.player1, gmc.state.player2]:
        if player is None:
            continue
        ...
```

**Fix (warmup_initiator.py):** Skip None players with warning.
```python
for player in [gmc.state.player1, gmc.state.player2]:
    if player is None:
        logger.warning("Skipping warmup for None player")
        continue
    ...
```

### Issue #6: Update types.py to match reality

**Problem:** Context builders return `{"dynamic": {...}, "service": {...}}` but TypedDicts in `types.py` show flat structures. Students use `ctx.get("dynamic", ctx)` at runtime.

**Fix:** Add `CallbackContext` wrapper TypedDict and `ServiceDefinition` TypedDict. Update existing context TypedDicts to document they represent the `dynamic` inner dict. Update module docstring.

### Issue #7: Accurate phase tracking

**Problem:** `questions.py:62` calls `advance_phase(ANSWERS_SENT)` after ONE player's questions are answered. `QUESTIONS_COLLECTING` and `GUESSES_COLLECTING` phases are never set. `scoring.py:84` sets `SCORING_COMPLETE` after first player scored (should be `GUESSES_COLLECTING`).

**Fix:**

Add `both_answers_sent()` to `GameState`:
```python
def both_answers_sent(self) -> bool:
    return (self.player1 is not None and self.player1.answers_sent
            and self.player2 is not None and self.player2.answers_sent)
```

In `questions.py`, replace line 62:
```python
if ctx.state.both_answers_sent():
    ctx.state.advance_phase(GamePhase.ANSWERS_SENT)
else:
    ctx.state.advance_phase(GamePhase.QUESTIONS_COLLECTING)
```

In `scoring.py`, replace line 84:
```python
if ctx.state.both_scores_sent():
    outgoing.extend(_build_match_result(ctx))
    ctx.state.advance_phase(GamePhase.MATCH_REPORTED)
else:
    ctx.state.advance_phase(GamePhase.GUESSES_COLLECTING)
```

### Issue #8: Validate assignment fields

**Problem:** `handler_new_round.py:105-116` uses `.get("field", "")` — silently creates GPRM with empty player emails/IDs. Warmup calls would go to empty addresses.

**Fix:** Validate required fields in `_build_gprm()`. Return None if critical fields are missing. Caller already handles None return.

```python
def _build_gprm(self, assignment, round_number, round_id):
    required = ["player1_email", "player1_id", "player2_email", "player2_id", "game_id"]
    missing = [f for f in required if not assignment.get(f)]
    if missing:
        logger.error(f"Assignment missing required fields: {missing}")
        return None
    ...
```

Update `handle()` to check for None GPRM:
```python
gprm = self._build_gprm(assignment, round_number, round_id)
if not gprm:
    return None
```

## Testing

Each fix gets TDD treatment: write failing test first, then implement.

- Issue #1: Test that abort completes gracefully when callback raises
- Issues #3-5: Test behavior with None players
- Issue #6: No runtime tests needed (type documentation only)
- Issue #7: Test phase progression for single and dual player flows
- Issue #8: Test that missing assignment fields prevent GPRM creation

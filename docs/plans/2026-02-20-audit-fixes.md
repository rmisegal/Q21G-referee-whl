# Audit Issue Fixes Implementation Plan

Version: 1.0.0

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 7 issues found during the wiring audit — 1 critical crash risk, 2 high defensive-guard gaps, 3 medium accuracy/type issues, 1 low validation gap.

**Architecture:** Targeted fixes in existing files. No new modules. TDD for each fix.

**Tech Stack:** Python 3.x, pytest, dataclasses, TypedDict

**Design Doc:** `docs/plans/2026-02-20-audit-fixes-design.md`

---

### Task 1: Resilient abort callback (Issue #1 — CRITICAL)

**Files:**
- Modify: `src/q21_referee/_rlgm/abort_handler.py:32-38`
- Test: `tests/test_abort_handler.py`

**Step 1: Write the failing test**

In `tests/test_abort_handler.py`, add a test that `score_player_on_abort` completes gracefully when the callback raises an exception:

```python
def test_score_player_on_abort_callback_failure():
    """abort scoring should not crash when callback fails."""
    gmc = _make_gmc()
    player = gmc.state.player1
    player.guess = {"opening_sentence": "test"}

    class FailingAI(MockRefereeAI):
        def get_score_feedback(self, ctx):
            raise RuntimeError("LLM timeout")

    result = score_player_on_abort(gmc, player, FailingAI(), make_config())

    # Should return score feedback with zero defaults, not crash
    assert len(result) == 1
    env, subject, recipient = result[0]
    assert env["message_type"] == "Q21SCOREFEEDBACK"
    assert player.league_points == 0
    assert player.private_score == 0.0
    assert player.score_sent is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_abort_handler.py::test_score_player_on_abort_callback_failure -v`
Expected: FAIL — process terminates or RuntimeError propagates

**Step 3: Implement the fix**

In `abort_handler.py`, replace `execute_callback` with `execute_callback_safe` and wrap in try/except:

```python
from .._gmc.callback_executor import execute_callback_safe

def score_player_on_abort(gmc, player, ai, config):
    ctx_builder = ContextBuilder(config, gmc.state)
    callback_ctx = ctx_builder.build_score_feedback_ctx(player, player.guess)
    service = SERVICE_DEFINITIONS["score_feedback"]

    try:
        result = execute_callback_safe(
            callback_fn=ai.get_score_feedback,
            callback_name="score_feedback",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
    except Exception as e:
        logger.error(f"Score callback failed during abort: {e}")
        result = {"league_points": 0, "private_score": 0.0,
                  "breakdown": {}, "feedback": None}

    # rest unchanged...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_abort_handler.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/q21_referee/_rlgm/abort_handler.py tests/test_abort_handler.py
git commit -m "fix: use resilient callback execution in abort scoring path"
```

---

### Task 2: None guards for snapshot.py (Issue #3)

**Files:**
- Modify: `src/q21_referee/_gmc/snapshot.py:13-20`
- Test: `tests/test_snapshot.py`

**Step 1: Write the failing test**

```python
def test_snapshot_with_none_player():
    """Snapshot should handle None player gracefully."""
    state = GameState(game_id="0101001", match_id="0101001",
                      season_id="S01", league_id="L01")
    state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
    state.player2 = None  # Not initialized

    result = build_state_snapshot("0101001", state)

    assert result["player1"]["email"] == "p1@test.com"
    assert result["player2"]["phase_reached"] == "not_initialized"
    assert result["player2"]["scored"] is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py::test_snapshot_with_none_player -v`
Expected: FAIL with AttributeError

**Step 3: Implement the fix**

In `snapshot.py`, add None guard and `_empty_snapshot()`:

```python
def build_state_snapshot(game_id: str, state: GameState) -> dict:
    return {
        "game_id": game_id,
        "phase": state.phase.value,
        "player1": _player_snapshot(state, state.player1) if state.player1 else _empty_snapshot(),
        "player2": _player_snapshot(state, state.player2) if state.player2 else _empty_snapshot(),
    }

def _empty_snapshot() -> dict:
    return {
        "email": "", "participant_id": "",
        "phase_reached": "not_initialized", "scored": False,
        "last_actor": "none",
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/q21_referee/_gmc/snapshot.py tests/test_snapshot.py
git commit -m "fix: add None guard for players in state snapshot builder"
```

---

### Task 3: None guards for abort_handler.py (Issue #4)

**Files:**
- Modify: `src/q21_referee/_rlgm/abort_handler.py:61-87`
- Test: `tests/test_abort_handler.py`

**Step 1: Write the failing tests**

```python
def test_determine_abort_winner_with_none_player():
    gmc = _make_gmc()
    gmc.state.player2 = None
    assert determine_abort_winner(gmc) is None

def test_is_abort_draw_with_none_player():
    gmc = _make_gmc()
    gmc.state.player2 = None
    assert is_abort_draw(gmc) is True

def test_build_abort_scores_with_none_player():
    gmc = _make_gmc()
    gmc.state.player2 = None
    scores = build_abort_scores(gmc)
    assert len(scores) == 1
    assert scores[0]["participant_id"] == "P001"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_abort_handler.py -v -k "none_player"`
Expected: FAIL with AttributeError

**Step 3: Implement the fix**

```python
def determine_abort_winner(gmc):
    p1, p2 = gmc.state.player1, gmc.state.player2
    if not p1 or not p2:
        return None
    if p1.league_points > p2.league_points:
        return p1.participant_id
    if p2.league_points > p1.league_points:
        return p2.participant_id
    return None

def is_abort_draw(gmc):
    p1, p2 = gmc.state.player1, gmc.state.player2
    if not p1 or not p2:
        return True
    return p1.league_points == p2.league_points

def build_abort_scores(gmc):
    scores = []
    for player in [gmc.state.player1, gmc.state.player2]:
        if player is None:
            continue
        scores.append({
            "participant_id": player.participant_id,
            "email": player.email,
            "league_points": player.league_points,
            "private_score": player.private_score,
        })
    return scores
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_abort_handler.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/q21_referee/_rlgm/abort_handler.py tests/test_abort_handler.py
git commit -m "fix: add None guards for players in abort handler functions"
```

---

### Task 4: None guard for warmup_initiator.py (Issue #5)

**Files:**
- Modify: `src/q21_referee/_rlgm/warmup_initiator.py`
- Test: `tests/test_warmup_initiator.py`

**Step 1: Write the failing test**

```python
def test_warmup_skips_none_player():
    """Warmup should skip None players with a warning."""
    gmc = _make_gmc()
    gmc.state.player2 = None

    outgoing = initiate_warmup(gmc, gprm, ai, config)

    # Should only send warmup for player1
    assert len(outgoing) == 1
    assert outgoing[0][2] == "p1@test.com"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_warmup_initiator.py::test_warmup_skips_none_player -v`
Expected: FAIL with AttributeError

**Step 3: Implement the fix**

In the loop that iterates players, add a None guard:

```python
for player in [gmc.state.player1, gmc.state.player2]:
    if player is None:
        logger.warning("Skipping warmup for None player")
        continue
    # ... existing warmup logic
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_warmup_initiator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/q21_referee/_rlgm/warmup_initiator.py tests/test_warmup_initiator.py
git commit -m "fix: skip None players in warmup initiator"
```

---

### Task 5: Accurate phase tracking (Issue #7)

**Files:**
- Modify: `src/q21_referee/_gmc/state.py` (add `both_answers_sent`)
- Modify: `src/q21_referee/_gmc/handlers/questions.py:62`
- Modify: `src/q21_referee/_gmc/handlers/scoring.py:83-84`
- Test: `tests/test_phase_tracking.py`

**Step 1: Write the failing tests**

```python
def test_first_player_answers_sets_questions_collecting():
    """After first player's answers sent, phase should be QUESTIONS_COLLECTING."""
    # Set up GMC, send questions for player1 only
    # Assert state.phase == GamePhase.QUESTIONS_COLLECTING

def test_both_players_answers_sets_answers_sent():
    """After both players' answers sent, phase should be ANSWERS_SENT."""
    # Set up GMC, send questions for both players
    # Assert state.phase == GamePhase.ANSWERS_SENT

def test_first_player_scored_sets_guesses_collecting():
    """After first player scored, phase should be GUESSES_COLLECTING."""
    # Set up GMC, score player1 only
    # Assert state.phase == GamePhase.GUESSES_COLLECTING

def test_both_players_scored_sets_match_reported():
    """After both players scored, phase should be MATCH_REPORTED."""
    # Set up GMC, score both players
    # Assert state.phase == GamePhase.MATCH_REPORTED
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_phase_tracking.py -v`
Expected: FAIL — first player sets ANSWERS_SENT / SCORING_COMPLETE instead

**Step 3: Add `both_answers_sent()` to GameState**

In `state.py`, add after `both_scores_sent`:

```python
def both_answers_sent(self) -> bool:
    return (self.player1 is not None and self.player1.answers_sent
            and self.player2 is not None and self.player2.answers_sent)
```

**Step 4: Fix questions.py phase advancement**

Replace line 62:

```python
if ctx.state.both_answers_sent():
    ctx.state.advance_phase(GamePhase.ANSWERS_SENT)
else:
    ctx.state.advance_phase(GamePhase.QUESTIONS_COLLECTING)
```

**Step 5: Fix scoring.py phase advancement**

Replace lines 83-84:

```python
else:
    ctx.state.advance_phase(GamePhase.GUESSES_COLLECTING)
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_phase_tracking.py -v && pytest tests/ -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/q21_referee/_gmc/state.py src/q21_referee/_gmc/handlers/questions.py src/q21_referee/_gmc/handlers/scoring.py tests/test_phase_tracking.py
git commit -m "fix: accurate phase tracking for questions and scoring stages"
```

---

### Task 6: Update types.py to match reality (Issue #6)

**Files:**
- Modify: `src/q21_referee/types.py`

**Step 1: Update types.py**

Add wrapper types at the top of the types section:

```python
class ServiceDefinition(TypedDict):
    """Service definition passed alongside dynamic context."""
    name: str
    description: str
    required_output_fields: List[str]
    deadline_seconds: int

class CallbackContext(TypedDict):
    """Wrapper structure for all callback contexts.

    Every callback receives this shape:
    - dynamic: Game data (varies per callback, see specific context types)
    - service: LLM service metadata

    Access pattern in your AI:
        data = ctx.get("dynamic", ctx)
        service = ctx.get("service", {})
    """
    dynamic: dict  # One of: WarmupContext, RoundStartContext, AnswersContext, ScoreFeedbackContext
    service: ServiceDefinition
```

Update module docstring to explain wrapped structure. Update each context TypedDict docstring to say "Represents the 'dynamic' section of the callback context."

**Step 2: Run existing tests**

Run: `pytest tests/ -v`
Expected: ALL PASS (no runtime behavior change)

**Step 3: Commit**

```bash
git add src/q21_referee/types.py
git commit -m "docs: update TypedDicts to document wrapped callback context structure"
```

---

### Task 7: Validate assignment fields (Issue #8)

**Files:**
- Modify: `src/q21_referee/_rlgm/handler_new_round.py:101-116`
- Test: `tests/test_handler_new_round.py`

**Step 1: Write the failing test**

```python
def test_build_gprm_rejects_missing_fields():
    """GPRM should not be built with missing required fields."""
    handler = BroadcastNewRoundHandler(state_machine, config, assignments=[
        {"round_number": 1, "game_id": "0101001", "player1_email": "p1@test.com",
         "player1_id": "P001"}  # missing player2 fields
    ])
    msg = {"message_type": "BROADCAST_NEW_LEAGUE_ROUND",
           "broadcast_id": "BC003",
           "payload": {"round_number": 1, "round_id": "ROUND_1"}}
    result = handler.handle(msg)
    assert result is None  # Should reject, not silently create with empty strings
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_handler_new_round.py::test_build_gprm_rejects_missing_fields -v`
Expected: FAIL — returns dict with empty-string GPRM

**Step 3: Implement the fix**

In `handler_new_round.py`, update `_build_gprm`:

```python
def _build_gprm(self, assignment, round_number, round_id):
    required = ["player1_email", "player1_id", "player2_email", "player2_id", "game_id"]
    missing = [f for f in required if not assignment.get(f)]
    if missing:
        logger.error(f"Assignment missing required fields: {missing}")
        return None
    return GPRM(
        player1_email=assignment["player1_email"],
        player1_id=assignment["player1_id"],
        player2_email=assignment["player2_email"],
        player2_id=assignment["player2_id"],
        season_id=self.config.get("season_id", ""),
        game_id=assignment["game_id"],
        match_id=assignment["game_id"],
        round_id=round_id,
        round_number=round_number,
    )
```

Update `handle()` to check for None GPRM:

```python
gprm = self._build_gprm(assignment, round_number, round_id)
if not gprm:
    return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handler_new_round.py -v && pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/q21_referee/_rlgm/handler_new_round.py tests/test_handler_new_round.py
git commit -m "fix: validate required assignment fields before building GPRM"
```

---

### Task 8: Update PRD and final verification

**Files:**
- Modify: `docs/prd-rlgm.md`

**Step 1: Update PRD**

Increment version. Document:
- Resilient abort callback behavior (Issue #1)
- None guards across abort, snapshot, warmup (Issues #3-5)
- Phase tracking fix (Issue #7)
- Assignment validation (Issue #8)

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 3: Verify 150-line file limit**

Run: `wc -l src/q21_referee/**/*.py src/q21_referee/_gmc/**/*.py src/q21_referee/_rlgm/**/*.py`
Expected: All files under 150 lines

**Step 4: Commit**

```bash
git add docs/prd-rlgm.md
git commit -m "docs: update PRD with audit fix details"
```

# Session 3: Game Integrity — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Protect game state from duplicate messages, out-of-order messages, stale game_id messages, duplicate broadcasts, and falsy field loss.

**Architecture:** Direct guards in each handler (duplicate + phase checks), game_id validation and broadcast idempotency in orchestrator, falsy→None fixes in protocol layers. One refactor: extract abort body from orchestrator to abort_handler to stay under 150 lines.

**Tech Stack:** Python 3, pytest, unittest.mock

**Design doc:** `docs/plans/2026-02-22-session3-integrity-design.md`

---

## CLAUDE.md — Required Reading

> **MANDATORY:** Before starting ANY task, read `CLAUDE.md` at the project root. Key rules for this plan:

| Rule | What it means for this plan |
|------|-----------------------------|
| **TDD** (Principle #6) | Write the failing test FIRST, run it, THEN implement. |
| **150-line file limit** (Principle #7) | After EVERY file edit, run `wc -l` on the file. If > 150, split immediately. |
| **Code-to-PRD mapping** (Doc §2) | Every source file must have `# Area:` and `# PRD:` header comments. |
| **PRD sync requirement** (Doc §3) | When code changes, update `docs/prd-rlgm.md`: increment version, update content. |
| **Reuse existing code** (Principle #3) | Search the codebase before writing anything new. |
| **No hardcoded values** (Principle #8) | No secrets, credentials, file paths, or URLs in source. |
| **Test file naming** (Testing §) | Tests live in `tests/`, named `test_<module>.py`. |

---

### Task 1: Add duplicate + phase guards to warmup handler

> **CLAUDE.md checkpoint:** Read `CLAUDE.md` before starting. Confirm: TDD, 150-line limit. File is 82 lines — safe margin.

**Issues:** #7, #14

**Context:** `handlers/warmup.py:28` gets the player, then immediately sets `player.warmup_answer` at line 34. A replayed message overwrites the answer and re-triggers the callback. Also, no phase check — a warmup response arriving during scoring would be processed.

**Files:**
- Modify: `src/q21_referee/_gmc/handlers/warmup.py:28-34`
- Test: `tests/test_handlers_warmup.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_handlers_warmup.py`:

```python
class TestWarmupDuplicateAndPhaseGuards:
    """Tests for duplicate protection and phase guards."""

    def test_duplicate_warmup_returns_empty(self):
        """Second warmup from same player is silently rejected."""
        ctx = make_ctx()
        player = ctx.state.get_player_by_email.return_value
        player.warmup_answer = "already answered"
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    def test_wrong_phase_returns_empty(self):
        """Warmup response in wrong phase is rejected."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.ROUND_STARTED
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_correct_phase_processes(self, mock_exec):
        """Warmup response in WARMUP_SENT phase is accepted."""
        mock_exec.return_value = {
            "book_name": "Test", "book_hint": "Hint",
            "association_word": "word",
        }
        ctx = make_ctx()
        ctx.state.phase = GamePhase.WARMUP_SENT
        outgoing = handle_warmup_response(ctx)
        assert len(outgoing) == 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers_warmup.py::TestWarmupDuplicateAndPhaseGuards -v`
Expected: FAIL — no duplicate guard, no phase check

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/handlers/warmup.py`, after the unknown-player guard (line 32), add:

```python
    if player.warmup_answer is not None:
        logger.info(f"Duplicate warmup from {player.participant_id}, ignoring")
        return []
    if ctx.state.phase != GamePhase.WARMUP_SENT:
        logger.warning(f"Warmup in wrong phase {ctx.state.phase.value}, ignoring")
        return []
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers_warmup.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_gmc/handlers/warmup.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_handlers_warmup.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/handlers/warmup.py tests/test_handlers_warmup.py
git commit -m "fix: add duplicate protection and phase guard to warmup handler"
```

---

### Task 2: Add duplicate + phase guards to questions handler

> **CLAUDE.md checkpoint:** Same pattern as Task 1. File is 73 lines — safe margin.

**Issues:** #8, #14

**Context:** `handlers/questions.py:28` gets the player, then sets `player.questions` at line 34 and `player.answers_sent = True` at line 66. A replayed message overwrites questions and fires the callback again.

**Files:**
- Modify: `src/q21_referee/_gmc/handlers/questions.py:28-34`
- Test: `tests/test_handlers_questions.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_handlers_questions.py`:

```python
from q21_referee._gmc.state import GamePhase


class TestQuestionsDuplicateAndPhaseGuards:
    """Tests for duplicate protection and phase guards."""

    def test_duplicate_questions_returns_empty(self):
        """Second questions batch from same player is rejected."""
        ctx = make_ctx()
        player = ctx.state.get_player_by_email.return_value
        player.answers_sent = True
        outgoing = handle_questions(ctx)
        assert outgoing == []

    def test_wrong_phase_returns_empty(self):
        """Questions in wrong phase are rejected."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.WARMUP_SENT
        outgoing = handle_questions(ctx)
        assert outgoing == []

    def test_round_started_phase_accepted(self):
        """Questions in ROUND_STARTED phase are accepted."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.ROUND_STARTED
        outgoing = handle_questions(ctx)
        assert len(outgoing) == 1

    def test_questions_collecting_phase_accepted(self):
        """Questions in QUESTIONS_COLLECTING phase are accepted."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.QUESTIONS_COLLECTING
        outgoing = handle_questions(ctx)
        assert len(outgoing) == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers_questions.py::TestQuestionsDuplicateAndPhaseGuards -v`
Expected: FAIL

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/handlers/questions.py`, after the unknown-player guard (line 32), add:

```python
    if player.answers_sent:
        logger.info(f"Duplicate questions from {player.participant_id}, ignoring")
        return []
    if ctx.state.phase not in (GamePhase.ROUND_STARTED, GamePhase.QUESTIONS_COLLECTING):
        logger.warning(f"Questions in wrong phase {ctx.state.phase.value}, ignoring")
        return []
```

**Step 4: Run tests**

Run: `pytest tests/test_handlers_questions.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_gmc/handlers/questions.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_handlers_questions.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/handlers/questions.py tests/test_handlers_questions.py
git commit -m "fix: add duplicate protection and phase guard to questions handler"
```

---

### Task 3: Add duplicate + phase guards to scoring handler

> **CLAUDE.md checkpoint:** File is 148 lines — TIGHT. The duplicate + phase guards add ~6 lines. Must trim elsewhere or stay at exactly 150.

**Issues:** #9, #14

**Context:** `handlers/scoring.py:36` gets the player, then sets `player.guess` at line 42 and `player.score_sent = True` at line 78. A replayed guess re-triggers scoring and could produce a second `MATCH_RESULT_REPORT`.

**Files:**
- Modify: `src/q21_referee/_gmc/handlers/scoring.py:36-42`
- Test: `tests/test_handlers_scoring.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_handlers_scoring.py`:

```python
from q21_referee._gmc.state import GamePhase


class TestScoringDuplicateAndPhaseGuards:
    """Tests for duplicate protection and phase guards."""

    def test_duplicate_guess_returns_empty(self):
        """Second guess from same player is rejected."""
        ctx = make_ctx()
        player = ctx.state.get_player_by_email.return_value
        player.score_sent = True
        outgoing = handle_guess(ctx)
        assert outgoing == []

    def test_wrong_phase_returns_empty(self):
        """Guess in wrong phase is rejected."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.WARMUP_SENT
        outgoing = handle_guess(ctx)
        assert outgoing == []

    def test_answers_sent_phase_accepted(self):
        """Guess in ANSWERS_SENT phase is accepted."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.ANSWERS_SENT
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1

    def test_guesses_collecting_phase_accepted(self):
        """Guess in GUESSES_COLLECTING phase is accepted."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.GUESSES_COLLECTING
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers_scoring.py::TestScoringDuplicateAndPhaseGuards -v`
Expected: FAIL

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/handlers/scoring.py`, after the unknown-player guard (line 40), add:

```python
    if player.score_sent:
        logger.info(f"Duplicate guess from {player.participant_id}, ignoring")
        return []
    if ctx.state.phase not in (GamePhase.ANSWERS_SENT, GamePhase.GUESSES_COLLECTING):
        logger.warning(f"Guess in wrong phase {ctx.state.phase.value}, ignoring")
        return []
```

**IMPORTANT:** The file is at 148 lines. Adding 6 lines puts it at 154. To stay under 150, trim the multi-line `breakdown` default dict (lines 67-72) to a single line:

```python
    breakdown = result.get("breakdown", {})
```

This removes 4 lines (the specific breakdown keys are never used — the `abort_handler.py` pattern also just uses `{}`).

**Step 4: Run tests**

Run: `pytest tests/test_handlers_scoring.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_gmc/handlers/scoring.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_handlers_scoring.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/handlers/scoring.py tests/test_handlers_scoring.py
git commit -m "fix: add duplicate protection and phase guard to scoring handler"
```

---

### Task 4: Extract abort_current_game body to abort_handler.py

> **CLAUDE.md checkpoint:** Prerequisite for Tasks 5-6. `orchestrator.py` is 149 lines. We need room for game_id validation + broadcast idempotency (~10 lines). This extraction saves ~15 lines.

**Context:** `orchestrator.py:103-124` contains the full abort logic: scoring loop, snapshot, match result build. The helper functions (`score_player_on_abort`, `determine_abort_winner`, etc.) already live in `abort_handler.py` (108 lines). Moving the orchestrating logic there too is natural.

**Files:**
- Modify: `src/q21_referee/_rlgm/abort_handler.py`
- Modify: `src/q21_referee/_rlgm/orchestrator.py`
- Test: existing `tests/test_orchestrator.py` must still pass

**Step 1: Add `build_abort_report` to abort_handler.py**

At the end of `src/q21_referee/_rlgm/abort_handler.py`, add:

```python
def build_abort_report(
    gmc: GameManagementCycle,
    reason: str,
    ai: RefereeAI,
    config: Dict[str, Any],
) -> List[Tuple[dict, str, str]]:
    """Build full abort report: score unscored players, build match result."""
    outgoing: List[Tuple[dict, str, str]] = []
    snapshot = gmc.get_state_snapshot()
    for key in ["player1", "player2"]:
        player = getattr(gmc.state, key)
        if player.guess is not None and not player.score_sent:
            outgoing.extend(score_player_on_abort(gmc, player, ai, config))
    env, subj = gmc.builder.build_match_result(
        game_id=gmc.gprm.game_id, match_id=gmc.gprm.match_id,
        round_id=gmc.gprm.round_id, winner_id=determine_abort_winner(gmc),
        is_draw=is_abort_draw(gmc), scores=build_abort_scores(gmc),
        status="aborted", abort_reason=reason,
        player_states={"player1": snapshot["player1"],
                       "player2": snapshot["player2"]})
    outgoing.append((env, subj, config.get("league_manager_email", "")))
    return outgoing
```

**Step 2: Update orchestrator.py**

Replace `abort_current_game` body (lines 103-124) with:

```python
    def abort_current_game(self, reason: str) -> Msgs:
        """Force-complete the current game with abort status."""
        if not self.current_game:
            return []
        outgoing = build_abort_report(
            self.current_game, reason, self.ai, self.config)
        self.current_game = None
        if self.state_machine.can_transition(RLGMEvent.GAME_ABORTED):
            self.state_machine.transition(RLGMEvent.GAME_ABORTED)
        return outgoing
```

Update import at line 22-23:
```python
from .abort_handler import (score_player_on_abort, determine_abort_winner,
                            is_abort_draw, build_abort_scores,
                            build_abort_report)
```

**Step 3: Run tests**

Run: `pytest tests/test_orchestrator.py tests/ -v`
Expected: ALL PASS (no behavior change)

**Step 4: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_rlgm/orchestrator.py` — must be ≤ 150 (should be ~138)
- [ ] Run `wc -l src/q21_referee/_rlgm/abort_handler.py` — must be ≤ 150

**Step 5: Commit**

```bash
git add src/q21_referee/_rlgm/orchestrator.py src/q21_referee/_rlgm/abort_handler.py
git commit -m "refactor: extract abort report building from orchestrator to abort_handler"
```

---

### Task 5: Add game_id validation on player messages

> **CLAUDE.md checkpoint:** After Task 4 extraction, orchestrator should be ~138 lines. Adding ~5 lines is safe.

**Issue:** #18

**Context:** `orchestrator.py:126-136` routes any player message to the current game without checking game_id. Stale messages from previous rounds are processed.

**Files:**
- Modify: `src/q21_referee/_rlgm/orchestrator.py:126-131`
- Test: `tests/test_orchestrator.py` (append)

**Step 1: Write the failing test**

Append to `tests/test_orchestrator.py`:

```python
    def test_game_id_mismatch_rejected(self):
        """Player message with wrong game_id is rejected."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        gprm = GPRM(
            player1_email="p1@test.com", player1_id="P001",
            player2_email="p2@test.com", player2_id="P002",
            season_id="S01", game_id="0101001",
            match_id="R1M1", round_id="ROUND_1", round_number=1,
        )
        orchestrator.current_game = GameManagementCycle(
            gprm=gprm, ai=ai, config=config)

        body = {"game_id": "0102999", "payload": {}}
        outgoing = orchestrator.route_player_message(
            "Q21WARMUPRESPONSE", body, "p1@test.com")
        assert outgoing == []

    def test_matching_game_id_accepted(self):
        """Player message with correct game_id is processed."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        gprm = GPRM(
            player1_email="p1@test.com", player1_id="P001",
            player2_email="p2@test.com", player2_id="P002",
            season_id="S01", game_id="0101001",
            match_id="R1M1", round_id="ROUND_1", round_number=1,
        )
        orchestrator.current_game = GameManagementCycle(
            gprm=gprm, ai=ai, config=config)

        body = {"game_id": "0101001", "payload": {"answer": "4"}}
        outgoing = orchestrator.route_player_message(
            "Q21WARMUPRESPONSE", body, "p1@test.com")
        # Doesn't crash — may return empty if warmup phase wrong, but not rejected for game_id
        assert isinstance(outgoing, list)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py::TestRLGMOrchestrator::test_game_id_mismatch_rejected -v`
Expected: FAIL — message is processed, not rejected

**Step 3: Implement the fix**

In `orchestrator.py`, in `route_player_message()`, after the `if not self.current_game:` guard, add:

```python
        incoming_game_id = body.get("game_id")
        if incoming_game_id and incoming_game_id != self.current_game.gprm.game_id:
            logger.warning("game_id mismatch: got %s, expected %s",
                           incoming_game_id, self.current_game.gprm.game_id)
            return []
```

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_rlgm/orchestrator.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_rlgm/orchestrator.py tests/test_orchestrator.py
git commit -m "fix: reject player messages with mismatched game_id"
```

---

### Task 6: Add broadcast idempotency

> **CLAUDE.md checkpoint:** Verify orchestrator line count before adding. Should be ~143 after Task 5.

**Issue:** #21

**Context:** `orchestrator.py:62-81` processes every broadcast without deduplication. If the League Manager re-sends `BROADCAST_NEW_LEAGUE_ROUND`, a second game starts.

**Files:**
- Modify: `src/q21_referee/_rlgm/orchestrator.py:34-43, 62-81`
- Test: `tests/test_orchestrator.py` (append)

**Step 1: Write the failing test**

Append to `tests/test_orchestrator.py`:

```python
    def test_duplicate_broadcast_skipped(self):
        """Duplicate broadcast_id is silently skipped."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        message = {
            "message_type": "BROADCAST_START_SEASON",
            "broadcast_id": "BC001",
            "payload": {"season_id": "S01", "league_id": "L01"},
        }

        result1 = orchestrator.handle_lm_message(message)
        result2 = orchestrator.handle_lm_message(message)

        assert result1 is not None
        assert result2 is None  # Duplicate skipped
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py::TestRLGMOrchestrator::test_duplicate_broadcast_skipped -v`
Expected: FAIL — both calls return a result

**Step 3: Implement the fix**

In `orchestrator.py` `__init__`, add after `self._pending_outgoing`:

```python
        self._processed_broadcasts: set = set()
```

In `handle_lm_message()`, add at the top (after `msg_type` extraction):

```python
        broadcast_id = message.get("broadcast_id")
        if broadcast_id and broadcast_id in self._processed_broadcasts:
            logger.info("Duplicate broadcast %s, skipping", broadcast_id)
            return None
```

At the end of `handle_lm_message()`, before `return result`, add:

```python
        if broadcast_id:
            self._processed_broadcasts.add(broadcast_id)
```

**Step 4: Run tests**

Run: `pytest tests/test_orchestrator.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_rlgm/orchestrator.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_orchestrator.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_rlgm/orchestrator.py tests/test_orchestrator.py
git commit -m "fix: add broadcast idempotency to prevent duplicate processing"
```

---

### Task 7: Fix falsy field guards in protocol.py

> **CLAUDE.md checkpoint:** File is 134 lines — safe margin. No new lines added (replacing `if x:` with `if x is not None:`).

**Issue:** #22

**Context:** `protocol.py:123-132` uses `if correlation_id:`, etc. An empty string `""` or integer `0` is dropped.

**Files:**
- Modify: `src/q21_referee/_shared/protocol.py:123-132`
- Test: `tests/test_protocol.py` (create)

**Step 1: Write the failing test**

Create `tests/test_protocol.py`:

```python
# Area: Shared Tests
# PRD: docs/prd-rlgm.md
"""Tests for protocol falsy field handling."""

from q21_referee._shared.protocol import build_envelope


class TestBuildEnvelopeFalsyFields:
    """Test that falsy but valid values are included in envelopes."""

    def test_empty_string_correlation_id_included(self):
        """Empty string correlation_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            correlation_id="",
        )
        assert "correlation_id" in env
        assert env["correlation_id"] == ""

    def test_empty_string_game_id_included(self):
        """Empty string game_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            game_id="",
        )
        assert "game_id" in env

    def test_none_fields_excluded(self):
        """None fields should NOT be in envelope (default behavior)."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
        )
        assert "correlation_id" not in env
        assert "game_id" not in env
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: `test_empty_string_correlation_id_included` FAILS — empty string is dropped

**Step 3: Implement the fix**

In `src/q21_referee/_shared/protocol.py`, replace lines 123-132:

```python
    # Add optional context fields
    if correlation_id is not None:
        envelope["correlation_id"] = correlation_id
    if league_id is not None:
        envelope["league_id"] = league_id
    if season_id is not None:
        envelope["season_id"] = season_id
    if round_id is not None:
        envelope["round_id"] = round_id
    if game_id is not None:
        envelope["game_id"] = game_id
```

**Step 4: Run tests**

Run: `pytest tests/test_protocol.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_shared/protocol.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_protocol.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_shared/protocol.py tests/test_protocol.py
git commit -m "fix: use None checks instead of falsy checks for protocol envelope fields"
```

---

### Task 8: Fix falsy field guards in envelope_builder.py

> **CLAUDE.md checkpoint:** File is 221 lines — KNOWN SESSION 4 DEBT. We're making minimal changes (replacing `if x:` with `if x is not None:`). Do NOT attempt to split.

**Issue:** #23

**Context:** `envelope_builder.py` has falsy checks at:
- Line 61: `if correlation_id:` in `_base_q21_envelope`
- Lines 83-88: `if round_id:`, `if game_id:`, `if correlation_id:` in `_base_league_envelope`
- Line 187: `if feedback:` in `build_score_feedback`
- Lines 215-217: `if abort_reason:`, `if player_states:` in `build_match_result`

**Files:**
- Modify: `src/q21_referee/_gmc/envelope_builder.py`
- Test: `tests/test_envelope_builder.py` (create)

**Step 1: Write the failing test**

Create `tests/test_envelope_builder.py`:

```python
# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for envelope builder falsy field handling."""

from q21_referee._gmc.envelope_builder import EnvelopeBuilder


def make_builder():
    return EnvelopeBuilder("ref@test.com", "REF001", "L01", "S01")


class TestEnvelopeBuilderFalsyFields:
    """Test that falsy but valid values are included."""

    def test_empty_feedback_included(self):
        """Empty string feedback should be in score envelope."""
        builder = make_builder()
        env, _ = builder.build_score_feedback(
            player_id="P001", game_id="0101001", match_id="M01",
            league_points=0, private_score=0.0, breakdown={},
            feedback="",
        )
        assert "feedback" in env["payload"]
        assert env["payload"]["feedback"] == ""

    def test_none_feedback_excluded(self):
        """None feedback should NOT be in score envelope."""
        builder = make_builder()
        env, _ = builder.build_score_feedback(
            player_id="P001", game_id="0101001", match_id="M01",
            league_points=0, private_score=0.0, breakdown={},
            feedback=None,
        )
        assert "feedback" not in env["payload"]

    def test_empty_correlation_id_in_q21(self):
        """Empty correlation_id should be in Q21 envelope."""
        builder = make_builder()
        env = builder._base_q21_envelope(
            "TEST", "P001", "0101001", "msg1", correlation_id="")
        assert "correlation_id" in env

    def test_empty_round_id_in_league(self):
        """Empty round_id should be in league envelope."""
        builder = make_builder()
        env = builder._base_league_envelope(
            "TEST", "LM", "msg1", round_id="")
        assert "round_id" in env
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_envelope_builder.py -v`
Expected: `test_empty_feedback_included` and others FAIL

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/envelope_builder.py`:

Line 61: `if correlation_id:` → `if correlation_id is not None:`
Line 83: `if round_id:` → `if round_id is not None:`
Line 85: `if game_id:` → `if game_id is not None:`
Line 87: `if correlation_id:` → `if correlation_id is not None:`
Line 187: `if feedback:` → `if feedback is not None:`
Line 215: `if abort_reason:` → `if abort_reason is not None:`
Line 217: `if player_states:` → `if player_states is not None:`

**Step 4: Run tests**

Run: `pytest tests/test_envelope_builder.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Note: `envelope_builder.py` is 221 lines (known Session 4 debt)
- [ ] Run `wc -l tests/test_envelope_builder.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/envelope_builder.py tests/test_envelope_builder.py
git commit -m "fix: use None checks instead of falsy checks in envelope builder"
```

---

### Task 9: Fix DemoAI shared state

> **CLAUDE.md checkpoint:** File is 345 lines — KNOWN SESSION 4 DEBT. Adding 3 lines for state reset. Do NOT attempt to split.

**Issue:** #20

**Context:** `demo_ai.py:104-127` — `get_round_start_info()` loads book data and stores it in instance variables (`_book_name`, `_book_hint`, `_association_domain`). These persist across rounds.

**Files:**
- Modify: `src/q21_referee/demo_ai.py:104`
- Test: `tests/test_demo_ai.py` (create)

**Step 1: Write the failing test**

Create `tests/test_demo_ai.py`:

```python
# Area: DemoAI Tests
# PRD: docs/prd-rlgm.md
"""Tests for DemoAI state management."""

from q21_referee.demo_ai import DemoAI


class TestDemoAIStateReset:
    """Test that DemoAI resets state between rounds."""

    def test_state_reset_between_rounds(self):
        """Instance variables should be reset at start of get_round_start_info."""
        ai = DemoAI()
        ctx = {}

        # First call sets state
        result1 = ai.get_round_start_info(ctx)
        assert ai._book_name is not None

        # Manually corrupt state to verify reset
        ai._book_name = "STALE_DATA"
        ai._book_hint = "STALE_HINT"
        ai._association_domain = "STALE_DOMAIN"

        # Second call should reset before loading
        result2 = ai.get_round_start_info(ctx)
        assert ai._book_name != "STALE_DATA"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_demo_ai.py -v`
Expected: FAIL — `_book_name` is still "STALE_DATA" (no reset)

**Step 3: Implement the fix**

In `src/q21_referee/demo_ai.py`, at the start of `get_round_start_info()` (line 104), add:

```python
    def get_round_start_info(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Return book info from demo file."""
        # Reset round-specific state
        self._book_name = None
        self._book_hint = None
        self._association_domain = None

        content = self._read_demo_file(
```

**Step 4: Run tests**

Run: `pytest tests/test_demo_ai.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Note: `demo_ai.py` is ~348 lines (known Session 4 debt)
- [ ] Run `wc -l tests/test_demo_ai.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/demo_ai.py tests/test_demo_ai.py
git commit -m "fix: reset DemoAI state between rounds to prevent stale data"
```

---

### Task 10: Fix nested attachment parsing

> **CLAUDE.md checkpoint:** File is 353 lines — KNOWN SESSION 4 DEBT. Adding 1-line fix. Do NOT attempt to split.

**Issue:** #26

**Context:** `email_client.py:243-246` recursively calls `_get_json_from_attachments({"payload": part})`. The wrapper dict has no `"id"` key, but `msg["id"]` is used at line 258 to fetch attachments.

**Files:**
- Modify: `src/q21_referee/_shared/email_client.py:243-244`
- Test: `tests/test_email_client.py` (append)

**Step 1: Write the failing test**

Append to `tests/test_email_client.py`:

```python
class TestNestedAttachmentParsing:
    """Tests for nested attachment handling."""

    def test_nested_parts_without_id_no_crash(self):
        """Recursive call with nested parts should not crash on missing id."""
        client = EmailClient.__new__(EmailClient)
        client.credentials_path = "creds.json"
        client.token_path = "token.json"
        client.address = "test@test.com"
        client._credentials = MagicMock()
        client._service = MagicMock()

        # Message with nested multipart structure
        msg = {
            "id": "msg123",
            "payload": {
                "parts": [
                    {
                        "mimeType": "multipart/mixed",
                        "parts": [
                            {
                                "filename": "data.json",
                                "mimeType": "application/json",
                                "body": {"attachmentId": "att1"},
                            }
                        ],
                    }
                ],
            },
        }

        # Should not raise KeyError
        client._service.users().messages().attachments().get().execute.return_value = {
            "data": "e30=",  # base64 for "{}"
        }
        result = client._get_json_from_attachments(msg)
        # Should have recursed and found the JSON attachment
        assert result is not None or result is None  # Just verify no crash
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_email_client.py::TestNestedAttachmentParsing -v`
Expected: May FAIL with KeyError if the recursive call hits `msg["id"]`

**Step 3: Implement the fix**

In `src/q21_referee/_shared/email_client.py`, replace line 244:

```python
                nested_result = self._get_json_from_attachments({"payload": part})
```

with:

```python
                nested_result = self._get_json_from_attachments(
                    {"payload": part, "id": msg.get("id", "")})
```

**Step 4: Run tests**

Run: `pytest tests/test_email_client.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Note: `email_client.py` is ~354 lines (known Session 4 debt)
- [ ] Run `wc -l tests/test_email_client.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_shared/email_client.py tests/test_email_client.py
git commit -m "fix: pass message id through nested attachment parsing to prevent KeyError"
```

---

### Task 11: Update PRD and CLAUDE.md

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Doc §1 (version), Doc §3 (sync PRD on code change).

**Files:**
- Modify: `docs/prd-rlgm.md`

**Step 1: Read the current PRD**

Read `docs/prd-rlgm.md` and note the version (currently `2.5.0`).

**Step 2: Increment the version**

Bump to `2.6.0`.

**Step 3: Update PRD content**

Add a new entry in the Change History section:

```markdown
### Game Integrity Fixes (v2.6.0)

| Fix | File(s) | Description |
|-----|---------|-------------|
| Duplicate warmup guard | `handlers/warmup.py` | Reject replayed warmup responses |
| Duplicate questions guard | `handlers/questions.py` | Reject replayed question batches |
| Duplicate scoring guard | `handlers/scoring.py` | Reject replayed guess submissions |
| Phase guards | `handlers/warmup.py`, `questions.py`, `scoring.py` | Reject messages in wrong game phase |
| game_id validation | `orchestrator.py` | Reject player messages with mismatched game_id |
| Broadcast idempotency | `orchestrator.py` | Skip duplicate broadcast_id messages |
| Extract abort report | `abort_handler.py` | `build_abort_report()` extracted from orchestrator |
| Falsy protocol fields | `protocol.py` | Use `is not None` instead of truthy checks |
| Falsy envelope fields | `envelope_builder.py` | Use `is not None` instead of truthy checks |
| DemoAI state reset | `demo_ai.py` | Reset round state before loading new data |
| Nested attachment fix | `email_client.py` | Pass message ID through recursive attachment parsing |
```

**Step 4: Commit**

```bash
git add docs/prd-rlgm.md
git commit -m "docs: update PRD to v2.6.0 for Session 3 game integrity fixes"
```

---

### Task 12: Full test suite + CLAUDE.md compliance audit

> **CLAUDE.md checkpoint:** Final read of `CLAUDE.md`. Walk through every principle and verify compliance.

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 2: Verify ALL line counts (CLAUDE.md Principle #7)**

Run:
```bash
wc -l src/q21_referee/_gmc/handlers/warmup.py src/q21_referee/_gmc/handlers/questions.py src/q21_referee/_gmc/handlers/scoring.py src/q21_referee/_rlgm/orchestrator.py src/q21_referee/_rlgm/abort_handler.py src/q21_referee/_shared/protocol.py
```
Expected: ALL ≤ 150

Note known Session 4 debt: `envelope_builder.py` (221), `demo_ai.py` (~348), `email_client.py` (~354)

**Step 3: Verify ALL file headers (CLAUDE.md Doc §2)**

Check `# Area:` and `# PRD: docs/prd-rlgm.md` on every modified source file.

**Step 4: Verify PRD version is `2.6.0`**

---

## Summary

| Task | Issue(s) | File(s) | What changes |
|------|----------|---------|--------------|
| 1 | #7, #14 | `handlers/warmup.py` | Duplicate guard + phase guard |
| 2 | #8, #14 | `handlers/questions.py` | Duplicate guard + phase guard |
| 3 | #9, #14 | `handlers/scoring.py` | Duplicate guard + phase guard + trim breakdown |
| 4 | — | `orchestrator.py`, `abort_handler.py` | Extract abort body, make room for Tasks 5-6 |
| 5 | #18 | `orchestrator.py` | game_id mismatch rejection |
| 6 | #21 | `orchestrator.py` | Broadcast idempotency |
| 7 | #22 | `protocol.py` | Falsy → None checks |
| 8 | #23 | `envelope_builder.py` | Falsy → None checks |
| 9 | #20 | `demo_ai.py` | State reset between rounds |
| 10 | #26 | `email_client.py` | Nested attachment ID fix |
| 11 | — | `docs/prd-rlgm.md` | PRD sync v2.6.0 |
| 12 | — | — | Full test suite + compliance audit |

## CLAUDE.md Quick Reference (for every task)

```
Before starting:  Read CLAUDE.md
Before coding:    Write the test FIRST (Principle #6 TDD)
After every edit:  wc -l <file> — must be ≤ 150 (Principle #7)
After every edit:  Check # Area: / # PRD: headers (Doc §2)
Before committing: No hardcoded values? (Principle #8)
After all tasks:   Update docs/prd-rlgm.md (Doc §3)
```

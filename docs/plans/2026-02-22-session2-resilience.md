# Session 2: Resilience & Safety — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Q21 Referee SDK resilient to student callback failures and email transport errors — crash-on-failure becomes log-and-continue.

**Architecture:** Change `execute_callback()` default to `terminate_on_error=False` (Approach A) so all callers get raise-instead-of-sys.exit behavior. Then wrap each handler's callback call in try/except with appropriate fallbacks (Approach C). Split oversized files (`callback_executor.py` 186→<150, `rlgm_runner.py` 255→<150) to comply with CLAUDE.md Principle #7.

**Tech Stack:** Python 3, pytest, unittest.mock, threading (Windows timeout fallback)

**Design doc:** `docs/plans/2026-02-22-session2-resilience-design.md`

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

### Task 1: Extract TimeoutHandler to _gmc/timeout.py

> **CLAUDE.md checkpoint:** Read `CLAUDE.md` before starting. Confirm: TDD, 150-line limit, `# Area:` / `# PRD:` on every new file.

**Issue:** `callback_executor.py` is 186 lines. We're modifying it in Tasks 2-3, so it must come under 150 first.

**Context:** `callback_executor.py:32-60` defines `TimeoutHandler`, a context manager for signal-based timeouts. It's self-contained — only depends on `signal` and `CallbackTimeoutError`. Extracting it to its own module also gives us a home for the Windows threading fallback (Task 8).

**Files:**
- Create: `src/q21_referee/_gmc/timeout.py`
- Modify: `src/q21_referee/_gmc/callback_executor.py`
- Test: existing tests must still pass (no behavior change)

**Step 1: Create the new module**

Create `src/q21_referee/_gmc/timeout.py`:

```python
# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.timeout — Callback timeout enforcement
========================================================

Context manager that enforces deadlines on student callbacks.
Uses signal.SIGALRM on Unix. On non-Unix platforms (Windows),
the timeout is a no-op (callbacks run without a deadline).

NOTE: Signal-based timeouts have a known re-entrancy limitation.
If two SIGALRM signals arrive close together, the second handler
replaces the first. This is acceptable because callbacks are
executed serially (never concurrently) by the SDK.
"""

import signal
from typing import Any, Dict

from ..errors import CallbackTimeoutError


class TimeoutHandler:
    """Context manager for callback timeout enforcement."""

    def __init__(self, seconds: int, callback_name: str, input_payload: Dict):
        self.seconds = seconds
        self.callback_name = callback_name
        self.input_payload = input_payload
        self._old_handler = None

    def _timeout_handler(self, signum, frame):
        raise CallbackTimeoutError(
            callback_name=self.callback_name,
            deadline_seconds=self.seconds,
            input_payload=self.input_payload,
        )

    def __enter__(self):
        if hasattr(signal, "SIGALRM"):
            self._old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False
```

**Step 2: Update callback_executor.py imports**

In `src/q21_referee/_gmc/callback_executor.py`:
- Remove the `TimeoutHandler` class (lines 32-60)
- Remove `import signal` and `import sys` (no longer needed)
- Add `from .timeout import TimeoutHandler`
- Trim `execute_callback` docstring to essentials
- Trim `execute_callback_safe` docstring to essentials

The file should now look like:

```python
# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.callback_executor — Safe callback execution
============================================================

Wraps callback invocation with:
1. Timeout enforcement (via TimeoutHandler)
2. JSON validation (ensure dict returned)
3. Schema validation
4. Error handling (raise or terminate on failure)
"""

from __future__ import annotations
from typing import Any, Callable, Dict
import logging

from ..errors import (
    CallbackTimeoutError,
    InvalidJSONResponseError,
    SchemaValidationError,
)
from .timeout import TimeoutHandler
from .validator import validate_output, apply_score_feedback_penalties
from .._shared.logging_config import log_and_terminate
from .._shared.protocol_logger import get_protocol_logger

logger = logging.getLogger("q21_referee.executor")


def execute_callback(
    callback_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    callback_name: str,
    ctx: Dict[str, Any],
    deadline_seconds: int,
    terminate_on_error: bool = True,
) -> Dict[str, Any]:
    """Execute a callback with timeout, validation, and error handling."""
    logger.debug(f"[CALLBACK] Executing {callback_name} (timeout={deadline_seconds}s)")
    protocol_logger = get_protocol_logger()
    protocol_logger.log_callback_call(callback_name)

    # ── Step 1: Execute with timeout ──────────────────────────
    try:
        with TimeoutHandler(deadline_seconds, callback_name, ctx):
            result = callback_fn(ctx)
    except CallbackTimeoutError as e:
        if terminate_on_error:
            log_and_terminate(e)
        raise

    # ── Step 2: Validate return type is dict ──────────────────
    if not isinstance(result, dict):
        error = InvalidJSONResponseError(
            callback_name=callback_name,
            input_payload=ctx,
            raw_output=result,
        )
        if terminate_on_error:
            log_and_terminate(error)
        raise error

    # ── Step 3: Validate against schema ───────────────────────
    validation_errors = validate_output(callback_name, result)
    if validation_errors:
        error = SchemaValidationError(
            callback_name=callback_name,
            input_payload=ctx,
            output_payload=result,
            validation_errors=validation_errors,
        )
        if terminate_on_error:
            log_and_terminate(error)
        raise error

    # ── Step 4: Apply soft constraint penalties ───────────────
    if callback_name == "score_feedback":
        result = apply_score_feedback_penalties(result)

    logger.debug(f"[CALLBACK] {callback_name} completed successfully")
    protocol_logger.log_callback_response(callback_name)
    return result


def execute_callback_safe(
    callback_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    callback_name: str,
    ctx: Dict[str, Any],
    deadline_seconds: int,
) -> Dict[str, Any]:
    """Execute a callback, raising exceptions instead of terminating."""
    return execute_callback(
        callback_fn=callback_fn,
        callback_name=callback_name,
        ctx=ctx,
        deadline_seconds=deadline_seconds,
        terminate_on_error=False,
    )
```

**Step 3: Run all tests to verify no behavior change**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 4: CLAUDE.md compliance check**

- [ ] `timeout.py` has `# Area: GMC` and `# PRD: docs/prd-rlgm.md` headers
- [ ] Run `wc -l src/q21_referee/_gmc/timeout.py` — must be ≤ 150
- [ ] Run `wc -l src/q21_referee/_gmc/callback_executor.py` — must be ≤ 150

**Step 5: Commit**

```bash
git add src/q21_referee/_gmc/timeout.py src/q21_referee/_gmc/callback_executor.py
git commit -m "refactor: extract TimeoutHandler to _gmc/timeout.py, trim callback_executor to <150 lines"
```

---

### Task 2: Change terminate_on_error default to False + add catch-all

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Principle #6 (TDD) — test first. Also Principle #3 — we're modifying an existing function, not creating new ones.

**Issues:** #1, #6

**Context:** `callback_executor.py:68` has `terminate_on_error: bool = True`. This means any callback failure calls `sys.exit(1)`. We change the default to `False` so exceptions propagate to callers. We also add a catch-all `except Exception` so arbitrary student errors (ValueError, KeyError, etc.) don't bypass the executor's error handling.

**Files:**
- Modify: `src/q21_referee/_gmc/callback_executor.py`
- Test: `tests/test_callback_executor.py` (create)

**Step 1: Write the failing tests**

Create `tests/test_callback_executor.py`:

```python
# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for callback_executor resilience."""

import pytest
from q21_referee._gmc.callback_executor import execute_callback, execute_callback_safe
from q21_referee.errors import CallbackTimeoutError, InvalidJSONResponseError


class TestExecuteCallbackDefault:
    """Test that execute_callback defaults to raising, not terminating."""

    def test_invalid_return_raises_not_exits(self):
        """With default terminate_on_error=False, bad return raises exception."""
        def bad_callback(ctx):
            return "not a dict"

        with pytest.raises(InvalidJSONResponseError):
            execute_callback(
                callback_fn=bad_callback,
                callback_name="test_cb",
                ctx={},
                deadline_seconds=5,
            )

    def test_callback_exception_propagates(self):
        """Arbitrary exceptions from callbacks should propagate."""
        def failing_callback(ctx):
            raise ValueError("student code broke")

        with pytest.raises(ValueError, match="student code broke"):
            execute_callback(
                callback_fn=failing_callback,
                callback_name="test_cb",
                ctx={},
                deadline_seconds=5,
            )

    def test_successful_callback_returns_result(self):
        """A valid callback still works normally."""
        def good_callback(ctx):
            return {"warmup_question": "What is 1+1?"}

        result = execute_callback(
            callback_fn=good_callback,
            callback_name="warmup_question",
            ctx={},
            deadline_seconds=5,
        )
        assert result["warmup_question"] == "What is 1+1?"


class TestExecuteCallbackSafe:
    """Test execute_callback_safe still works (now equivalent to default)."""

    def test_safe_raises_on_bad_return(self):
        def bad_callback(ctx):
            return 42

        with pytest.raises(InvalidJSONResponseError):
            execute_callback_safe(
                callback_fn=bad_callback,
                callback_name="test_cb",
                ctx={},
                deadline_seconds=5,
            )
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_callback_executor.py -v`
Expected: `test_invalid_return_raises_not_exits` FAILS (currently calls sys.exit), `test_callback_exception_propagates` FAILS (exception not caught by executor)

**Step 3: Implement the changes**

In `src/q21_referee/_gmc/callback_executor.py`:

1. Change default: `terminate_on_error: bool = True` → `terminate_on_error: bool = False`

2. Add catch-all after `CallbackTimeoutError` handler. The try/except block becomes:

```python
    # ── Step 1: Execute with timeout ──────────────────────────
    try:
        with TimeoutHandler(deadline_seconds, callback_name, ctx):
            result = callback_fn(ctx)
    except CallbackTimeoutError as e:
        if terminate_on_error:
            log_and_terminate(e)
        raise
    except Exception as e:
        logger.error(f"Callback '{callback_name}' raised: {e}", exc_info=True)
        if terminate_on_error:
            log_and_terminate(e)
        raise
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_callback_executor.py -v`
Expected: ALL PASS

Run: `pytest tests/ -v`
Expected: ALL PASS (existing tests unaffected)

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_gmc/callback_executor.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_callback_executor.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/callback_executor.py tests/test_callback_executor.py
git commit -m "fix: change terminate_on_error default to False, add catch-all for arbitrary callback exceptions"
```

---

### Task 3: Wrap warmup_initiator callback with try/except

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Principle #3 (Reuse existing code) — we reuse the fallback pattern from `abort_handler.py:47-53`. Also Principle #7 — `warmup_initiator.py` is 86 lines, safe margin.

**Issue:** #10 (partial)

**Context:** `warmup_initiator.py:55-60` calls `execute_callback()` for `get_warmup_question`. If the callback fails, the exception propagates up to `orchestrator.start_round()`. The GMC is already created (orchestrator line 99) but warmup was never sent — inconsistent state.

**Solution:** Wrap in try/except. On failure, use fallback question `"What is 2 + 2?"` (already the default at line 61). The warmup is a connectivity check, not a game decision.

**Files:**
- Modify: `src/q21_referee/_rlgm/warmup_initiator.py:53-61`
- Test: `tests/test_warmup_initiator.py` (append)

**Step 1: Write the failing test**

Append to `tests/test_warmup_initiator.py`:

```python
class TestWarmupCallbackResilience:
    """Tests for warmup callback failure handling."""

    def test_callback_failure_uses_fallback_question(self):
        """If get_warmup_question fails, fallback question is used."""
        class FailingAI(MockRefereeAI):
            def get_warmup_question(self, ctx):
                raise ValueError("AI exploded")

        config = make_config()
        gprm = make_gprm()
        ai = FailingAI()
        gmc = GameManagementCycle(gprm, ai, config)

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        # Should still send warmup calls with fallback question
        assert len(outgoing) == 2
        # Phase should still advance
        assert gmc.state.phase == GamePhase.WARMUP_SENT
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_warmup_initiator.py::TestWarmupCallbackResilience -v`
Expected: FAIL — `ValueError: AI exploded` propagates uncaught

**Step 3: Implement the fix**

In `src/q21_referee/_rlgm/warmup_initiator.py`, replace lines 53-61 with:

```python
    # Call student callback (resilient: use fallback on failure)
    service = SERVICE_DEFINITIONS["warmup_question"]
    try:
        result = execute_callback(
            callback_fn=ai.get_warmup_question,
            callback_name="warmup_question",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
        warmup_q = result.get("warmup_question", "What is 2 + 2?")
    except Exception:
        logger.error("get_warmup_question failed, using fallback", exc_info=True)
        warmup_q = "What is 2 + 2?"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_warmup_initiator.py -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_rlgm/warmup_initiator.py` — must be ≤ 150
- [ ] Verify `# Area: RLGM` and `# PRD: docs/prd-rlgm.md` at top

**Step 6: Commit**

```bash
git add src/q21_referee/_rlgm/warmup_initiator.py tests/test_warmup_initiator.py
git commit -m "fix: warmup_initiator uses fallback question when callback fails"
```

---

### Task 4: Wrap handlers/warmup.py callback with try/except

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Principle #6 (TDD). The handler is 76 lines — safe margin.

**Issue:** #10 (partial)

**Context:** `handlers/warmup.py:48-53` calls `execute_callback()` for `get_round_start_info`. If the callback fails, both players never get `Q21ROUNDSTART`. The abort safety net (triggered by `BROADCAST_END_LEAGUE_ROUND`) handles cleanup.

**Files:**
- Modify: `src/q21_referee/_gmc/handlers/warmup.py:46-57`
- Test: `tests/test_handlers_warmup.py` (create)

**Step 1: Write the failing test**

Create `tests/test_handlers_warmup.py`:

```python
# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup handler resilience."""

from unittest.mock import Mock, MagicMock
from q21_referee._gmc.handlers.warmup import handle_warmup_response


def make_ctx(callback_raises=None):
    """Build a mock handler context with both warmups already received."""
    ctx = Mock()
    ctx.body = {"payload": {"answer": "4"}}
    ctx.sender_email = "p1@test.com"

    player = Mock()
    player.participant_id = "P001"
    player.warmup_answer = None
    ctx.state.get_player_by_email.return_value = player
    ctx.state.both_warmups_received.return_value = True
    ctx.state.player1 = player
    ctx.state.player2 = Mock(participant_id="P002", email="p2@test.com",
                             questions_message_id=None)

    # Mock the callback context builder
    ctx.context_builder.build_round_start_info_ctx.return_value = {}

    # Mock the AI callback
    if callback_raises:
        ctx.ai.get_round_start_info.side_effect = callback_raises
    else:
        ctx.ai.get_round_start_info.return_value = {
            "book_name": "Test", "book_hint": "Hint",
            "association_word": "word",
        }

    # Mock envelope builder
    ctx.builder.build_round_start.return_value = (
        {"message_id": "msg1", "message_type": "Q21ROUNDSTART"},
        "SUBJECT",
    )
    ctx.state.game_id = "0101001"
    ctx.state.match_id = "0101001"
    ctx.state.auth_token = "tok_abc"

    return ctx


class TestWarmupHandlerResilience:
    """Tests for warmup handler callback failure."""

    def test_callback_failure_returns_empty(self):
        """If get_round_start_info raises, handler returns empty."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    def test_successful_callback_sends_round_start(self):
        """Normal flow: both players get Q21ROUNDSTART."""
        ctx = make_ctx()
        outgoing = handle_warmup_response(ctx)
        assert len(outgoing) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers_warmup.py::TestWarmupHandlerResilience::test_callback_failure_returns_empty -v`
Expected: FAIL — `ValueError: AI broke` propagates

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/handlers/warmup.py`, wrap the callback call (lines 46-57) in try/except:

```python
    # Build context for student callback
    callback_ctx = ctx.context_builder.build_round_start_info_ctx()

    # Call student callback (resilient: return empty on failure)
    service = SERVICE_DEFINITIONS["round_start_info"]
    try:
        result = execute_callback(
            callback_fn=ctx.ai.get_round_start_info,
            callback_name="round_start_info",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
    except Exception:
        logger.error("get_round_start_info failed, game stalled", exc_info=True)
        return []

    ctx.state.book_name = result.get("book_name", "Unknown Book")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers_warmup.py -v`
Expected: ALL PASS

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_gmc/handlers/warmup.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_handlers_warmup.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/handlers/warmup.py tests/test_handlers_warmup.py
git commit -m "fix: warmup handler returns empty on callback failure instead of crashing"
```

---

### Task 5: Wrap handlers/questions.py callback with try/except

> **CLAUDE.md checkpoint:** Same pattern as Task 4. TDD first. File is 67 lines — safe.

**Issue:** #10 (partial)

**Context:** `handlers/questions.py:42-47` calls `execute_callback()` for `get_answers`. If the callback fails, the player never receives answers. The abort safety net handles cleanup.

**Files:**
- Modify: `src/q21_referee/_gmc/handlers/questions.py:40-47`
- Test: `tests/test_handlers_questions.py` (create)

**Step 1: Write the failing test**

Create `tests/test_handlers_questions.py`:

```python
# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for questions handler resilience."""

from unittest.mock import Mock
from q21_referee._gmc.handlers.questions import handle_questions


def make_ctx(callback_raises=None):
    """Build a mock handler context."""
    ctx = Mock()
    ctx.body = {"payload": {"questions": ["Q1"]}, "message_id": "msg_in"}
    ctx.sender_email = "p1@test.com"

    player = Mock()
    player.participant_id = "P001"
    player.questions = None
    player.answers_sent = False
    ctx.state.get_player_by_email.return_value = player
    ctx.state.both_answers_sent.return_value = False

    ctx.context_builder.build_answers_ctx.return_value = {}

    if callback_raises:
        ctx.ai.get_answers.side_effect = callback_raises
    else:
        ctx.ai.get_answers.return_value = {"answers": ["A1"]}

    ctx.builder.build_answers_batch.return_value = (
        {"message_id": "msg_out", "message_type": "Q21ANSWERSBATCH"}, "SUBJ",
    )
    ctx.state.game_id = "0101001"
    ctx.state.match_id = "0101001"
    ctx.state.auth_token = "tok_abc"

    return ctx


class TestQuestionsHandlerResilience:
    """Tests for questions handler callback failure."""

    def test_callback_failure_returns_empty(self):
        """If get_answers raises, handler returns empty."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        outgoing = handle_questions(ctx)
        assert outgoing == []

    def test_successful_callback_sends_answers(self):
        """Normal flow: player gets Q21ANSWERSBATCH."""
        ctx = make_ctx()
        outgoing = handle_questions(ctx)
        assert len(outgoing) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers_questions.py::TestQuestionsHandlerResilience::test_callback_failure_returns_empty -v`
Expected: FAIL

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/handlers/questions.py`, wrap lines 40-47:

```python
    # Build context for student callback
    callback_ctx = ctx.context_builder.build_answers_ctx(player, player.questions)

    # Call student callback (resilient: return empty on failure)
    service = SERVICE_DEFINITIONS["answers"]
    try:
        result = execute_callback(
            callback_fn=ctx.ai.get_answers,
            callback_name="answers",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
    except Exception:
        logger.error("get_answers failed for %s, game stalled",
                     player.participant_id, exc_info=True)
        return []

    answers = result.get("answers", [])
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
git commit -m "fix: questions handler returns empty on callback failure instead of crashing"
```

---

### Task 6: Wrap handlers/scoring.py callback with try/except + zero-score fallback

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Principle #3 (Reuse) — we reuse the zero-score fallback pattern from `abort_handler.py:21-26, 53`. File is 134 lines — watch the limit.

**Issue:** #10 (partial)

**Context:** `handlers/scoring.py:43-48` calls `execute_callback()` for `get_score_feedback`. Unlike warmup and questions, scoring should NOT return empty — we want to produce a zero-score result so the game can still send `MATCH_RESULT_REPORT`. This matches the abort_handler pattern.

**Files:**
- Modify: `src/q21_referee/_gmc/handlers/scoring.py:41-48`
- Test: `tests/test_handlers_scoring.py` (create)

**Step 1: Write the failing test**

Create `tests/test_handlers_scoring.py`:

```python
# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for scoring handler resilience."""

from unittest.mock import Mock
from q21_referee._gmc.handlers.scoring import handle_guess


def make_ctx(callback_raises=None):
    """Build a mock handler context."""
    ctx = Mock()
    ctx.body = {"payload": {"guess": "BookX"}, "message_id": "msg_in"}
    ctx.sender_email = "p1@test.com"

    player = Mock()
    player.participant_id = "P001"
    player.email = "p1@test.com"
    player.guess = None
    player.score_sent = False
    player.league_points = 0
    player.private_score = 0.0
    player.feedback = None
    ctx.state.get_player_by_email.return_value = player
    ctx.state.both_scores_sent.return_value = False

    ctx.context_builder.build_score_feedback_ctx.return_value = {}

    if callback_raises:
        ctx.ai.get_score_feedback.side_effect = callback_raises
    else:
        ctx.ai.get_score_feedback.return_value = {
            "league_points": 10, "private_score": 5.0,
            "breakdown": {}, "feedback": "good",
        }

    ctx.builder.build_score_feedback.return_value = (
        {"message_id": "msg_out", "message_type": "Q21SCOREFEEDBACK"}, "SUBJ",
    )
    ctx.state.game_id = "0101001"
    ctx.state.match_id = "0101001"

    return ctx


class TestScoringHandlerResilience:
    """Tests for scoring handler callback failure."""

    def test_callback_failure_sends_zero_score(self):
        """If get_score_feedback raises, send zero-score feedback."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        outgoing = handle_guess(ctx)

        # Should still send feedback (with zero scores)
        assert len(outgoing) == 1
        # Player should be marked as scored
        player = ctx.state.get_player_by_email.return_value
        assert player.score_sent is True
        assert player.league_points == 0
        assert player.private_score == 0.0

    def test_successful_callback_sends_score(self):
        """Normal flow: player gets score feedback."""
        ctx = make_ctx()
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers_scoring.py::TestScoringHandlerResilience::test_callback_failure_sends_zero_score -v`
Expected: FAIL — `ValueError: AI broke` propagates

**Step 3: Implement the fix**

In `src/q21_referee/_gmc/handlers/scoring.py`, wrap lines 41-48:

```python
    # Build context for student callback
    callback_ctx = ctx.context_builder.build_score_feedback_ctx(player, payload)

    # Call student callback (resilient: use zero-score on failure)
    service = SERVICE_DEFINITIONS["score_feedback"]
    try:
        result = execute_callback(
            callback_fn=ctx.ai.get_score_feedback,
            callback_name="score_feedback",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
    except Exception:
        logger.error("get_score_feedback failed for %s, using zero defaults",
                     player.participant_id, exc_info=True)
        result = {"league_points": 0, "private_score": 0.0,
                  "breakdown": {}, "feedback": None}

    league_points = result.get("league_points", 0)
```

**Step 4: Run tests**

Run: `pytest tests/test_handlers_scoring.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/_gmc/handlers/scoring.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_handlers_scoring.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/handlers/scoring.py tests/test_handlers_scoring.py
git commit -m "fix: scoring handler uses zero-score defaults on callback failure"
```

---

### Task 7: Extract protocol context from rlgm_runner.py

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Principle #5 (Modularity) and #7 (150-line limit). `rlgm_runner.py` is 255 lines — must be split before Task 8 adds email retry logic.

**Issue:** Prerequisite for #11

**Context:** Lines 174-240 of `rlgm_runner.py` manage protocol logger context (game_id formatting per message type). This is a distinct concern from the core event loop. Extract to pure functions in a new module.

**Files:**
- Create: `src/q21_referee/_rlgm/runner_protocol_context.py`
- Modify: `src/q21_referee/rlgm_runner.py`
- Test: existing `tests/test_rlgm_runner.py` must still pass

**Step 1: Create the new module**

Create `src/q21_referee/_rlgm/runner_protocol_context.py`:

```python
# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.runner_protocol_context — Protocol logger context
====================================================================

Pure functions that update the protocol logger's game_id and role_active
state based on message type and orchestrator state. Extracted from
rlgm_runner.py to keep it under 150 lines.
"""

import logging

logger = logging.getLogger("q21_referee")

# Season-level message types (use 0199999, empty role)
SEASON_LEVEL_MESSAGES = {
    "BROADCAST_START_SEASON",
    "SEASON_REGISTRATION_RESPONSE",
    "BROADCAST_ASSIGNMENT_TABLE",
    "LEAGUE_COMPLETED",
    "MATCH_RESULT_REPORT",
}


def update_context_before_routing(orchestrator, message_type, body,
                                  protocol_logger):
    """Update protocol logger context BEFORE routing (for RECEIVED log).

    Game ID format: SSRRGGG (SS=season always "01", RR=round, GGG=game)
    - Season-level messages: 0199999 (RR=99 -> empty role)
    - Round-level (START-ROUND): 01RR999 (ACTIVE/INACTIVE based on assignment)
    - Game-level (active game): 01RRGGG (ACTIVE)
    """
    # If we have an active game, use its context (game-level)
    if orchestrator.current_game:
        gprm = orchestrator.current_game.gprm
        if gprm and gprm.game_id:
            protocol_logger.set_game_id(gprm.game_id)
            protocol_logger.set_role_active(True)
            return

    # Season-level messages: 0199999, role will be empty (RR=99)
    if message_type in SEASON_LEVEL_MESSAGES:
        protocol_logger.set_game_id("0199999")
        protocol_logger.set_role_active(False)
        return

    # Round-level: BROADCAST_NEW_LEAGUE_ROUND
    if message_type == "BROADCAST_NEW_LEAGUE_ROUND":
        payload = body.get("payload") or {}
        round_number = payload.get("round_number")
        if not isinstance(round_number, int):
            logger.warning(
                "Invalid round_number in payload: %s, defaulting to 0",
                round_number,
            )
            round_number = 0

        assignment = find_assignment_for_round(orchestrator, round_number)
        if assignment:
            game_id = assignment.get("game_id", "")
            if game_id:
                protocol_logger.set_game_id(game_id)
                protocol_logger.set_role_active(True)
                return

        game_id = f"01{round_number:02d}999"
        protocol_logger.set_game_id(game_id)
        protocol_logger.set_role_active(False)
        return

    # Default fallback
    protocol_logger.set_game_id("0199999")
    protocol_logger.set_role_active(False)


def update_context_after_routing(orchestrator, protocol_logger):
    """Update protocol logger context AFTER routing (for SENT logs)."""
    if orchestrator.current_game:
        gprm = orchestrator.current_game.gprm
        if gprm and gprm.game_id:
            protocol_logger.set_game_id(gprm.game_id)
            protocol_logger.set_role_active(True)


def find_assignment_for_round(orchestrator, round_number):
    """Find assignment for the given round number."""
    for assignment in orchestrator.get_assignments():
        if assignment.get("round_number") == round_number:
            return assignment
    return {}
```

**Step 2: Update rlgm_runner.py**

Remove `SEASON_LEVEL_MESSAGES`, `_update_protocol_logger_context`, `_update_protocol_logger_context_after_routing`, and `_find_assignment_for_round` from `rlgm_runner.py`. Replace with imports and calls to the new module:

Add import at top:
```python
from ._rlgm.runner_protocol_context import (
    update_context_before_routing,
    update_context_after_routing,
)
```

In `_poll_and_process`, replace:
```python
                self._update_protocol_logger_context(message_type, body)
```
with:
```python
                update_context_before_routing(
                    self.orchestrator, message_type, body,
                    self._protocol_logger)
```

Replace:
```python
                self._update_protocol_logger_context_after_routing()
```
with:
```python
                update_context_after_routing(
                    self.orchestrator, self._protocol_logger)
```

**Step 3: Update tests to use new function signatures**

In `tests/test_rlgm_runner.py`, the `TestProtocolLoggerContext` tests call `runner._update_protocol_logger_context(...)`. These tests should now import and call the module functions directly OR keep calling via the runner (which delegates). Since we're removing the methods from the runner, update the tests to use the new functions:

Change import:
```python
from q21_referee._rlgm.runner_protocol_context import (
    update_context_before_routing,
)
```

Change test calls from `runner._update_protocol_logger_context("TYPE", body)` to `update_context_before_routing(runner.orchestrator, "TYPE", body, runner._protocol_logger)`.

**Step 4: Run tests**

Run: `pytest tests/test_rlgm_runner.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] `runner_protocol_context.py` has `# Area: RLGM` and `# PRD: docs/prd-rlgm.md`
- [ ] Run `wc -l src/q21_referee/_rlgm/runner_protocol_context.py` — must be ≤ 150
- [ ] Run `wc -l src/q21_referee/rlgm_runner.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_rlgm_runner.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/_rlgm/runner_protocol_context.py src/q21_referee/rlgm_runner.py tests/test_rlgm_runner.py
git commit -m "refactor: extract protocol logger context from rlgm_runner to runner_protocol_context.py"
```

---

### Task 8: Add email send retry for MATCH_RESULT_REPORT + threading timeout

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Principle #8 (No hardcoded values) — the retry delay (2 seconds) is a constant in the module, not a config value (acceptable for internal retry logic).

**Issues:** #11, #13

**Context:** `rlgm_runner.py:254` calls `self.email_client.send()` and ignores the return value. For `MATCH_RESULT_REPORT` messages, a failed send means the League Manager never learns the game outcome. Also, `timeout.py` needs a threading fallback for Windows.

**Files:**
- Modify: `src/q21_referee/rlgm_runner.py` (email retry in `_send_messages`)
- Modify: `src/q21_referee/_gmc/timeout.py` (threading fallback)
- Test: `tests/test_rlgm_runner.py` (append), `tests/test_timeout.py` (create)

**Step 1: Write failing tests**

Append to `tests/test_rlgm_runner.py`:

```python
class TestSendMessages:
    """Tests for email send retry logic."""

    def create_config(self):
        return {
            "referee_id": "REF001", "referee_email": "ref@test.com",
            "group_id": "GROUP_A", "league_id": "LEAGUE001",
            "season_id": "S01", "league_manager_email": "lm@test.com",
        }

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_send_failure_logged(self, mock_email_cls):
        """Send failure is logged."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)
        runner.email_client.send.return_value = False

        envelope = {"message_type": "Q21WARMUPCALL"}
        runner._send_messages([(envelope, "SUBJ", "p1@test.com")])

        runner.email_client.send.assert_called_once()

    @patch("q21_referee.rlgm_runner.EmailClient")
    @patch("q21_referee.rlgm_runner.time")
    def test_match_result_retried_on_failure(self, mock_time, mock_email_cls):
        """MATCH_RESULT_REPORT gets one retry on send failure."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)
        # First call fails, second succeeds
        runner.email_client.send.side_effect = [False, True]

        envelope = {"message_type": "MATCH_RESULT_REPORT"}
        runner._send_messages([(envelope, "SUBJ", "lm@test.com")])

        assert runner.email_client.send.call_count == 2
```

Create `tests/test_timeout.py`:

```python
# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for timeout handler."""

import pytest
from unittest.mock import patch
from q21_referee._gmc.timeout import TimeoutHandler
from q21_referee.errors import CallbackTimeoutError


class TestTimeoutHandler:
    """Tests for TimeoutHandler."""

    def test_no_timeout_returns_normally(self):
        """Callback completing within deadline works fine."""
        with TimeoutHandler(5, "test_cb", {}) as th:
            result = 42
        assert result == 42

    @patch("q21_referee._gmc.timeout.hasattr", return_value=False)
    def test_no_sigalrm_is_noop(self, mock_hasattr):
        """On non-Unix, TimeoutHandler is a no-op."""
        # This just verifies it doesn't crash
        with TimeoutHandler(1, "test_cb", {}):
            pass
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rlgm_runner.py::TestSendMessages -v`
Expected: FAIL — `_send_messages` doesn't retry

**Step 3: Implement email retry**

In `src/q21_referee/rlgm_runner.py`, replace `_send_messages`:

```python
    def _send_messages(self, outgoing: List[Tuple[dict, str, str]]) -> None:
        """Send outgoing messages. Retry once for MATCH_RESULT_REPORT."""
        for envelope, subject, recipient in outgoing:
            success = self.email_client.send(recipient, subject, envelope)
            if not success:
                msg_type = envelope.get("message_type", "")
                logger.warning(f"Send failed: {msg_type} to {recipient}")
                if msg_type == "MATCH_RESULT_REPORT":
                    time.sleep(2)
                    retry = self.email_client.send(recipient, subject, envelope)
                    if not retry:
                        logger.error(f"MATCH_RESULT_REPORT retry failed to {recipient}")
```

**Step 4: Run tests**

Run: `pytest tests/test_rlgm_runner.py tests/test_timeout.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] Run `wc -l src/q21_referee/rlgm_runner.py` — must be ≤ 150
- [ ] Run `wc -l src/q21_referee/_gmc/timeout.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_rlgm_runner.py` — must be ≤ 150
- [ ] Run `wc -l tests/test_timeout.py` — must be ≤ 150

**Step 6: Commit**

```bash
git add src/q21_referee/rlgm_runner.py src/q21_referee/_gmc/timeout.py tests/test_rlgm_runner.py tests/test_timeout.py
git commit -m "fix: retry MATCH_RESULT_REPORT on send failure, add timeout tests"
```

---

### Task 9: Add OAuth token refresh on poll failure

> **CLAUDE.md checkpoint:** This is a 1-line fix. TDD still applies. `email_client.py` is 353 lines (known debt, Session 4 split).

**Issue:** #12

**Context:** `email_client.py:184-185` catches poll errors and logs them, but the stale `_service` persists. Setting `self._service = None` forces reconnection on next poll, which triggers `_get_credentials()` to refresh the OAuth token.

**Files:**
- Modify: `src/q21_referee/_shared/email_client.py:184-185`
- Test: `tests/test_email_client.py` (create)

**Step 1: Write the failing test**

Create `tests/test_email_client.py`:

```python
# Area: Shared Tests
# PRD: docs/prd-rlgm.md
"""Tests for email client resilience."""

from unittest.mock import patch, MagicMock
from q21_referee._shared.email_client import EmailClient


class TestPollResilience:
    """Tests for poll() error recovery."""

    @patch("q21_referee._shared.email_client.build")
    @patch("q21_referee._shared.email_client.InstalledAppFlow")
    @patch("q21_referee._shared.email_client.Path")
    def test_poll_error_resets_service(self, mock_path, mock_flow, mock_build):
        """After a poll error, _service should be None to force reconnect."""
        client = EmailClient.__new__(EmailClient)
        client.credentials_path = "creds.json"
        client.token_path = "token.json"
        client.address = "test@test.com"
        client._credentials = MagicMock()

        # Create a mock service that fails on list()
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = Exception("API error")
        client._service = mock_service

        # Poll should not crash
        result = client.poll()

        assert result == []
        # Service should be reset so next call reconnects
        assert client._service is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_email_client.py -v`
Expected: FAIL — `client._service` is still the mock (not None)

**Step 3: Implement the fix**

In `src/q21_referee/_shared/email_client.py`, change lines 184-186 from:

```python
        except Exception as e:
            logger.error(f"Poll error: {e}")
```

to:

```python
        except Exception as e:
            logger.error(f"Poll error: {e}")
            self._service = None  # Force reconnect on next poll
```

**Step 4: Run tests**

Run: `pytest tests/test_email_client.py tests/ -v`
Expected: ALL PASS

**Step 5: CLAUDE.md compliance check**

- [ ] `email_client.py` has `# Area: Shared` and `# PRD: docs/prd-rlgm.md` — verified
- [ ] Run `wc -l tests/test_email_client.py` — must be ≤ 150
- [ ] Note: `email_client.py` is 354 lines (known debt, Session 4)

**Step 6: Commit**

```bash
git add src/q21_referee/_shared/email_client.py tests/test_email_client.py
git commit -m "fix: reset Gmail service on poll failure to force OAuth token refresh"
```

---

### Task 10: Update PRD

> **CLAUDE.md checkpoint:** Re-read `CLAUDE.md` Documentation & Versioning — Doc §1 (version at top), Doc §3 (sync PRD when code changes).

**Context:** We modified `callback_executor.py`, `timeout.py` (new), `warmup_initiator.py`, `handlers/warmup.py`, `handlers/questions.py`, `handlers/scoring.py`, `rlgm_runner.py`, `runner_protocol_context.py` (new), `email_client.py`. Per CLAUDE.md, we must sync `docs/prd-rlgm.md`.

**Files:**
- Modify: `docs/prd-rlgm.md`

**Step 1: Read the current PRD**

Read `docs/prd-rlgm.md` and note the version (currently `2.4.0`).

**Step 2: Increment the version**

Bump to `2.5.0`.

**Step 3: Update PRD content**

Add a new entry in the Change History section:

```markdown
### Resilience & Safety Fixes (v2.5.0)

| Fix | File(s) | Description |
|-----|---------|-------------|
| Safe callback default | `callback_executor.py` | `terminate_on_error` defaults to `False`; callbacks raise instead of calling `sys.exit(1)` |
| Catch-all handler | `callback_executor.py` | Arbitrary student exceptions caught and re-raised (not just timeout/validation) |
| Extract TimeoutHandler | `timeout.py` (new) | Timeout enforcement extracted from callback_executor; includes signal re-entrancy docs |
| Resilient warmup init | `warmup_initiator.py` | Callback failure uses fallback question instead of crashing |
| Resilient warmup handler | `handlers/warmup.py` | Callback failure returns empty (game stalls, process lives) |
| Resilient questions handler | `handlers/questions.py` | Callback failure returns empty (game stalls, process lives) |
| Resilient scoring handler | `handlers/scoring.py` | Callback failure uses zero-score defaults (game continues) |
| Extract protocol context | `runner_protocol_context.py` (new) | Protocol logger context extracted from rlgm_runner |
| Email send retry | `rlgm_runner.py` | MATCH_RESULT_REPORT retried once on send failure |
| OAuth refresh | `email_client.py` | `_service` reset on poll failure to force token refresh |
```

Also update the File Structure section to include:
- `_gmc/timeout.py` — Callback timeout enforcement (signal-based)
- `_rlgm/runner_protocol_context.py` — Protocol logger context management

Also update CLAUDE.md Project Structure to include the new files.

**Step 4: Update CLAUDE.md Project Structure**

In `CLAUDE.md`, add the two new files to the project structure tree:
- Under `_gmc/`: add `timeout.py` after `snapshot.py`
- Under `_rlgm/`: add `runner_protocol_context.py` after `abort_handler.py`

**Step 5: CLAUDE.md compliance check**

- [ ] PRD has version `2.5.0` at top
- [ ] Changes match the actual code

**Step 6: Commit**

```bash
git add docs/prd-rlgm.md CLAUDE.md
git commit -m "docs: update PRD to v2.5.0 and CLAUDE.md structure for Session 2 resilience fixes"
```

---

### Task 11: Full test suite + CLAUDE.md compliance audit

> **CLAUDE.md checkpoint:** Final read of `CLAUDE.md`. Walk through every principle and verify compliance.

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 2: Verify ALL line counts (CLAUDE.md Principle #7)**

Run:
```bash
wc -l src/q21_referee/_gmc/timeout.py src/q21_referee/_gmc/callback_executor.py src/q21_referee/_gmc/handlers/warmup.py src/q21_referee/_gmc/handlers/questions.py src/q21_referee/_gmc/handlers/scoring.py src/q21_referee/_rlgm/warmup_initiator.py src/q21_referee/_rlgm/runner_protocol_context.py src/q21_referee/rlgm_runner.py
```
Expected: ALL ≤ 150 (except `email_client.py` — known Session 4 debt)

**Step 3: Verify ALL file headers (CLAUDE.md Doc §2)**

For each new/modified source file, confirm `# Area:` and `# PRD: docs/prd-rlgm.md`:
- `_gmc/timeout.py` — `# Area: GMC`
- `_gmc/callback_executor.py` — `# Area: GMC`
- `_gmc/handlers/warmup.py` — `# Area: GMC`
- `_gmc/handlers/questions.py` — `# Area: GMC`
- `_gmc/handlers/scoring.py` — `# Area: GMC`
- `_rlgm/warmup_initiator.py` — `# Area: RLGM`
- `_rlgm/runner_protocol_context.py` — `# Area: RLGM`
- `rlgm_runner.py` — `# Area: RLGM`
- `_shared/email_client.py` — `# Area: Shared`

**Step 4: Verify no hardcoded values (CLAUDE.md Principle #8)**

Scan all modified files. The only "constant" is the 2-second retry delay in `rlgm_runner.py` — this is internal retry logic, not a configurable value.

**Step 5: Verify PRD was updated (CLAUDE.md Doc §3)**

Confirm `docs/prd-rlgm.md` is at version `2.5.0` and reflects all Session 2 changes.

---

## Summary

| Task | Issue(s) | File(s) | What changes |
|------|----------|---------|--------------|
| 1 | — | `timeout.py`, `callback_executor.py` | Extract TimeoutHandler, trim to <150 |
| 2 | #1, #6 | `callback_executor.py` | Default→False, catch-all |
| 3 | #10 | `warmup_initiator.py` | try/except + fallback question |
| 4 | #10 | `handlers/warmup.py` | try/except → empty on failure |
| 5 | #10 | `handlers/questions.py` | try/except → empty on failure |
| 6 | #10 | `handlers/scoring.py` | try/except + zero-score fallback |
| 7 | — | `runner_protocol_context.py`, `rlgm_runner.py` | Extract protocol context, trim runner |
| 8 | #11, #13 | `rlgm_runner.py`, `timeout.py` | Email retry, timeout tests |
| 9 | #12 | `email_client.py` | Reset _service on poll failure |
| 10 | — | `docs/prd-rlgm.md`, `CLAUDE.md` | PRD sync, structure update |
| 11 | #34 | — | Full test suite + compliance audit |

## CLAUDE.md Quick Reference (for every task)

```
Before starting:  Read CLAUDE.md
Before coding:    Write the test FIRST (Principle #6 TDD)
After every edit:  wc -l <file> — must be ≤ 150 (Principle #7)
After every edit:  Check # Area: / # PRD: headers (Doc §2)
Before committing: No hardcoded values? (Principle #8)
After all tasks:   Update docs/prd-rlgm.md (Doc §3)
```

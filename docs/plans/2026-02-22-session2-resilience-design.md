# Session 2: Resilience & Safety — Design

Version: 1.0.0

## Overview

Make the Q21 Referee SDK resilient to student callback failures and email transport errors. Currently, if a student's `RefereeAI` callback raises an exception or times out, the process terminates via `sys.exit(1)`. This session replaces crash-on-failure with log-and-continue behavior at every callback and email send site.

**Audit issues addressed:** #1, #6, #10, #11, #12, #13, #34

**Reform-introduced issues status:** All 5 reform-introduced issues (#1-#5 from the reform audit) are already resolved in the current code. `abort_handler.py` uses `execute_callback_safe` with try/except, `snapshot.py` has None player guards, `abort_handler.py` has None guards on all player access, and `warmup_initiator.py` guards `if player is None: continue`. No work needed.

---

## Approach: A+C Hybrid

**Approach A — Safe by Default:** Change `execute_callback()` default from `terminate_on_error=True` to `terminate_on_error=False`. All callers get resilient behavior (raise instead of `sys.exit`) without code changes.

**Approach C — Handler Try/Except:** Wrap `execute_callback` calls in handlers with try/except. On failure: log error, return empty outgoing list. The game stalls for that player but the process stays alive. Follows the pattern already established in `abort_handler.py`.

---

## Changes

### 1. Split callback_executor.py (186 lines → under 150)

**Problem:** `callback_executor.py` is 186 lines. We're modifying it, so it must come under 150 per CLAUDE.md Principle #7.

**Solution:** Extract `TimeoutHandler` class to `_gmc/timeout.py` (~30 lines). Trim `execute_callback()` docstring (parameter/return docs repeat the type hints). Keeps `execute_callback` and `execute_callback_safe` in `callback_executor.py`.

**New file:** `src/q21_referee/_gmc/timeout.py`
**Modified:** `src/q21_referee/_gmc/callback_executor.py`

### 2. Change terminate_on_error default to False

**Problem:** `execute_callback()` has `terminate_on_error=True` default. When a student callback fails, `log_and_terminate()` calls `sys.exit(1)`, killing the entire referee process. No `MATCH_RESULT_REPORT` is sent, the League Manager never learns the game outcome.

**Solution:** Change default to `False` at `callback_executor.py:68`. Exceptions propagate to callers instead of terminating. Callers who need termination behavior (none currently) must explicitly opt in.

**Impact:** `execute_callback_safe()` becomes functionally equivalent to `execute_callback()` but remains as a semantic marker (intent: "I expect this to raise, not terminate"). No change needed to `abort_handler.py` which already uses `execute_callback_safe`.

**Modified:** `src/q21_referee/_gmc/callback_executor.py`

### 3. Add catch-all for arbitrary callback exceptions

**Problem:** `execute_callback()` only catches `CallbackTimeoutError`. If a student callback raises `ValueError`, `KeyError`, `TypeError`, etc., the exception propagates uncaught past the executor.

**Solution:** Add a catch-all `except Exception` after the `CallbackTimeoutError` handler:
- Log the error with full traceback
- If `terminate_on_error=True`, call `log_and_terminate`
- Otherwise, re-raise the original exception

No new exception class needed (avoids bloating `errors.py` which is already at 159 lines). Handlers catch `Exception` in their own try/except.

**Modified:** `src/q21_referee/_gmc/callback_executor.py`

### 4. Wrap warmup_initiator callback with try/except

**Problem:** `warmup_initiator.py:55` calls `execute_callback()` for `get_warmup_question`. If the callback fails, the exception propagates to `orchestrator.start_round()` and up to `rlgm_runner._poll_and_process()`, where it's caught by the generic `except Exception`. But by then, `current_game` has been set (line 99 of orchestrator), so the game is in an inconsistent state: GMC exists but warmup was never sent.

**Solution:** Wrap the `execute_callback` call in try/except inside `initiate_warmup()`. On failure:
- Log error
- Use fallback warmup question: `"What is 2 + 2?"` (already used as default)
- Continue sending warmup calls normally

This is better than failing the entire round start. The warmup question is a connectivity check, not a critical game decision.

**Modified:** `src/q21_referee/_rlgm/warmup_initiator.py`

### 5. Wrap GMC handler callbacks with try/except

**Problem:** Three GMC handlers call `execute_callback()` without error handling:
- `handlers/warmup.py:48` — `get_round_start_info` callback
- `handlers/questions.py:42` — `get_answers` callback
- `handlers/scoring.py:43` — `get_score_feedback` callback

If any callback fails, the game enters an inconsistent state.

**Solution:** Wrap each `execute_callback` call in try/except. On failure:
- `warmup.py`: Log error, return empty. Game stalls (players never get `Q21ROUNDSTART`). Game will be aborted when `BROADCAST_END_LEAGUE_ROUND` arrives.
- `questions.py`: Log error, return empty. Player never gets answers. Same abort safety net.
- `scoring.py`: Log error, use zero-score defaults (same pattern as `abort_handler.py:53`). Send the zero-score feedback so the game can still produce a `MATCH_RESULT_REPORT`.

**Modified:** `src/q21_referee/_gmc/handlers/warmup.py`, `questions.py`, `scoring.py`

### 6. Split rlgm_runner.py (255 lines → under 150)

**Problem:** `rlgm_runner.py` is 255 lines. We're adding email retry logic, so it must come under 150.

**Solution:** Extract protocol logger context management to `_rlgm/runner_protocol_context.py`:
- `SEASON_LEVEL_MESSAGES` constant
- `update_context_before_routing()` function
- `update_context_after_routing()` function
- `find_assignment_for_round()` helper

These are pure functions that take orchestrator + protocol_logger as args. No class needed. The runner calls them instead of its own methods.

**New file:** `src/q21_referee/_rlgm/runner_protocol_context.py`
**Modified:** `src/q21_referee/rlgm_runner.py`

### 7. Check email send return values with retry

**Problem:** `rlgm_runner.py:254` calls `self.email_client.send()` but ignores the `bool` return value. If a `MATCH_RESULT_REPORT` fails to send, the League Manager never learns the game outcome. There's no retry.

**Solution:** Check `send()` return value. On failure:
- Log warning for all message types
- For `MATCH_RESULT_REPORT` messages: retry once after a 2-second delay
- If retry also fails: log error (the game result is lost)

Detection: Check `envelope.get("message_type") == "MATCH_RESULT_REPORT"` to identify critical messages.

**Modified:** `src/q21_referee/rlgm_runner.py`

### 8. Add OAuth token refresh on poll failure

**Problem:** `email_client.py:184-185` catches poll errors and logs them, but the stale `_service` object persists. If the OAuth token expires mid-session, every subsequent poll fails silently (returns empty list).

**Solution:** In the outer `except` of `poll()`, set `self._service = None`. On the next poll call, `poll()` line 148-149 checks `if not self._service: self._connect()`, which triggers `_get_credentials()` which refreshes the token.

This is a 1-line fix. No file split needed for `email_client.py` (353 lines is a Session 4 concern — we're adding 1 line, not significantly increasing the file).

**Modified:** `src/q21_referee/_shared/email_client.py`

### 9. Add threading-based timeout fallback for Windows

**Problem:** `TimeoutHandler` uses `signal.SIGALRM` which is Unix-only. On Windows, the `if hasattr(signal, "SIGALRM")` check makes `__enter__` and `__exit__` no-ops — callbacks run with no timeout at all.

**Solution:** When `SIGALRM` is unavailable, run the callback in a `threading.Thread` with `join(timeout=seconds)`. If the thread exceeds the deadline, raise `CallbackTimeoutError`. Known limitation: the callback thread continues running in the background (Python threads can't be forcibly killed).

This goes in the new `_gmc/timeout.py` module.

**Modified:** `src/q21_referee/_gmc/timeout.py`

### 10. Add signal re-entrancy comment

**Problem:** Issue #34 — If two SIGALRM signals arrive close together, the second could clobber the first signal handler. This is a known limitation of signal-based timeouts, not a bug to fix.

**Solution:** Add a comment in `timeout.py` documenting the re-entrancy concern and why it's acceptable (callbacks are serialized, not concurrent).

**Modified:** `src/q21_referee/_gmc/timeout.py`

### 11. Update PRD

Per CLAUDE.md Doc §3, update `docs/prd-rlgm.md` to reflect all Session 2 changes: resilient callback execution, email retry, OAuth refresh, file splits.

**Modified:** `docs/prd-rlgm.md`

---

## File Impact Summary

| File | Action | Change |
|------|--------|--------|
| `_gmc/timeout.py` | **Create** | TimeoutHandler extracted from callback_executor + threading fallback |
| `_gmc/callback_executor.py` | **Modify** | Default→False, catch-all, import timeout, trim docstrings |
| `_gmc/handlers/warmup.py` | **Modify** | try/except around get_round_start_info callback |
| `_gmc/handlers/questions.py` | **Modify** | try/except around get_answers callback |
| `_gmc/handlers/scoring.py` | **Modify** | try/except around get_score_feedback + zero-score fallback |
| `_rlgm/warmup_initiator.py` | **Modify** | try/except around get_warmup_question + fallback question |
| `_rlgm/runner_protocol_context.py` | **Create** | Protocol context methods extracted from rlgm_runner |
| `rlgm_runner.py` | **Modify** | Extract protocol context, add email send retry |
| `_shared/email_client.py` | **Modify** | Reset _service on poll failure (1 line) |
| `docs/prd-rlgm.md` | **Modify** | PRD sync for Session 2 changes |

## Test Strategy

Each change gets a failing test first (CLAUDE.md Principle #6 TDD):

| Change | Test |
|--------|------|
| Default change | Test execute_callback raises (not terminates) on failure |
| Catch-all | Test that arbitrary exceptions are caught and re-raised |
| warmup_initiator try/except | Test callback failure returns warmup with fallback question |
| warmup.py try/except | Test callback failure returns empty outgoing |
| questions.py try/except | Test callback failure returns empty outgoing |
| scoring.py try/except | Test callback failure returns zero-score feedback |
| Email retry | Test MATCH_RESULT_REPORT gets one retry on send failure |
| OAuth refresh | Test _service reset on poll error |
| Threading timeout | Test timeout fires on non-Unix (mock hasattr) |
| File splits | Existing tests pass after extraction (no behavior change) |

## Risks

- **Stalled games:** When a callback fails, the game stalls for that player. The abort mechanism (triggered by `BROADCAST_END_LEAGUE_ROUND`) is the safety net. This is acceptable — a stalled game is better than a dead process.
- **Threading timeout leak:** On Windows, the timed-out callback thread continues running. Acceptable for an educational SDK.
- **email_client.py line count:** At 353 lines, this file violates the 150-line limit. We're deferring the full split to Session 4 since the OAuth fix is 1 line. Documented as known debt.

## Excluded from Session 2

- `email_client.py` full split (Session 4)
- `errors.py` split/trim (Session 4, currently 159 lines)
- Context wrapping mismatch (pre-existing, Session 4)
- Empty string defaults in handler_new_round (already fixed in v2.1.0)

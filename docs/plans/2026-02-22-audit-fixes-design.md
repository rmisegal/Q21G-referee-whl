# Audit Fixes Design

Version: 1.0.0

## Overview

Fix 40 issues found during a comprehensive code audit of the Q21 Referee SDK. Issues span all severity levels: 6 CRITICAL, 8 HIGH, 11 MEDIUM, 15 LOW.

Work is split into 4 themed sessions, each self-contained and independently testable.

## Session 1: Wiring & Registration

**Issues:** #2, #3, #4, #5, #25

**Problem:** 4 handler classes exist but are never registered in the orchestrator. `LEAGUE_COMPLETED` passes the message filter but `is_lm_message()` returns `False`, so it's silently dropped. `season_id` from `BROADCAST_START_SEASON` is not stored for downstream use.

**Fixes:**

1. **Register missing handlers** (`orchestrator.py`) — Import and register `BroadcastKeepAliveHandler`, `BroadcastCriticalPauseHandler`, `BroadcastCriticalResetHandler`, `BroadcastRoundResultsHandler`. These classes already exist; they just need `reg()` calls.

2. **Add missing message types** (`_runner_config.py`) — Add `BROADCAST_CRITICAL_PAUSE`, `BROADCAST_CRITICAL_RESET`, `BROADCAST_ROUND_RESULTS` to `INCOMING_MESSAGE_TYPES`.

3. **Fix `is_lm_message()`** (`_runner_config.py`) — Extend to also match `"LEAGUE_COMPLETED"`:
   ```python
   return message_type.startswith("BROADCAST_") or message_type in {
       "SEASON_REGISTRATION_RESPONSE", "LEAGUE_COMPLETED"
   }
   ```

4. **Register `LEAGUE_COMPLETED` handler** (`orchestrator.py`) — Wire to `BroadcastEndSeasonHandler` or create a minimal handler that transitions the state machine and signals the poll loop to stop.

5. **Store `season_id` from `BROADCAST_START_SEASON`** (`handler_start_season.py`) — Save `season_id` and `league_id` to `self.config` so `handler_new_round._build_gprm()` can access them.

**Files:** `orchestrator.py`, `_runner_config.py`, `handler_start_season.py`

---

## Session 2: Resilience & Safety

**Issues:** #1, #6, #10, #11, #12, #13, #34

**Problem:** Callback failures (exceptions, timeouts, validation errors) kill the entire process via `sys.exit(1)`. Email send failures are silently ignored. OAuth token expiry causes permanent poll failure. No timeout enforcement on Windows.

**Fixes:**

1. **Catch all callback exceptions** (`callback_executor.py`) — Add catch-all around `callback_fn(ctx)` that logs the error and raises a custom exception instead of letting arbitrary exceptions propagate with state already mutated.

2. **Change `terminate_on_error` default to `False`** (`callback_executor.py`) — Errors raise exceptions instead of calling `sys.exit(1)`. Callers decide how to handle.

3. **Handle callback failures in handlers** (`handlers/warmup.py`, `questions.py`, `scoring.py`) — Wrap `execute_callback` in try/except. On failure: log error, don't advance phase, return empty outgoing list. Game stalls for that player but process stays alive.

4. **Check email send return values** (`rlgm_runner.py`) — `_send_messages()` logs failures and retries once for critical messages (`MATCH_RESULT_REPORT`). If send fails for match result, don't call `complete_game()` — keep game alive for retry.

5. **Add OAuth token refresh** (`email_client.py`) — On poll failure, set `self._service = None` and retry once to force re-authentication.

6. **Add threading-based timeout fallback** (`callback_executor.py`) — When `signal.SIGALRM` unavailable (Windows), use `threading.Timer` with a flag check after callback returns.

**Files:** `callback_executor.py`, `handlers/warmup.py`, `handlers/questions.py`, `handlers/scoring.py`, `rlgm_runner.py`, `email_client.py`

---

## Session 3: Game Integrity

**Issues:** #7, #8, #9, #14, #18, #20, #21, #22, #23, #24, #26

**Problem:** No duplicate protection — replayed messages cause duplicate `MATCH_RESULT_REPORT`s. No phase guards — out-of-order messages corrupt game state. No game_id validation — stale messages from previous rounds are processed by the current game. Abort always reports draws regardless of game progress.

**Fixes:**

1. **Add duplicate protection** (`handlers/warmup.py`, `questions.py`, `scoring.py`) — Check existing `PlayerState` fields before processing:
   - Warmup: `if player.warmup_answer is not None: return []`
   - Questions: `if player.answers_sent: return []`
   - Scoring: `if player.score_sent: return []`

2. **Add phase guards** (`handlers/warmup.py`, `questions.py`, `scoring.py`) — Check `ctx.state.phase` at handler entry:
   - Warmup: requires `WARMUP_SENT`
   - Questions: requires `ROUND_STARTED` or `QUESTIONS_COLLECTING`
   - Scoring: requires `ANSWERS_SENT` or `GUESSES_COLLECTING`

3. **Add game_id validation** (`orchestrator.py`) — In `route_player_message()`, compare incoming `game_id` against `self.current_game.gprm.game_id`. Reject mismatches.

4. **Fix DemoAI shared state** (`demo_ai.py`) — Reset instance variables at start of `get_round_start_info` before loading new data.

5. **Add broadcast idempotency** — Use in-memory `set()` of processed `broadcast_id` values in the orchestrator. Check before handling, add after processing.

6. **Fix falsy field guards** (`protocol.py`, `envelope_builder.py`) — Change `if value:` to `if value is not None:` so empty strings and `0` are included.

7. **Fix abort scoring** (`orchestrator.py`) — Compare player progress (guess submitted > questions answered > warmup only) instead of always reporting draw.

8. **Fix nested attachment parsing** (`email_client.py`) — Guard against missing `"id"` key in recursive `_get_json_from_attachments` call.

9. **Verify `book_name` in protocol** (`envelope_builder.py`) — Confirm whether protocol requires `book_name` in `Q21ROUNDSTART`. If not, remove it.

10. **Fix TypedDict naming** (`types.py`, `callbacks.py`) — Align `player_a`/`player_b` vs `player1`/`player2` everywhere.

**Files:** `handlers/warmup.py`, `handlers/questions.py`, `handlers/scoring.py`, `orchestrator.py`, `protocol.py`, `envelope_builder.py`, `email_client.py`, `demo_ai.py`, `types.py`, `callbacks.py`

---

## Session 4: Cleanup

**Issues:** #15, #16, #17, #19, #27-40

**Problem:** 5 files exceed the 150-line limit. Entire database layer (5 files) is dead code. Miscellaneous minor issues: wrong log level for match results, regex missing "Not Relevant", deprecated datetime format, type coercion gaps.

**Fixes:**

1. **Split oversized files:**
   - `validator.py` (422 lines) → `validator_warmup.py`, `validator_questions.py`, `validator_scoring.py`, `validator_common.py`
   - `context_builder.py` (260 lines) → `context_warmup.py`, `context_questions.py`, `context_scoring.py`
   - `envelope_builder.py` (222 lines) → `envelope_player.py`, `envelope_league.py`
   - `demo_ai.py` (346 lines) → `demo_ai.py` (callbacks) + `demo_data_loader.py` (file parsing)
   - `errors.py` (159 lines) → Trim or split

2. **Dead database layer** — Keep files with `# NOTE: not yet wired` annotation. Full wiring is a future session.

3. **Fix `group_id` as `player_id`** (`handler_assignment.py`) — Document assumption or add fallback field check.

4. **Fix `MATCH_RESULT_REPORT` log level** (`rlgm_runner.py`) — Move from `SEASON_LEVEL_MESSAGES` to game-level.

5. **Minor fixes:**
   - Assignment ack with 0 assignments: document as correct (#15)
   - HTML body fallback: not needed, JSON is in attachments (#27)
   - Timestamp format: change colon to period before ms (#38)
   - DemoAI regex: add `"Not Relevant"` pattern (#39)
   - `round_number` type: cast to `int()` (#40)
   - Return type annotation: `Optional[dict]` (#36)
   - Config mutation: add comment (#37)
   - Signal re-entrancy: add comment (#33)

6. **Update PRD** — Increment version, document all changes.

**Files:** `validator.py` (split), `context_builder.py` (split), `envelope_builder.py` (split), `demo_ai.py` (split), `errors.py`, `handler_assignment.py`, `rlgm_runner.py`, `protocol_logger.py`, `handler_end_round.py`, `prd-rlgm.md`

---

## Summary

| Session | Theme | Issues | Est. Tasks |
|---------|-------|--------|------------|
| 1 | Wiring & Registration | #2, #3, #4, #5, #25 | ~5 |
| 2 | Resilience & Safety | #1, #6, #10, #11, #12, #13, #34 | ~7 |
| 3 | Game Integrity | #7, #8, #9, #14, #18, #20-24, #26 | ~11 |
| 4 | Cleanup | #15-17, #19, #27-40 | ~12 |

## Principles

- TDD for every fix (per CLAUDE.md)
- 150-line file limit enforced
- PRD sync after each session
- Frequent commits per task

# Session 3: Game Integrity — Design

Version: 1.0.0

## Overview

Protect game state from duplicate messages, out-of-order messages, stale messages, and protocol field loss. Currently, replayed player messages cause duplicate `MATCH_RESULT_REPORT`s, out-of-order messages corrupt game state, stale messages from previous rounds are processed by the current game, and falsy protocol fields (empty string, zero) are silently dropped.

**Audit issues addressed:** #7, #8, #9, #14, #18, #20, #21, #22, #23, #24, #26

---

## Approach: Direct Fixes

Each fix is local to the file it touches. No new abstractions or middleware. One small refactor: extract `abort_current_game` body from `orchestrator.py` (149 lines) to `abort_handler.py` (108 lines) to make room for the broadcast idempotency and game_id validation additions.

---

## Changes

### 1. Add duplicate protection to warmup handler

**Issue:** #7

**Problem:** Replayed `Q21WARMUPRESPONSE` from the same player is processed again. The warmup answer is overwritten and `both_warmups_received()` re-triggers the callback flow.

**Solution:** At the top of `handle_warmup_response()`, after getting the player, check:
```python
if player.warmup_answer is not None:
    return []
```

**Modified:** `src/q21_referee/_gmc/handlers/warmup.py`

### 2. Add duplicate protection to questions handler

**Issue:** #8

**Problem:** Replayed `Q21QUESTIONSBATCH` re-processes answers. `player.answers_sent` gets set True again, the callback fires again, and a duplicate `Q21ANSWERSBATCH` is sent.

**Solution:** After getting the player, check:
```python
if player.answers_sent:
    return []
```

**Modified:** `src/q21_referee/_gmc/handlers/questions.py`

### 3. Add duplicate protection to scoring handler

**Issue:** #9

**Problem:** Replayed `Q21GUESSSUBMISSION` re-triggers scoring. A second `MATCH_RESULT_REPORT` is sent if `both_scores_sent()` fires again.

**Solution:** After getting the player, check:
```python
if player.score_sent:
    return []
```

**Modified:** `src/q21_referee/_gmc/handlers/scoring.py`

### 4. Add phase guards to all handlers

**Issue:** #14

**Problem:** Out-of-order player messages are processed without phase validation. A guess arriving before answers are sent, or questions arriving before round start, corrupts game state.

**Solution:** Add phase checks at handler entry, after the unknown-player guard:

- `warmup.py`: Reject unless `phase == WARMUP_SENT`
- `questions.py`: Reject unless `phase in {ROUND_STARTED, QUESTIONS_COLLECTING}`
- `scoring.py`: Reject unless `phase in {ANSWERS_SENT, GUESSES_COLLECTING}`

Each returns `[]` with a warning log on phase mismatch.

**Modified:** `src/q21_referee/_gmc/handlers/warmup.py`, `questions.py`, `scoring.py`

### 5. Add game_id validation on player messages

**Issue:** #18

**Problem:** `orchestrator.route_player_message()` routes any player message to the current game without checking game_id. Stale messages from a previous round (different game_id) are processed by the current game.

**Solution:** In `route_player_message()`, extract `game_id` from the body and compare against `self.current_game.gprm.game_id`. Reject mismatches.

```python
incoming_game_id = body.get("game_id")
if incoming_game_id and incoming_game_id != self.current_game.gprm.game_id:
    logger.warning("game_id mismatch: got %s, expected %s",
                   incoming_game_id, self.current_game.gprm.game_id)
    return []
```

**Modified:** `src/q21_referee/_rlgm/orchestrator.py`

### 6. Add broadcast idempotency

**Issue:** #21

**Problem:** Duplicate broadcast messages from the League Manager are processed multiple times. A re-sent `BROADCAST_NEW_LEAGUE_ROUND` starts a second game for the same round.

**Solution:** Add `self._processed_broadcasts: set = set()` to `RLGMOrchestrator.__init__`. In `handle_lm_message()`, check `broadcast_id` before routing:

```python
broadcast_id = message.get("broadcast_id")
if broadcast_id and broadcast_id in self._processed_broadcasts:
    logger.info("Duplicate broadcast %s, skipping", broadcast_id)
    return None
# ... route ...
self._processed_broadcasts.add(broadcast_id)
```

**Modified:** `src/q21_referee/_rlgm/orchestrator.py`

### 7. Extract abort_current_game body to abort_handler.py

**Problem:** `orchestrator.py` is 149 lines. Changes #5 and #6 add ~10 lines. To stay under 150, we need to move code out.

**Solution:** Move the body of `abort_current_game` to a new function `build_abort_report(gmc, reason, ai, config)` in `abort_handler.py`. The orchestrator method becomes a thin wrapper:

```python
def abort_current_game(self, reason: str) -> Msgs:
    if not self.current_game:
        return []
    outgoing = build_abort_report(self.current_game, reason, self.ai, self.config)
    self.current_game = None
    if self.state_machine.can_transition(RLGMEvent.GAME_ABORTED):
        self.state_machine.transition(RLGMEvent.GAME_ABORTED)
    return outgoing
```

This moves the scoring loop, snapshot building, and match result construction to `abort_handler.py` where the helper functions already live.

**Modified:** `src/q21_referee/_rlgm/orchestrator.py`, `src/q21_referee/_rlgm/abort_handler.py`

### 8. Fix falsy field guards in protocol.py

**Issue:** #22

**Problem:** `build_envelope()` lines 123-132 use `if correlation_id:`, `if league_id:`, etc. An empty string `""` or `0` is treated as "not provided" and dropped from the envelope.

**Solution:** Change all five guards to `if <field> is not None:`.

**Modified:** `src/q21_referee/_shared/protocol.py`

### 9. Fix falsy field guards in envelope_builder.py

**Issue:** #23

**Problem:** `_base_league_envelope()` lines 83-88 and `build_score_feedback()` line 187 and `build_match_result()` lines 215-217 use `if value:` checks. Zero scores, empty feedback strings, and False values are dropped.

**Solution:** Change all falsy checks to `if value is not None:`.

**Modified:** `src/q21_referee/_gmc/envelope_builder.py` (221 lines — known Session 4 debt)

### 10. Fix DemoAI shared state

**Issue:** #20

**Problem:** `DemoAI` instance variables (`_book_name`, `_book_hint`, etc.) persist across rounds. When multiple games run in the same RLGM session, stale data from the previous game contaminates the next.

**Solution:** At the start of `get_round_start_info()`, reset the round-specific variables before loading new data:

```python
def get_round_start_info(self, ctx):
    self._book_name = None
    self._book_hint = None
    self._association_domain = None
    # ... existing load logic ...
```

**Modified:** `src/q21_referee/demo_ai.py` (345 lines — known Session 4 debt)

### 11. Fix nested attachment parsing

**Issue:** #26

**Problem:** `_get_json_from_attachments()` line 244 passes `{"payload": part}` for recursive calls. If the nested `part` has no `"id"` key, the recursive call may attempt to fetch an attachment without a message ID, causing a KeyError at line 258 (`msg["id"]`).

**Solution:** Pass the original message `id` through the recursive call, and guard against missing `attachmentId`:

In the recursive call at line 243-246, the issue is that `msg["id"]` on line 258 uses the original message dict's ID, but the recursive wrapper `{"payload": part}` has no `"id"`. Fix: pass the message ID explicitly or restructure to pass the original msg.

Simplest fix — guard the recursive call's return and keep the original msg available:

```python
if part.get("parts"):
    nested_result = self._get_json_from_attachments(
        {"payload": part, "id": msg.get("id", "")})
    if nested_result:
        return nested_result
```

**Modified:** `src/q21_referee/_shared/email_client.py` (353 lines — known Session 4 debt)

### 12. Fix TypedDict player_a/player_b naming

**Issue:** From audit — `player_a`/`player_b` in types.py and context_builder.py vs `player1`/`player2` in GameState.

**Decision:** Keep `player_a`/`player_b` in the callback contexts. The context represents the student-facing API where "a" and "b" are intentional abstractions (player A is the opponent, player B is contextual). The `player1`/`player2` naming is internal (GameState). These are different naming domains, not a bug.

**No change needed.** Document this decision in the PRD.

### 13. Verify book_name in protocol

**Issue:** From audit — unclear whether protocol requires `book_name` in `Q21ROUNDSTART`.

**Decision:** `book_name` IS included in the `Q21ROUNDSTART` payload at `envelope_builder.py:133`. The protocol spec (referenced in the docstring as §7.4) includes it. This is correct behavior.

**No change needed.** Document as verified.

### 14. Update PRD

Per CLAUDE.md Doc §3, update `docs/prd-rlgm.md` to reflect all Session 3 changes.

**Modified:** `docs/prd-rlgm.md`

---

## File Impact Summary

| File | Action | Change |
|------|--------|--------|
| `_gmc/handlers/warmup.py` | **Modify** | Duplicate guard + phase guard |
| `_gmc/handlers/questions.py` | **Modify** | Duplicate guard + phase guard |
| `_gmc/handlers/scoring.py` | **Modify** | Duplicate guard + phase guard |
| `_rlgm/orchestrator.py` | **Modify** | game_id validation, broadcast idempotency, thin abort wrapper |
| `_rlgm/abort_handler.py` | **Modify** | Accept `build_abort_report` extracted from orchestrator |
| `_shared/protocol.py` | **Modify** | Falsy → None checks (5 fields) |
| `_gmc/envelope_builder.py` | **Modify** | Falsy → None checks (known debt: 221 lines) |
| `demo_ai.py` | **Modify** | Reset state at round start (known debt: 345 lines) |
| `_shared/email_client.py` | **Modify** | Guard nested attachment parsing (known debt: 353 lines) |
| `docs/prd-rlgm.md` | **Modify** | PRD sync for Session 3 changes |

## Test Strategy

| Change | Test |
|--------|------|
| Duplicate warmup | Test second warmup returns empty |
| Duplicate questions | Test second questions returns empty |
| Duplicate scoring | Test second guess returns empty |
| Phase guard warmup | Test warmup rejected in wrong phase |
| Phase guard questions | Test questions rejected in wrong phase |
| Phase guard scoring | Test scoring rejected in wrong phase |
| game_id validation | Test mismatched game_id returns empty |
| Broadcast idempotency | Test duplicate broadcast_id skipped |
| Abort extraction | Existing abort tests pass unchanged |
| Falsy protocol fields | Test empty string and 0 are included |
| Falsy envelope fields | Test zero scores and empty feedback included |
| DemoAI state reset | Test state reset between rounds |
| Nested attachment | Test missing ID in nested parts |

## Risks

- **scoring.py at 148 lines:** Adding duplicate + phase guards pushes close to 150. May need to trim blank lines or shorten comments.
- **orchestrator.py at 149 lines:** The abort extraction + new guards must net to ≤ 150 lines. The extraction saves ~15 lines, additions cost ~10.
- **Over-limit files:** envelope_builder.py (221), demo_ai.py (345), email_client.py (353) all get small fixes but remain over 150. Tracked as known Session 4 debt.

## Excluded from Session 3

- File splits for envelope_builder.py, demo_ai.py, email_client.py (Session 4)
- TypedDict player_a/player_b rename (not a bug — different naming domains)
- book_name protocol verification (confirmed correct)

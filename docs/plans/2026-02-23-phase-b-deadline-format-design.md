# Phase B: In-Game Deadline & Format Validation — Design

**Version:** 1.0.0
**Created:** 2026-02-23
**Status:** Approved

---

## 1. Problem

Phase A detects malfunctions **before** a game starts (via lookup table). But once a game is running, a player can still malfunction by:
1. **Not responding** — player never sends warmup response, questions, or guess
2. **Sending malformed messages** — bad subject line format, missing JSON fields, invalid payload structure

Currently, the referee waits indefinitely for player responses. There is no timeout enforcement and no format validation on incoming player messages.

## 2. Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Timeout action | Abort entire game | Uses existing abort_handler infrastructure. Timed-out player gets technical loss. |
| Check location | Polling loop | Each poll cycle checks for expired deadlines. Fits single-threaded architecture. |
| Timeout values | Configurable, default 40s | Via `config["player_response_timeout_seconds"]`. |
| Warmup retry | No retry, abort on first timeout | Simpler. AGENT_CORE.md retry spec deferred. |
| Format validation scope | Anything that would cause handler errors | Subject line format, required JSON fields, per-message payload structure. |
| Format violation action | Abort game | Same as timeout — abort with reason. |

## 3. Components

### 3.1 DeadlineTracker (`_gmc/deadline_tracker.py`)

Tracks outgoing message deadlines per-player:

- `set_deadline(phase, player_email, deadline_seconds)` — record deadline
- `check_expired() -> List[dict]` — return expired deadlines
- `cancel(player_email)` — remove deadline when valid response arrives
- `clear()` — remove all deadlines on game complete/abort

Lives on GMC instance (per-game). Timeout seconds from `config["player_response_timeout_seconds"]` (default: 40).

**Deadlines set at:**
- `warmup_initiator.py` — after sending Q21_WARMUP_CALL
- `warmup.py` handler — after sending Q21_ROUND_START
- `questions.py` handler — after sending Q21_ANSWERS_BATCH

**Deadlines cancelled at:**
- `router.py` — when valid player response arrives, cancel that player's deadline

### 3.2 IncomingValidator (`_gmc/incoming_validator.py`)

Validates incoming player messages before routing:

1. **Body JSON:** `message_type` present, `sender.email` present, `payload` is dict
2. **Per-message payload:**
   - `Q21_WARMUP_RESPONSE`: payload has `answer`
   - `Q21_QUESTIONS_BATCH`: payload has `questions` (list)
   - `Q21_GUESS_SUBMISSION`: payload is dict with content

Returns list of validation errors (empty = valid).

**Runs in:** `orchestrator.route_player_message()` before calling GMC. Bad format → abort.

### 3.3 Polling Loop Integration

`rlgm_runner._poll_and_process()` gains a new step after message processing:

```
check_deadlines() → if expired → abort_current_game("player_timeout:email")
```

### 3.4 Orchestrator Changes

- New `check_deadlines()` method
- `route_player_message()` validates format before routing
- Bad format → `abort_current_game("format_violation:email")`

## 4. File Impact

| File | Action | Change |
|------|--------|--------|
| `_gmc/deadline_tracker.py` | Create | ~60 lines |
| `_gmc/incoming_validator.py` | Create | ~60 lines |
| `_gmc/gmc.py` | Modify | Add tracker attribute |
| `_gmc/router.py` | Modify | Cancel deadline on valid response |
| `_gmc/handlers/warmup.py` | Modify | Set deadline after round_start |
| `_gmc/handlers/questions.py` | Modify | Set deadline after answers |
| `_rlgm/orchestrator.py` | Modify | check_deadlines(), validate format |
| `_rlgm/warmup_initiator.py` | Modify | Set deadline after warmup call |
| `rlgm_runner.py` | Modify | Call check_deadlines() each cycle |
| `docs/prd-rlgm.md` | Modify | Add changelog entry |
| `CLAUDE.md` | Modify | Add new files to structure |

## 5. Testing

- `tests/test_deadline_tracker.py` — set/cancel/check_expired/clear
- `tests/test_incoming_validator.py` — per-message validation rules
- `tests/test_deadline_integration.py` — timeout → abort flow
- `tests/test_format_abort.py` — bad format → abort flow

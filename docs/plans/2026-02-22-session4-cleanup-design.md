# Session 4: File Splits — Design

Version: 1.0.0

## Overview

Get all source files under the CLAUDE.md 150-line limit. Pure mechanical splits — no behavior changes. Each split extracts a cohesive section into a new module and updates imports.

**Scope:** 8 source files over 150 lines. One exemption: `callbacks.py` (329 lines) is the student-facing abstract class — splitting would hurt discoverability.

**Not in scope:** The 13 remaining audit fixes (#15-17, #19, #27-40) are deferred to Session 5.

---

## Approach: Mechanical Extraction

Each split follows the same pattern:
1. Create new module with extracted code
2. Add re-exports in original module (backward compat for `__init__.py` imports)
3. Update direct imports in callers
4. Run tests — must pass unchanged
5. Verify both files under 150 lines

No behavior changes. No refactoring. No new logic.

---

## Changes

### 1. Split validator.py (421 lines → 3 files)

**Current structure:**
- Lines 1-100: `CALLBACK_SCHEMAS` dict, `SCORE_FEEDBACK_WORD_LIMITS`, `WORD_COUNT_PENALTY_PERCENT`
- Lines 101-155: `validate_output()` orchestrator
- Lines 156-370: `_check_required_fields()`, `_check_types()`, `_check_constraints()`, `_apply_constraints()`, `_count_words()`, `_check_list_items()`, `_check_nested()`
- Lines 374-421: `apply_score_feedback_penalties()`

**Split:**
- **`validator_schemas.py`** (~100 lines): `CALLBACK_SCHEMAS`, `SCORE_FEEDBACK_WORD_LIMITS`, `WORD_COUNT_PENALTY_PERCENT`
- **`validator_helpers.py`** (~140 lines): All `_check_*` and `_apply_*` helper functions
- **`validator.py`** (~90 lines): `validate_output()`, `apply_score_feedback_penalties()`, imports from the two new modules

**Callers to update:**
- `_gmc/callback_executor.py` imports `validate_output`, `apply_score_feedback_penalties`
- `_gmc/__init__.py` imports `validate_output`

Both import from `validator.py` which stays as the public API — no caller changes needed.

### 2. Split email_client.py (354 lines → 3 files)

**Current structure:**
- Lines 49-145: `EmailClient.__init__`, `connect_imap`, `_connect`, `_get_credentials`, `disconnect_imap`
- Lines 146-228: `poll`, `_parse_message`, `_get_json_from_attachments`, `_get_body`
- Lines 294-354: `send`

**Split:**
- **`email_auth.py`** (~100 lines): `GMAIL_SCOPES`, OAuth credential management (`_get_credentials`), extracted as standalone function
- **`email_reader.py`** (~130 lines): `poll`, `_parse_message`, `_get_json_from_attachments`, `_get_body`
- **`email_client.py`** (~120 lines): `EmailClient` class using `email_auth` for credentials and `email_reader`/`send` methods inline. Alternatively, keep `send` in the main class and extract only the reader methods.

**Callers to update:**
- `_shared/__init__.py` imports `EmailClient`
- `email_client.py` itself imports `get_protocol_logger`

`EmailClient` stays as the public class — no caller changes needed.

### 3. Split demo_ai.py (350 lines → 2 files)

**Current structure:**
- Lines 41-167: `DemoAI` class, `__init__`, `_load_private_data`, 4 callback methods
- Lines 192-351: `_calculate_scores`, `_calculate_similarity`, `_score_justification`, `_generate_feedback`

**Split:**
- **`demo_ai.py`** (~140 lines): `DemoAI` class with 4 callbacks + `_load_private_data` + `_read_demo_file`
- **`demo_scorer.py`** (~140 lines): Scoring functions extracted as module-level functions (take explicit params instead of `self`)

**Callers to update:**
- `__init__.py` imports `DemoAI`
- `cli.py` imports `DemoAI`

Both import `DemoAI` from `demo_ai.py` — no caller changes needed.

### 4. Split context_builder.py (259 lines → 2 files)

**Current structure:**
- Lines 1-53: `SERVICE_DEFINITIONS` dict
- Lines 59-260: `ContextBuilder` class with `_base_dynamic` + 4 builder methods

**Split:**
- **`context_service.py`** (~55 lines): `SERVICE_DEFINITIONS` dict only
- **`context_builder.py`** (~150 lines): `ContextBuilder` class, imports `SERVICE_DEFINITIONS` from `context_service`

**Callers to update:**
- `handlers/warmup.py`, `handlers/questions.py`, `handlers/scoring.py` import `SERVICE_DEFINITIONS`
- `_rlgm/warmup_initiator.py`, `_rlgm/abort_handler.py` import `ContextBuilder, SERVICE_DEFINITIONS`
- `_gmc/router.py` imports `ContextBuilder`
- `_gmc/__init__.py` imports `ContextBuilder, SERVICE_DEFINITIONS`

Update callers that import `SERVICE_DEFINITIONS` to import from `context_service`. Re-export from `context_builder` for backward compat.

### 5. Split envelope_builder.py (221 lines → 2 files)

**Current structure:**
- Lines 1-31: Helper functions (`_now_iso`, `_msg_id`, `_email_subject`)
- Lines 32-90: `EnvelopeBuilder` class + base templates
- Lines 93-222: 5 message builder methods

**Split:**
- **`envelope_helpers.py`** (~35 lines): `_now_iso`, `_msg_id`, `_email_subject`
- **`envelope_builder.py`** (~140 lines): `EnvelopeBuilder` class, imports helpers

**Callers to update:**
- `_gmc/gmc.py`, `_gmc/router.py`, `_gmc/__init__.py` import `EnvelopeBuilder`

All import `EnvelopeBuilder` from `envelope_builder.py` — no caller changes needed.

### 6. Split protocol_logger.py (221 lines → 2 files)

**Current structure:**
- Lines 1-93: Color codes + 5 mapping dicts (`RECEIVE_DISPLAY_NAMES`, `SEND_DISPLAY_NAMES`, `EXPECTED_RESPONSES`, `DEFAULT_DEADLINES`, `CALLBACK_DISPLAY_NAMES`)
- Lines 95-222: `ProtocolLogger` class + singleton `get_protocol_logger()`

**Split:**
- **`protocol_display.py`** (~90 lines): Color codes + all 5 mapping dicts
- **`protocol_logger.py`** (~130 lines): `ProtocolLogger` class + singleton, imports display config

**Callers to update:**
- `email_client.py`, `callback_executor.py`, `runner_protocol_context.py`, `_shared/__init__.py` import from `protocol_logger`

All import `get_protocol_logger` or `ProtocolLogger` — no caller changes needed (class stays in `protocol_logger.py`).

### 7. Split logging_config.py (187 lines → 2 files)

**Current structure:**
- Lines 30-122: `ProtocolFilter`, `TerminalFormatter`, `JSONFormatter`, `setup_logging()`
- Lines 124-188: `log_callback_error()`, `log_and_terminate()`, protocol mode functions

**Split:**
- **`logging_formatters.py`** (~95 lines): `ProtocolFilter`, `TerminalFormatter`, `JSONFormatter` classes
- **`logging_config.py`** (~95 lines): `setup_logging()`, `log_callback_error()`, `log_and_terminate()`, protocol mode functions — imports formatters

**Callers to update:**
- `_shared/__init__.py` imports multiple symbols from `logging_config`
- `callback_executor.py` imports `log_and_terminate`

Re-export from `logging_config.py` for backward compat.

### 8. Split errors.py (158 lines → 2 files)

**Current structure:**
- Lines 1-101: `Q21RefereeError`, `CallbackTimeoutError`, `InvalidJSONResponseError`, `SchemaValidationError`
- Lines 103-158: `_format_error_block()`, `_indent_json()`

**Split:**
- **`error_formatter.py`** (~60 lines): `_format_error_block()`, `_indent_json()`
- **`errors.py`** (~100 lines): Exception classes, imports formatter

**Callers to update:**
- `__init__.py`, `_gmc/timeout.py`, `_gmc/callback_executor.py` import from `errors`

All import exception classes — no caller changes needed (formatter is internal).

### 9. Update PRD

Bump `docs/prd-rlgm.md` to v2.7.0. Add Session 4 change history entry listing all file splits. Update file structure section.

---

## File Impact Summary

| Original File | Lines | New Files Created | Post-Split Lines |
|---|---|---|---|
| `_gmc/validator.py` | 421 | `validator_schemas.py`, `validator_helpers.py` | ~90, ~100, ~140 |
| `_shared/email_client.py` | 354 | `email_auth.py`, `email_reader.py` | ~120, ~100, ~130 |
| `demo_ai.py` | 350 | `demo_scorer.py` | ~140, ~140 |
| `_gmc/context_builder.py` | 259 | `context_service.py` | ~150, ~55 |
| `_gmc/envelope_builder.py` | 221 | `envelope_helpers.py` | ~140, ~35 |
| `_shared/protocol_logger.py` | 221 | `protocol_display.py` | ~130, ~90 |
| `_shared/logging_config.py` | 187 | `logging_formatters.py` | ~95, ~95 |
| `errors.py` | 158 | `error_formatter.py` | ~100, ~60 |

**New files created:** 8
**Total source files after split:** ~50

## Test Strategy

No new tests needed. All splits are mechanical — existing tests must pass unchanged after each split. Run `pytest tests/ -v` after every split.

## Risks

- **Import cycles:** Splitting within the same package could create circular imports. Mitigation: extract data/config modules (schemas, display maps) that have no internal imports.
- **Re-export drift:** If callers import from the original module via `__init__.py`, re-exports must be maintained. Mitigation: keep re-exports in original module.
- **Test file splits:** `test_orchestrator.py` (282 lines) and other test files are over 150. Decision: defer test file splits — they're not source code.

## Excluded from Session 4

- `callbacks.py` (329 lines) — exempted, student-facing API
- 13 remaining audit fixes (#15-17, #19, #27-40) — Session 5
- Test file splits — not source code, lower priority

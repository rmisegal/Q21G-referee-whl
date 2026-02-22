# Session 4: File Splits — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get all source files under the CLAUDE.md 150-line limit through mechanical extraction splits.

**Architecture:** Pure mechanical splits — extract cohesive sections into new modules, add re-exports in original module for backward compat, update direct imports. No behavior changes.

**Tech Stack:** Python, pytest

**Design Doc:** `docs/plans/2026-02-22-session4-cleanup-design.md`

**Baseline:** 277 tests pass. 8 source files over 150 lines.

---

### Task 1: Split validator.py (421 lines -> 3 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/_gmc/validator_schemas.py`
- Create: `src/q21_referee/_gmc/validator_helpers.py`
- Modify: `src/q21_referee/_gmc/validator.py`

**Current structure:**
- Lines 1-101: `CALLBACK_SCHEMAS`, `SCORE_FEEDBACK_WORD_LIMITS`, `WORD_COUNT_PENALTY_PERCENT`
- Lines 107-154: `validate_output()` orchestrator
- Lines 161-371: `_check_required_fields`, `_check_types`, `_check_constraints`, `_apply_constraints`, `_count_words`, `_check_list_items`, `_check_nested`
- Lines 374-421: `apply_score_feedback_penalties()`

**Callers (no changes needed — they import from `validator.py` which stays as public API):**
- `_gmc/callback_executor.py:21` — `from .validator import validate_output, apply_score_feedback_penalties`
- `_gmc/__init__.py:19` — `from .validator import validate_output`

**Step 1: Create `validator_schemas.py`**

Extract lines 1-101 (file header, imports, `CALLBACK_SCHEMAS`, `SCORE_FEEDBACK_WORD_LIMITS`, `WORD_COUNT_PENALTY_PERCENT`) into new file `src/q21_referee/_gmc/validator_schemas.py`.

Add header:
```python
# Area: GMC
# PRD: docs/prd-rlgm.md
```

Keep only the needed imports: `from __future__ import annotations` and `from typing import Any, Dict`.

**Step 2: Create `validator_helpers.py`**

Extract lines 161-371 (all `_check_*`, `_apply_*`, `_count_words` functions) into `src/q21_referee/_gmc/validator_helpers.py`.

Add header. Import `from typing import Any, Dict, List`.

**Step 3: Update `validator.py`**

Replace the file with just the orchestrator functions:
- `validate_output()` (lines 107-154)
- `apply_score_feedback_penalties()` (lines 374-421)
- Import `CALLBACK_SCHEMAS`, `SCORE_FEEDBACK_WORD_LIMITS`, `WORD_COUNT_PENALTY_PERCENT` from `.validator_schemas`
- Import all helper functions from `.validator_helpers`
- Re-export `CALLBACK_SCHEMAS` for backward compat (used by `__init__.py`)

**Step 4: Verify line counts**

Run: `wc -l src/q21_referee/_gmc/validator_schemas.py src/q21_referee/_gmc/validator_helpers.py src/q21_referee/_gmc/validator.py`

All three must be under 150 lines.

**Step 5: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 6: Commit**

```bash
git add src/q21_referee/_gmc/validator_schemas.py src/q21_referee/_gmc/validator_helpers.py src/q21_referee/_gmc/validator.py
git commit -m "Split validator.py (421->3 files) — schemas, helpers, orchestrator"
```

---

### Task 2: Split email_client.py (354 lines -> 3 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/_shared/email_auth.py`
- Create: `src/q21_referee/_shared/email_reader.py`
- Modify: `src/q21_referee/_shared/email_client.py`

**Current structure:**
- Lines 19-46: Imports, `GMAIL_SCOPES`
- Lines 49-145: `EmailClient.__init__`, `connect_imap`, `_connect`, `_get_credentials`, `disconnect_imap`
- Lines 146-293: `poll`, `_parse_message`, `_get_json_from_attachments`, `_get_body`
- Lines 295-354: `send`

**Callers (no changes needed — they import `EmailClient` which stays):**
- `_shared/__init__.py:12` — `from .email_client import EmailClient`

**Step 1: Create `email_auth.py`**

Extract `GMAIL_SCOPES` and `_get_credentials` as a standalone function (takes `credentials_path`, `token_path` params instead of `self`):

```python
# Area: Shared
# PRD: docs/prd-rlgm.md
"""OAuth2 credential management for Gmail API."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger("q21_referee.email")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials(credentials_path: str, token_path: str) -> Credentials:
    """Get or refresh OAuth2 credentials."""
    # ... (exact copy of EmailClient._get_credentials body, using params instead of self.*)
```

**Step 2: Create `email_reader.py`**

Extract `poll`, `_parse_message`, `_get_json_from_attachments`, `_get_body` as methods on a mixin or as module-level functions that take `service` as parameter. Since these methods use `self._service` and `self._connect()`, the cleanest approach is to keep them as part of `EmailClient` but in a separate file using a mixin pattern.

Alternative (simpler): Extract as standalone functions that take `service` parameter. `poll` also needs `_connect` fallback, so it's simpler to keep `poll` in the main class and only extract the parser helpers.

**Recommended approach:** Keep `EmailClient` as the single class in `email_client.py` but extract:
- `email_auth.py`: `GMAIL_SCOPES` + `get_credentials()` standalone function (~50 lines)
- `email_reader.py`: `_parse_message()`, `_get_json_from_attachments()`, `_get_body()` as standalone functions taking required params (~100 lines)
- `email_client.py`: `EmailClient` class with `__init__`, `connect_imap`, `_connect`, `disconnect_imap`, `poll` (calls reader functions), `send` (~130 lines)

In `email_reader.py`:
```python
def parse_message(msg: dict, service) -> Optional[Dict[str, Any]]:
    """Parse Gmail API message into standard format."""
    # ... same body but uses `service` param for attachment fetching

def get_json_from_attachments(msg: dict, service) -> Optional[Dict[str, Any]]:
    """Extract JSON from email attachments."""
    # ... same body but uses `service` param

def get_body(payload: dict) -> str:
    """Extract text body from message payload."""
    # ... exact same body (no self usage)
```

**Step 3: Update `email_client.py`**

- Import `GMAIL_SCOPES`, `get_credentials` from `.email_auth`
- Import `parse_message`, `get_json_from_attachments`, `get_body` from `.email_reader`
- Replace `self._get_credentials()` with `get_credentials(self.credentials_path, self.token_path)`
- Replace `self._parse_message(msg)` with `parse_message(msg, self._service)`
- Remove the extracted method bodies

**Step 4: Verify line counts**

Run: `wc -l src/q21_referee/_shared/email_auth.py src/q21_referee/_shared/email_reader.py src/q21_referee/_shared/email_client.py`

All three must be under 150 lines.

**Step 5: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 6: Commit**

```bash
git add src/q21_referee/_shared/email_auth.py src/q21_referee/_shared/email_reader.py src/q21_referee/_shared/email_client.py
git commit -m "Split email_client.py (354->3 files) — auth, reader, client"
```

---

### Task 3: Split demo_ai.py (350 lines -> 2 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/demo_scorer.py`
- Modify: `src/q21_referee/demo_ai.py`

**Current structure:**
- Lines 28-167: `DemoAI` class — `__init__`, `_load_private_data`, `_read_demo_file`, 4 callback methods
- Lines 192-351: Scoring methods — `_calculate_scores`, `_calculate_similarity`, `_score_justification`, `_generate_feedback`

**Callers (no changes needed — they import `DemoAI` which stays):**
- `__init__.py:40` — `from .demo_ai import DemoAI`
- `cli.py` — `from .demo_ai import DemoAI`

**Step 1: Create `demo_scorer.py`**

Extract `_calculate_scores`, `_calculate_similarity`, `_score_justification`, `_generate_feedback` as module-level functions (replace `self` with explicit parameters):

```python
# Area: Shared
# PRD: docs/prd-rlgm.md
"""Scoring functions for DemoAI."""

from typing import Any, Dict


def calculate_scores(
    actual_sentence: str, actual_word: str,
    sentence_guess: str, sentence_just: str,
    word_guess: str, word_just: str,
) -> Dict[str, Any]:
    """Calculate all scores for a player's guess."""
    # ... exact same body, calling calculate_similarity etc. (no self.)


def calculate_similarity(actual: str, guess: str) -> float:
    # ... exact same body (no self.)


def score_justification(text: str, min_words: int, max_words: int) -> float:
    # ... exact same body (no self.)


def generate_feedback(sentence_score: float, word_score: float, actual_word: str) -> Dict[str, str]:
    # ... exact same body (no self.)
```

Note: Remove the leading `_` from function names since they're now module-level public functions.

**Step 2: Update `demo_ai.py`**

- Add `from .demo_scorer import calculate_scores` at top
- In `get_score_feedback`, replace `self._calculate_scores(...)` with `calculate_scores(...)`
- Remove the 4 method bodies (lines 192-351)

**Step 3: Verify line counts**

Run: `wc -l src/q21_referee/demo_scorer.py src/q21_referee/demo_ai.py`

Both must be under 150 lines.

**Step 4: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 5: Commit**

```bash
git add src/q21_referee/demo_scorer.py src/q21_referee/demo_ai.py
git commit -m "Split demo_ai.py (350->2 files) — scorer extracted"
```

---

### Task 4: Split context_builder.py (259 lines -> 2 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/_gmc/context_service.py`
- Modify: `src/q21_referee/_gmc/context_builder.py`
- Modify: `src/q21_referee/_gmc/__init__.py` (update import source for `SERVICE_DEFINITIONS`)

**Current structure:**
- Lines 27-52: `SERVICE_DEFINITIONS` dict
- Lines 59-259: `ContextBuilder` class

**Callers that import `SERVICE_DEFINITIONS`:**
- `_gmc/handlers/warmup.py:14` — `from ..context_builder import SERVICE_DEFINITIONS`
- `_gmc/handlers/questions.py:14` — `from ..context_builder import SERVICE_DEFINITIONS`
- `_gmc/handlers/scoring.py:14` — `from ..context_builder import SERVICE_DEFINITIONS`
- `_gmc/__init__.py:16` — `from .context_builder import ContextBuilder, SERVICE_DEFINITIONS`
- `_rlgm/abort_handler.py:15` — `from .._gmc.context_builder import ContextBuilder, SERVICE_DEFINITIONS`
- `_rlgm/warmup_initiator.py:17` — `from .._gmc.context_builder import ContextBuilder, SERVICE_DEFINITIONS`

**Step 1: Create `context_service.py`**

Extract `SERVICE_DEFINITIONS` dict:

```python
# Area: GMC
# PRD: docs/prd-rlgm.md
"""Service definitions for student callbacks."""

from __future__ import annotations
from typing import Any, Dict

SERVICE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # ... exact copy of the dict
}
```

**Step 2: Update `context_builder.py`**

- Add `from .context_service import SERVICE_DEFINITIONS` at top
- Remove the `SERVICE_DEFINITIONS` dict definition (lines 23-52)
- Keep re-export: the import makes `SERVICE_DEFINITIONS` available from this module
- Result: ~150 lines (class + imports + re-export)

If still over 150 lines, trim docstring verbosity in the builder methods.

**Step 3: Update `_gmc/__init__.py`**

Change line 16 from:
```python
from .context_builder import ContextBuilder, SERVICE_DEFINITIONS
```
to:
```python
from .context_builder import ContextBuilder
from .context_service import SERVICE_DEFINITIONS
```

**Step 4: Update handler imports (optional)**

The handlers import `from ..context_builder import SERVICE_DEFINITIONS`. This still works because `context_builder.py` re-exports it. No changes strictly needed, but for clarity, update:
- `handlers/warmup.py:14` → `from ..context_service import SERVICE_DEFINITIONS`
- `handlers/questions.py:14` → `from ..context_service import SERVICE_DEFINITIONS`
- `handlers/scoring.py:14` → `from ..context_service import SERVICE_DEFINITIONS`

Also update cross-package imports:
- `_rlgm/abort_handler.py:15` → keep `from .._gmc.context_builder import ContextBuilder` + add `from .._gmc.context_service import SERVICE_DEFINITIONS`
- `_rlgm/warmup_initiator.py:17` → same pattern

**Step 5: Verify line counts**

Run: `wc -l src/q21_referee/_gmc/context_service.py src/q21_referee/_gmc/context_builder.py`

Both must be under 150 lines.

**Step 6: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 7: Commit**

```bash
git add src/q21_referee/_gmc/context_service.py src/q21_referee/_gmc/context_builder.py src/q21_referee/_gmc/__init__.py src/q21_referee/_gmc/handlers/warmup.py src/q21_referee/_gmc/handlers/questions.py src/q21_referee/_gmc/handlers/scoring.py src/q21_referee/_rlgm/abort_handler.py src/q21_referee/_rlgm/warmup_initiator.py
git commit -m "Split context_builder.py (259->2 files) — service defs extracted"
```

---

### Task 5: Split envelope_builder.py (221 lines -> 2 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/_gmc/envelope_helpers.py`
- Modify: `src/q21_referee/_gmc/envelope_builder.py`

**Current structure:**
- Lines 19-29: `_now_iso()`, `_msg_id()`, `_email_subject()`
- Lines 32-221: `EnvelopeBuilder` class (5 builder methods)

**Callers (no changes needed — they import `EnvelopeBuilder` which stays):**
- `_gmc/gmc.py`, `_gmc/router.py`, `_gmc/__init__.py:15`

**Step 1: Create `envelope_helpers.py`**

Extract the 3 helper functions:

```python
# Area: GMC
# PRD: docs/prd-rlgm.md
"""Helper functions for envelope construction."""

import uuid
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def msg_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def email_subject(protocol: str, role: str, email: str,
                  tx_id: str, message_type: str) -> str:
    return f"{protocol}::{role}::{email}::{tx_id}::{message_type}"
```

Note: Drop the leading `_` since they're now module-level public functions. Update all call sites in `envelope_builder.py`.

**Step 2: Update `envelope_builder.py`**

- Add `from .envelope_helpers import now_iso, msg_id, email_subject` at top
- Replace `_now_iso()` calls with `now_iso()`
- Replace `_msg_id(...)` calls with `msg_id(...)`
- Replace `_email_subject(...)` calls with `email_subject(...)`
- Remove the 3 function definitions

**Step 3: Verify line counts**

Run: `wc -l src/q21_referee/_gmc/envelope_helpers.py src/q21_referee/_gmc/envelope_builder.py`

Both must be under 150 lines. `envelope_helpers.py` ~20 lines, `envelope_builder.py` ~195 lines.

If `envelope_builder.py` is still over 150, look for further extraction. The `build_match_result` method (lines 195-221) could move to a second file, or collapse the repeated `from datetime import timedelta` imports (lines 100, 125, 152) into a single top-level import to save lines. Also strip redundant section comment lines.

**Step 4: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 5: Commit**

```bash
git add src/q21_referee/_gmc/envelope_helpers.py src/q21_referee/_gmc/envelope_builder.py
git commit -m "Split envelope_builder.py (221->2 files) — helpers extracted"
```

---

### Task 6: Split protocol_logger.py (221 lines -> 2 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/_shared/protocol_display.py`
- Modify: `src/q21_referee/_shared/protocol_logger.py`

**Current structure:**
- Lines 20-92: Color codes + 5 mapping dicts (`RECEIVE_DISPLAY_NAMES`, `SEND_DISPLAY_NAMES`, `EXPECTED_RESPONSES`, `DEFAULT_DEADLINES`, `CALLBACK_DISPLAY_NAMES`)
- Lines 95-221: `ProtocolLogger` class + singleton `get_protocol_logger()`

**Callers (no changes needed — they import `ProtocolLogger`/`get_protocol_logger` which stay):**
- `_shared/__init__.py:30` — `from .protocol_logger import get_protocol_logger, ProtocolLogger`
- `_shared/email_client.py:38` — `from .protocol_logger import get_protocol_logger`
- `_gmc/callback_executor.py` — `from .._shared.protocol_logger import get_protocol_logger`

**Step 1: Create `protocol_display.py`**

Extract color codes + all 5 mapping dicts:

```python
# Area: Shared
# PRD: docs/LOGGER_OUTPUT_REFEREE.md
"""Display constants for protocol logging."""

# ANSI Color Codes
GREEN = "\033[32m"
ORANGE = "\033[38;5;208m"
RED = "\033[31m"
RESET = "\033[0m"

RECEIVE_DISPLAY_NAMES = { ... }
SEND_DISPLAY_NAMES = { ... }
EXPECTED_RESPONSES = { ... }
DEFAULT_DEADLINES = { ... }
CALLBACK_DISPLAY_NAMES = { ... }
```

**Step 2: Update `protocol_logger.py`**

- Add `from .protocol_display import (GREEN, ORANGE, RED, RESET, RECEIVE_DISPLAY_NAMES, SEND_DISPLAY_NAMES, EXPECTED_RESPONSES, DEFAULT_DEADLINES, CALLBACK_DISPLAY_NAMES)` at top
- Remove the constant definitions (lines 20-92)

**Step 3: Verify line counts**

Run: `wc -l src/q21_referee/_shared/protocol_display.py src/q21_referee/_shared/protocol_logger.py`

Both must be under 150 lines.

**Step 4: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 5: Commit**

```bash
git add src/q21_referee/_shared/protocol_display.py src/q21_referee/_shared/protocol_logger.py
git commit -m "Split protocol_logger.py (221->2 files) — display constants extracted"
```

---

### Task 7: Split logging_config.py (187 lines -> 2 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/_shared/logging_formatters.py`
- Modify: `src/q21_referee/_shared/logging_config.py`

**Current structure:**
- Lines 30-75: `ProtocolFilter`, `TerminalFormatter`, `JSONFormatter` classes
- Lines 77-187: `setup_logging()`, `log_callback_error()`, `log_and_terminate()`, protocol mode functions

**Callers (no changes needed — they import from `logging_config`):**
- `_shared/__init__.py:13-20` — imports 6 symbols from `logging_config`
- `_gmc/callback_executor.py:22` — `from .._shared.logging_config import log_and_terminate`

**Step 1: Create `logging_formatters.py`**

Extract the 3 formatter/filter classes:

```python
# Area: Shared
# PRD: docs/prd-rlgm.md
"""Logging formatters and filters."""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone


class ProtocolFilter(logging.Filter):
    # ... exact copy

class TerminalFormatter(logging.Formatter):
    # ... exact copy

class JSONFormatter(logging.Formatter):
    # ... exact copy
```

Note: `ProtocolFilter` references `_protocol_mode_enabled` from `logging_config`. To avoid circular imports, pass the flag via a function reference. The simplest approach: `ProtocolFilter` imports `is_protocol_mode_enabled` from `logging_config`. But that creates a circular import.

**Better approach:** Keep `_protocol_mode_enabled` and `ProtocolFilter` together. Extract only `TerminalFormatter` and `JSONFormatter` to `logging_formatters.py`. This avoids circular imports.

Even simpler: Move the `_protocol_mode_enabled` flag into `logging_formatters.py` along with `ProtocolFilter`, `enable_protocol_mode`, `disable_protocol_mode`, `is_protocol_mode_enabled`. Then `logging_config.py` imports from `logging_formatters.py`.

Recommended split:
- **`logging_formatters.py`** (~60 lines): `ProtocolFilter`, `TerminalFormatter`, `JSONFormatter`, `_protocol_mode_enabled`, `enable_protocol_mode`, `disable_protocol_mode`, `is_protocol_mode_enabled`
- **`logging_config.py`** (~80 lines): `setup_logging()`, `log_callback_error()`, `log_and_terminate()` — imports formatters

Update `_shared/__init__.py` to also import from `logging_formatters`:
```python
from .logging_formatters import (
    enable_protocol_mode,
    disable_protocol_mode,
    is_protocol_mode_enabled,
)
from .logging_config import (
    setup_logging,
    log_and_terminate,
    log_callback_error,
)
```

Or keep re-exports in `logging_config.py` so `__init__.py` doesn't change.

**Step 2: Update `logging_config.py`**

- Import `ProtocolFilter, TerminalFormatter, JSONFormatter` from `.logging_formatters`
- Import `enable_protocol_mode, disable_protocol_mode, is_protocol_mode_enabled` for re-export
- Remove the class/function definitions that moved

**Step 3: Verify line counts**

Run: `wc -l src/q21_referee/_shared/logging_formatters.py src/q21_referee/_shared/logging_config.py`

Both must be under 150 lines.

**Step 4: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 5: Commit**

```bash
git add src/q21_referee/_shared/logging_formatters.py src/q21_referee/_shared/logging_config.py src/q21_referee/_shared/__init__.py
git commit -m "Split logging_config.py (187->2 files) — formatters extracted"
```

---

### Task 8: Split errors.py (158 lines -> 2 files)

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7). No behavior changes.

**Files:**
- Create: `src/q21_referee/error_formatter.py`
- Modify: `src/q21_referee/errors.py`

**Current structure:**
- Lines 14-100: `Q21RefereeError`, `CallbackTimeoutError`, `InvalidJSONResponseError`, `SchemaValidationError`
- Lines 103-158: `_format_error_block()`, `_indent_json()`

**Callers (no changes needed — they import exception classes from `errors`):**
- `__init__.py:43-48` — imports 4 exception classes
- `_gmc/timeout.py:28` — `from ..errors import CallbackTimeoutError`
- `_gmc/callback_executor.py:15-18` — imports 3 exception classes
- `_shared/logging_config.py:21` — `from ..errors import Q21RefereeError` (TYPE_CHECKING)

**Step 1: Create `error_formatter.py`**

Extract `_format_error_block()` and `_indent_json()`:

```python
# Area: Shared
# PRD: docs/prd-rlgm.md
"""Error formatting for structured callback error logs."""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional


def format_error_block(
    error_type: str,
    callback_name: str,
    deadline_seconds: Optional[int],
    input_payload: Dict[str, Any],
    output_payload: Optional[Dict[str, Any]],
    validation_errors: Optional[List[str]],
) -> str:
    # ... exact same body


def indent_json(data: Dict[str, Any], indent: int = 2) -> str:
    # ... exact same body
```

Note: Drop leading `_` since these are now module-level functions. Update call sites in `errors.py`.

**Step 2: Update `errors.py`**

- Add `from .error_formatter import format_error_block, indent_json` at top
- Replace `_format_error_block(...)` calls with `format_error_block(...)`
- Remove the function definitions (lines 103-158)

**Step 3: Verify line counts**

Run: `wc -l src/q21_referee/error_formatter.py src/q21_referee/errors.py`

Both must be under 150 lines.

**Step 4: Run tests**

Run: `pytest tests/ -q`
Expected: 277 passed

**Step 5: Commit**

```bash
git add src/q21_referee/error_formatter.py src/q21_referee/errors.py
git commit -m "Split errors.py (158->2 files) — formatter extracted"
```

---

### Task 9: Update PRD to v2.7.0

**CLAUDE.md checkpoint:** When code changes, update the corresponding PRD (Doc §3). Increment version.

**Files:**
- Modify: `docs/prd-rlgm.md`

**Step 1: Update PRD**

- Bump version to `2.7.0`
- Add Session 4 change history entry listing all 8 file splits
- Update the file structure section to include new files:
  - `_gmc/validator_schemas.py`, `_gmc/validator_helpers.py`
  - `_gmc/context_service.py`
  - `_gmc/envelope_helpers.py`
  - `_shared/email_auth.py`, `_shared/email_reader.py`
  - `_shared/protocol_display.py`, `_shared/logging_formatters.py`
  - `error_formatter.py`, `demo_scorer.py`

**Step 2: Commit**

```bash
git add docs/prd-rlgm.md
git commit -m "Update PRD to v2.7.0 — Session 4 file splits"
```

---

### Task 10: Full compliance audit

**CLAUDE.md checkpoint:** All Python files must stay under 150 lines (Principle 7).

**Step 1: Check all source files under 150 lines**

Run: `find src/q21_referee -name "*.py" -not -path "*__pycache__*" | xargs wc -l | sort -n`

Verify ALL files ≤ 150 lines (except `callbacks.py` which is exempted at 329 lines).

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: 277 passed (or more if any tests were added)

**Step 3: Verify no `# NOTE:` split markers remain**

Run: `grep -r "NOTE.*split\|NOTE.*Part 22\|exceeds 150" src/q21_referee/ --include="*.py"`

Remove any stale split-marker comments.

**Step 4: Commit cleanup if needed**

```bash
git add -A && git commit -m "Session 4 complete — all source files under 150 lines"
```

# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.timeout — Callback timeout enforcement
========================================================

Context manager that enforces a wall-clock deadline on student callbacks
using POSIX ``signal.SIGALRM``.

Signal re-entrancy note (Issue #34)
------------------------------------
``signal.signal()`` is *not* re-entrant. If two threads race to set
SIGALRM handlers, one handler silently overwrites the other. This is
safe in the current design because callbacks always run on the main
thread, and the RLGM event loop is single-threaded.  If we ever move
to concurrent callback execution, replace this with a
``threading.Timer`` fallback (see Task 8 in the resilience plan).

On non-Unix platforms (Windows), ``SIGALRM`` is unavailable and the
context manager becomes a no-op — callbacks run without a timeout.
"""

from __future__ import annotations

import signal
from typing import Dict, Any

from ..errors import CallbackTimeoutError


class TimeoutHandler:
    """Context manager for callback timeout enforcement."""

    def __init__(self, seconds: int, callback_name: str, input_payload: Dict[str, Any]):
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
        # Only use signal-based timeout on Unix systems
        if hasattr(signal, "SIGALRM"):
            self._old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)  # Cancel the alarm
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False  # Don't suppress exceptions

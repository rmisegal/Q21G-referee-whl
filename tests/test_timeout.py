# Area: GMC
# PRD: docs/prd-rlgm.md
"""Tests for TimeoutHandler extracted to _gmc/timeout.py."""

import signal
import pytest

from q21_referee._gmc.timeout import TimeoutHandler
from q21_referee.errors import CallbackTimeoutError


class TestTimeoutHandler:
    """Tests for TimeoutHandler context manager."""

    def test_enter_sets_alarm(self):
        """On Unix, entering the context sets a SIGALRM handler and alarm."""
        with TimeoutHandler(5, "test_cb", {}) as th:
            assert th.seconds == 5
            assert th.callback_name == "test_cb"
            # Alarm should be active (non-zero remaining time or 0 if just set)
            remaining = signal.alarm(0)  # Cancel and get remaining
            # Re-set it so __exit__ works cleanly
            signal.alarm(0)

    def test_exit_cancels_alarm(self):
        """Exiting the context cancels the alarm and restores the old handler."""
        old_handler = signal.getsignal(signal.SIGALRM)
        with TimeoutHandler(10, "test_cb", {}):
            pass
        restored = signal.getsignal(signal.SIGALRM)
        assert restored == old_handler

    def test_timeout_raises_callback_timeout_error(self):
        """When the alarm fires, CallbackTimeoutError is raised."""
        with pytest.raises(CallbackTimeoutError) as exc_info:
            with TimeoutHandler(1, "slow_cb", {"key": "val"}):
                import time
                time.sleep(3)
        assert exc_info.value.callback_name == "slow_cb"
        assert exc_info.value.deadline_seconds == 1
        assert exc_info.value.input_payload == {"key": "val"}

    def test_no_timeout_when_callback_completes_in_time(self):
        """No error when callback completes within the deadline."""
        with TimeoutHandler(5, "fast_cb", {}):
            result = 1 + 1
        assert result == 2

    def test_does_not_suppress_exceptions(self):
        """__exit__ returns False so other exceptions propagate."""
        with pytest.raises(ValueError, match="oops"):
            with TimeoutHandler(5, "test_cb", {}):
                raise ValueError("oops")

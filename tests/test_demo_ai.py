# Area: DemoAI Tests
# PRD: docs/prd-rlgm.md
"""Tests for DemoAI state management."""

from unittest.mock import patch

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

    def test_stale_state_cleared_on_failed_round(self):
        """State must be None (reset) even if get_round_start_info fails."""
        ai = DemoAI()
        ctx = {}

        # First call succeeds — sets _book_name
        ai.get_round_start_info(ctx)
        assert ai._book_name is not None

        # Patch _read_demo_file to raise, simulating file-read failure
        with patch.object(ai, "_read_demo_file", side_effect=OSError("boom")):
            try:
                ai.get_round_start_info(ctx)
            except OSError:
                pass

        # After a failed call, stale state should have been cleared
        # (reset happens BEFORE the file read that raised)
        assert ai._book_name is None
        assert ai._book_hint is None
        assert ai._association_domain is None

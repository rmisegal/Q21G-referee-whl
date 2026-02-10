# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_CRITICAL_PAUSE handler."""

import pytest
from unittest.mock import patch, Mock
from q21_referee._rlgm.handler_critical_pause import BroadcastCriticalPauseHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastCriticalPauseHandler:
    """Tests for BroadcastCriticalPauseHandler."""

    def create_handler_in_running_state(self):
        """Create handler with state machine in RUNNING state."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        handler = BroadcastCriticalPauseHandler(state_machine)
        return handler, state_machine

    def create_pause_message(self, reason="System maintenance"):
        """Create sample critical pause message."""
        return {
            "message_type": "BROADCAST_CRITICAL_PAUSE",
            "broadcast_id": "CP001",
            "payload": {
                "reason": reason,
                "timestamp": "2026-01-15T10:00:00Z",
            },
        }

    def test_pauses_state_machine(self):
        """Test that handler pauses the state machine."""
        handler, state_machine = self.create_handler_in_running_state()
        assert state_machine.current_state == RLGMState.RUNNING

        handler.handle(self.create_pause_message())

        assert state_machine.current_state == RLGMState.PAUSED
        assert state_machine.saved_state == RLGMState.RUNNING

    def test_stores_pause_reason(self):
        """Test that pause reason is stored."""
        handler, _ = self.create_handler_in_running_state()

        handler.handle(self.create_pause_message(reason="Emergency stop"))

        assert handler.pause_reason == "Emergency stop"

    def test_returns_none(self):
        """Test that handler returns None (no response needed)."""
        handler, _ = self.create_handler_in_running_state()

        result = handler.handle(self.create_pause_message())

        assert result is None

    def test_logs_pause(self):
        """Test that pause is logged."""
        handler, _ = self.create_handler_in_running_state()

        with patch("q21_referee._rlgm.handler_critical_pause.logger") as mock_logger:
            handler.handle(self.create_pause_message())
            mock_logger.warning.assert_called()

    def test_already_paused_is_noop(self):
        """Test that pausing when already paused does nothing."""
        handler, state_machine = self.create_handler_in_running_state()

        # First pause
        handler.handle(self.create_pause_message())
        assert state_machine.current_state == RLGMState.PAUSED
        saved = state_machine.saved_state

        # Second pause should not change saved state
        handler.handle(self.create_pause_message())
        assert state_machine.saved_state == saved

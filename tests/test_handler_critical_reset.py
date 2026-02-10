# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_CRITICAL_RESET handler."""

import pytest
from unittest.mock import patch
from q21_referee._rlgm.handler_critical_reset import BroadcastCriticalResetHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastCriticalResetHandler:
    """Tests for BroadcastCriticalResetHandler."""

    def create_handler_in_running_state(self):
        """Create handler with state machine in RUNNING state."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        handler = BroadcastCriticalResetHandler(state_machine)
        return handler, state_machine

    def create_reset_message(self, reason="Season cancelled"):
        """Create sample critical reset message."""
        return {
            "message_type": "BROADCAST_CRITICAL_RESET",
            "broadcast_id": "CR001",
            "payload": {
                "reason": reason,
                "timestamp": "2026-01-15T10:00:00Z",
            },
        }

    def test_resets_state_machine(self):
        """Test that handler resets the state machine."""
        handler, state_machine = self.create_handler_in_running_state()
        assert state_machine.current_state == RLGMState.RUNNING

        handler.handle(self.create_reset_message())

        assert state_machine.current_state == RLGMState.INIT_START_STATE

    def test_clears_saved_state(self):
        """Test that reset clears any saved state from pause."""
        handler, state_machine = self.create_handler_in_running_state()

        # First pause to create saved state
        state_machine.pause()
        assert state_machine.saved_state is not None

        # Then reset
        handler.handle(self.create_reset_message())

        assert state_machine.saved_state is None

    def test_stores_reset_reason(self):
        """Test that reset reason is stored."""
        handler, _ = self.create_handler_in_running_state()

        handler.handle(self.create_reset_message(reason="Technical issues"))

        assert handler.reset_reason == "Technical issues"

    def test_returns_none(self):
        """Test that handler returns None (no response needed)."""
        handler, _ = self.create_handler_in_running_state()

        result = handler.handle(self.create_reset_message())

        assert result is None

    def test_logs_reset(self):
        """Test that reset is logged."""
        handler, _ = self.create_handler_in_running_state()

        with patch("q21_referee._rlgm.handler_critical_reset.logger") as mock_logger:
            handler.handle(self.create_reset_message())
            mock_logger.warning.assert_called()

    def test_reset_from_any_state(self):
        """Test that reset works from any state."""
        state_machine = RLGMStateMachine()
        handler = BroadcastCriticalResetHandler(state_machine)

        # From INIT
        handler.handle(self.create_reset_message())
        assert state_machine.current_state == RLGMState.INIT_START_STATE

        # From WAITING_FOR_CONFIRMATION
        state_machine.transition(RLGMEvent.SEASON_START)
        handler.handle(self.create_reset_message())
        assert state_machine.current_state == RLGMState.INIT_START_STATE

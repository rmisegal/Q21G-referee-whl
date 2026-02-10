# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_END_SEASON handler."""

import pytest
from unittest.mock import patch
from q21_referee._rlgm.handler_end_season import BroadcastEndSeasonHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastEndSeasonHandler:
    """Tests for BroadcastEndSeasonHandler."""

    def create_handler_in_running_state(self):
        """Create handler with state machine in RUNNING state."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        handler = BroadcastEndSeasonHandler(state_machine)
        return handler, state_machine

    def create_end_season_message(self):
        """Create sample end season message."""
        return {
            "message_type": "BROADCAST_END_SEASON",
            "broadcast_id": "BC005",
            "payload": {
                "season_id": "SEASON_2026_Q1",
                "final_standings": [],
            },
        }

    def test_logs_season_completion(self):
        """Test that season completion is logged."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_end_season_message()

        with patch("q21_referee._rlgm.handler_end_season.logger") as mock_logger:
            handler.handle(message)
            mock_logger.info.assert_called()

    def test_transitions_to_completed(self):
        """Test that handler transitions to COMPLETED state."""
        handler, state_machine = self.create_handler_in_running_state()
        assert state_machine.current_state == RLGMState.RUNNING

        handler.handle(self.create_end_season_message())

        assert state_machine.current_state == RLGMState.COMPLETED

    def test_returns_none(self):
        """Test that handler returns None (no response needed)."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_end_season_message()

        result = handler.handle(message)

        assert result is None

    def test_extracts_season_id(self):
        """Test that season_id is extracted."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_end_season_message()

        handler.handle(message)

        assert handler.completed_season_id == "SEASON_2026_Q1"

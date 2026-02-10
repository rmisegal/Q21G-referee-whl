# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_END_LEAGUE_ROUND handler."""

import pytest
from unittest.mock import patch
from q21_referee._rlgm.handler_end_round import BroadcastEndRoundHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastEndRoundHandler:
    """Tests for BroadcastEndRoundHandler."""

    def create_handler_in_running_state(self):
        """Create handler with state machine in RUNNING state."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        handler = BroadcastEndRoundHandler(state_machine)
        return handler, state_machine

    def create_end_round_message(self, round_number=1, round_id="ROUND_1"):
        """Create sample end round message."""
        return {
            "message_type": "BROADCAST_END_LEAGUE_ROUND",
            "broadcast_id": "BC004",
            "payload": {
                "round_number": round_number,
                "round_id": round_id,
                "season_id": "SEASON_2026_Q1",
            },
        }

    def test_logs_round_completion(self):
        """Test that round completion is logged."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_end_round_message()

        with patch("q21_referee._rlgm.handler_end_round.logger") as mock_logger:
            handler.handle(message)
            mock_logger.info.assert_called()

    def test_returns_none(self):
        """Test that handler returns None (no response needed)."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_end_round_message()

        result = handler.handle(message)

        assert result is None

    def test_extracts_round_info(self):
        """Test that round info is extracted and stored."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_end_round_message(round_number=3, round_id="ROUND_3")

        handler.handle(message)

        assert handler.last_completed_round == 3
        assert handler.last_completed_round_id == "ROUND_3"

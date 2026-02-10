# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for SEASON_REGISTRATION_RESPONSE handler."""

import pytest
from q21_referee._rlgm.handler_registration_response import (
    SeasonRegistrationResponseHandler,
)
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestSeasonRegistrationResponseHandler:
    """Tests for SeasonRegistrationResponseHandler."""

    def create_handler_in_waiting_state(self):
        """Create handler with state machine in WAITING_FOR_CONFIRMATION."""
        state_machine = RLGMStateMachine()
        # Transition to WAITING_FOR_CONFIRMATION
        state_machine.transition(RLGMEvent.SEASON_START)
        return SeasonRegistrationResponseHandler(state_machine), state_machine

    def create_accepted_message(self):
        """Create an accepted registration response."""
        return {
            "message_type": "SEASON_REGISTRATION_RESPONSE",
            "payload": {
                "status": "accepted",
                "referee_id": "REF001",
                "season_id": "SEASON_2026_Q1",
            },
        }

    def create_rejected_message(self, reason="Quota full"):
        """Create a rejected registration response."""
        return {
            "message_type": "SEASON_REGISTRATION_RESPONSE",
            "payload": {
                "status": "rejected",
                "referee_id": "REF001",
                "reason": reason,
            },
        }

    def test_accepted_transitions_to_waiting_for_assignment(self):
        """Test that accepted status transitions to WAITING_FOR_ASSIGNMENT."""
        handler, state_machine = self.create_handler_in_waiting_state()
        assert state_machine.current_state == RLGMState.WAITING_FOR_CONFIRMATION

        handler.handle(self.create_accepted_message())

        assert state_machine.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

    def test_rejected_transitions_to_init(self):
        """Test that rejected status transitions back to INIT_START_STATE."""
        handler, state_machine = self.create_handler_in_waiting_state()
        assert state_machine.current_state == RLGMState.WAITING_FOR_CONFIRMATION

        handler.handle(self.create_rejected_message())

        assert state_machine.current_state == RLGMState.INIT_START_STATE

    def test_returns_none(self):
        """Test that handler returns None (no response needed)."""
        handler, _ = self.create_handler_in_waiting_state()

        result = handler.handle(self.create_accepted_message())

        assert result is None

    def test_extracts_status_from_payload(self):
        """Test that status is correctly extracted from payload."""
        handler, state_machine = self.create_handler_in_waiting_state()

        # Test with accepted
        handler.handle(self.create_accepted_message())
        assert state_machine.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

    def test_unknown_status_does_not_transition(self):
        """Test that unknown status does not change state."""
        handler, state_machine = self.create_handler_in_waiting_state()
        original_state = state_machine.current_state

        message = {
            "message_type": "SEASON_REGISTRATION_RESPONSE",
            "payload": {"status": "pending"},
        }
        handler.handle(message)

        assert state_machine.current_state == original_state

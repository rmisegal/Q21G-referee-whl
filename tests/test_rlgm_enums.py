# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM state and event enums."""

import pytest
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestRLGMState:
    """Tests for RLGMState enum."""

    def test_rlgm_state_values(self):
        """Test that all expected states exist with correct values."""
        assert RLGMState.INIT_START_STATE.value == "INIT_START_STATE"
        assert RLGMState.WAITING_FOR_CONFIRMATION.value == "WAITING_FOR_CONFIRMATION"
        assert RLGMState.WAITING_FOR_ASSIGNMENT.value == "WAITING_FOR_ASSIGNMENT"
        assert RLGMState.RUNNING.value == "RUNNING"
        assert RLGMState.IN_GAME.value == "IN_GAME"
        assert RLGMState.PAUSED.value == "PAUSED"
        assert RLGMState.COMPLETED.value == "COMPLETED"

    def test_rlgm_state_count(self):
        """Test that we have exactly 7 states."""
        assert len(RLGMState) == 7


class TestRLGMEvent:
    """Tests for RLGMEvent enum."""

    def test_rlgm_event_values(self):
        """Test that all expected events exist with correct values."""
        assert RLGMEvent.SEASON_START.value == "SEASON_START"
        assert RLGMEvent.REGISTRATION_ACCEPTED.value == "REGISTRATION_ACCEPTED"
        assert RLGMEvent.REGISTRATION_REJECTED.value == "REGISTRATION_REJECTED"
        assert RLGMEvent.ASSIGNMENT_RECEIVED.value == "ASSIGNMENT_RECEIVED"
        assert RLGMEvent.ROUND_START.value == "ROUND_START"
        assert RLGMEvent.GAME_COMPLETE.value == "GAME_COMPLETE"
        assert RLGMEvent.SEASON_END.value == "SEASON_END"
        assert RLGMEvent.PAUSE.value == "PAUSE"
        assert RLGMEvent.CONTINUE.value == "CONTINUE"
        assert RLGMEvent.RESET.value == "RESET"

    def test_rlgm_event_count(self):
        """Test that we have exactly 10 events."""
        assert len(RLGMEvent) == 10

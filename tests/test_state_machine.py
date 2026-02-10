# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM State Machine."""

import pytest
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestRLGMStateMachineBase:
    """Tests for basic state machine functionality."""

    def test_initial_state_is_init(self):
        """Test that state machine starts in INIT_START_STATE."""
        sm = RLGMStateMachine()
        assert sm.current_state == RLGMState.INIT_START_STATE

    def test_can_transition_returns_true_for_valid(self):
        """Test can_transition returns True for valid transitions."""
        sm = RLGMStateMachine()
        # From INIT_START_STATE, SEASON_START is valid
        assert sm.can_transition(RLGMEvent.SEASON_START) is True

    def test_can_transition_returns_false_for_invalid(self):
        """Test can_transition returns False for invalid transitions."""
        sm = RLGMStateMachine()
        # From INIT_START_STATE, ROUND_START is not valid
        assert sm.can_transition(RLGMEvent.ROUND_START) is False

    def test_transition_changes_state(self):
        """Test that transition changes state correctly."""
        sm = RLGMStateMachine()
        assert sm.current_state == RLGMState.INIT_START_STATE

        sm.transition(RLGMEvent.SEASON_START)
        assert sm.current_state == RLGMState.WAITING_FOR_CONFIRMATION

    def test_transition_raises_on_invalid(self):
        """Test that invalid transition raises ValueError."""
        sm = RLGMStateMachine()
        with pytest.raises(ValueError):
            sm.transition(RLGMEvent.ROUND_START)


class TestRLGMStateMachineTransitions:
    """Tests for specific state transitions."""

    def test_full_happy_path(self):
        """Test complete happy path through states."""
        sm = RLGMStateMachine()

        # INIT -> WAITING_FOR_CONFIRMATION
        sm.transition(RLGMEvent.SEASON_START)
        assert sm.current_state == RLGMState.WAITING_FOR_CONFIRMATION

        # WAITING_FOR_CONFIRMATION -> WAITING_FOR_ASSIGNMENT
        sm.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        assert sm.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

        # WAITING_FOR_ASSIGNMENT -> RUNNING
        sm.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        assert sm.current_state == RLGMState.RUNNING

        # RUNNING -> IN_GAME
        sm.transition(RLGMEvent.ROUND_START)
        assert sm.current_state == RLGMState.IN_GAME

        # IN_GAME -> RUNNING
        sm.transition(RLGMEvent.GAME_COMPLETE)
        assert sm.current_state == RLGMState.RUNNING

        # RUNNING -> COMPLETED
        sm.transition(RLGMEvent.SEASON_END)
        assert sm.current_state == RLGMState.COMPLETED

    def test_registration_rejected(self):
        """Test rejection returns to INIT."""
        sm = RLGMStateMachine()
        sm.transition(RLGMEvent.SEASON_START)
        sm.transition(RLGMEvent.REGISTRATION_REJECTED)
        assert sm.current_state == RLGMState.INIT_START_STATE


class TestRLGMStateMachinePauseResume:
    """Tests for pause/resume/reset functionality."""

    def test_pause_saves_current_state(self):
        """Test that pause saves the current state."""
        sm = RLGMStateMachine()
        sm.transition(RLGMEvent.SEASON_START)
        sm.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        assert sm.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

        sm.pause()
        assert sm.current_state == RLGMState.PAUSED
        assert sm.saved_state == RLGMState.WAITING_FOR_ASSIGNMENT

    def test_resume_restores_saved_state(self):
        """Test that resume restores the saved state."""
        sm = RLGMStateMachine()
        sm.transition(RLGMEvent.SEASON_START)
        sm.transition(RLGMEvent.REGISTRATION_ACCEPTED)

        sm.pause()
        assert sm.current_state == RLGMState.PAUSED

        sm.resume()
        assert sm.current_state == RLGMState.WAITING_FOR_ASSIGNMENT
        assert sm.saved_state is None

    def test_reset_returns_to_init(self):
        """Test that reset returns to INIT_START_STATE."""
        sm = RLGMStateMachine()
        sm.transition(RLGMEvent.SEASON_START)
        sm.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        sm.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        assert sm.current_state == RLGMState.RUNNING

        sm.reset()
        assert sm.current_state == RLGMState.INIT_START_STATE
        assert sm.saved_state is None

    def test_reset_clears_saved_state(self):
        """Test that reset also clears any saved state from pause."""
        sm = RLGMStateMachine()
        sm.transition(RLGMEvent.SEASON_START)
        sm.pause()
        assert sm.saved_state == RLGMState.WAITING_FOR_CONFIRMATION

        sm.reset()
        assert sm.current_state == RLGMState.INIT_START_STATE
        assert sm.saved_state is None

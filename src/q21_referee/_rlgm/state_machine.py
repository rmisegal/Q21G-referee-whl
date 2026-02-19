# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.state_machine — RLGM State Machine
====================================================

Implements the state machine that tracks the referee's lifecycle
within a season. Handles transitions between states based on events
from the League Manager.
"""

from typing import Optional
from .enums import RLGMState, RLGMEvent


# Valid state transitions: {current_state: {event: next_state}}
TRANSITIONS = {
    RLGMState.INIT_START_STATE: {
        RLGMEvent.SEASON_START: RLGMState.WAITING_FOR_CONFIRMATION,
    },
    RLGMState.WAITING_FOR_CONFIRMATION: {
        RLGMEvent.REGISTRATION_ACCEPTED: RLGMState.WAITING_FOR_ASSIGNMENT,
        RLGMEvent.REGISTRATION_REJECTED: RLGMState.INIT_START_STATE,
    },
    RLGMState.WAITING_FOR_ASSIGNMENT: {
        RLGMEvent.ASSIGNMENT_RECEIVED: RLGMState.RUNNING,
    },
    RLGMState.RUNNING: {
        RLGMEvent.ROUND_START: RLGMState.IN_GAME,
        RLGMEvent.SEASON_END: RLGMState.COMPLETED,
    },
    RLGMState.IN_GAME: {
        RLGMEvent.GAME_COMPLETE: RLGMState.RUNNING,
        RLGMEvent.GAME_ABORTED: RLGMState.RUNNING,
    },
    RLGMState.PAUSED: {},
    RLGMState.COMPLETED: {},
}


class RLGMStateMachine:
    """
    State machine for RLGM lifecycle management.

    Tracks the current state and validates/executes transitions
    based on events received from the League Manager.

    Attributes:
        current_state: The current state of the state machine
        saved_state: State saved when paused (for resume)
    """

    def __init__(self):
        """Initialize state machine in INIT_START_STATE."""
        self.current_state = RLGMState.INIT_START_STATE
        self.saved_state: Optional[RLGMState] = None

    def can_transition(self, event: RLGMEvent) -> bool:
        """
        Check if a transition is valid from current state.

        Args:
            event: The event to check

        Returns:
            True if the transition is valid, False otherwise
        """
        valid_transitions = TRANSITIONS.get(self.current_state, {})
        return event in valid_transitions

    def transition(self, event: RLGMEvent, force: bool = False) -> RLGMState:
        """
        Execute a state transition.

        Args:
            event: The event triggering the transition
            force: If True, allow transition even if not valid (for out-of-order messages)

        Returns:
            The new state after transition

        Raises:
            ValueError: If the transition is not valid and force=False
        """
        if not self.can_transition(event):
            if force:
                # Log warning but allow transition for out-of-order messages
                import logging
                logger = logging.getLogger("q21_referee.rlgm.state_machine")
                logger.warning(
                    f"Forced transition: {event.value} from {self.current_state.value}"
                )
                # Try to find any state that accepts this event
                for state, transitions in TRANSITIONS.items():
                    if event in transitions:
                        self.current_state = transitions[event]
                        return self.current_state
                return self.current_state
            raise ValueError(
                f"Invalid transition: {event.value} from {self.current_state.value}"
            )

        next_state = TRANSITIONS[self.current_state][event]
        self.current_state = next_state
        return next_state

    def pause(self) -> None:
        """
        Pause the state machine, saving current state.

        Can be called from any state except PAUSED.
        """
        if self.current_state != RLGMState.PAUSED:
            self.saved_state = self.current_state
            self.current_state = RLGMState.PAUSED

    def resume(self) -> None:
        """
        Resume from paused state, restoring saved state.

        Only valid when in PAUSED state with a saved state.
        """
        if self.current_state == RLGMState.PAUSED and self.saved_state:
            self.current_state = self.saved_state
            self.saved_state = None

    def reset(self) -> None:
        """Reset state machine to initial state."""
        self.current_state = RLGMState.INIT_START_STATE
        self.saved_state = None

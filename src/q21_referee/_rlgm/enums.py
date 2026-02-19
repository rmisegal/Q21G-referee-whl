# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.enums — RLGM State Machine Enums
==================================================

Defines the states and events for the Referee League Game Manager
state machine.
"""

from enum import Enum


class RLGMState(Enum):
    """
    States of the RLGM state machine.

    State transitions:
    INIT_START_STATE -> WAITING_FOR_CONFIRMATION (on SEASON_START)
    WAITING_FOR_CONFIRMATION -> WAITING_FOR_ASSIGNMENT (on REGISTRATION_ACCEPTED)
    WAITING_FOR_CONFIRMATION -> INIT_START_STATE (on REGISTRATION_REJECTED)
    WAITING_FOR_ASSIGNMENT -> RUNNING (on ASSIGNMENT_RECEIVED)
    RUNNING -> IN_GAME (on ROUND_START)
    IN_GAME -> RUNNING (on GAME_COMPLETE or GAME_ABORTED)
    RUNNING -> COMPLETED (on SEASON_END)
    Any state -> PAUSED (on PAUSE)
    PAUSED -> previous state (on CONTINUE)
    Any state -> INIT_START_STATE (on RESET)
    """
    INIT_START_STATE = "INIT_START_STATE"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    WAITING_FOR_ASSIGNMENT = "WAITING_FOR_ASSIGNMENT"
    RUNNING = "RUNNING"
    IN_GAME = "IN_GAME"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class RLGMEvent(Enum):
    """
    Events that trigger state transitions in the RLGM state machine.

    Events are triggered by:
    - SEASON_START: BROADCAST_START_SEASON received
    - REGISTRATION_ACCEPTED: SEASON_REGISTRATION_RESPONSE with status=accepted
    - REGISTRATION_REJECTED: SEASON_REGISTRATION_RESPONSE with status=rejected
    - ASSIGNMENT_RECEIVED: BROADCAST_ASSIGNMENT_TABLE received
    - ROUND_START: BROADCAST_NEW_LEAGUE_ROUND received
    - GAME_COMPLETE: GMC returns GameResult
    - SEASON_END: BROADCAST_END_SEASON received
    - PAUSE: BROADCAST_CRITICAL_PAUSE received
    - CONTINUE: Implicit resume after pause
    - RESET: BROADCAST_CRITICAL_RESET received
    """
    SEASON_START = "SEASON_START"
    REGISTRATION_ACCEPTED = "REGISTRATION_ACCEPTED"
    REGISTRATION_REJECTED = "REGISTRATION_REJECTED"
    ASSIGNMENT_RECEIVED = "ASSIGNMENT_RECEIVED"
    ROUND_START = "ROUND_START"
    GAME_COMPLETE = "GAME_COMPLETE"
    GAME_ABORTED = "GAME_ABORTED"
    SEASON_END = "SEASON_END"
    PAUSE = "PAUSE"
    CONTINUE = "CONTINUE"
    RESET = "RESET"

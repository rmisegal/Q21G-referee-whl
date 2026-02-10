# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
RLGM (Referee League Game Manager) - Orchestration layer for League Manager communication.

This package handles:
- Season lifecycle management
- Registration with League Manager
- Assignment handling
- Round management
- Game orchestration via GMC
"""

from .enums import RLGMState, RLGMEvent
from .gprm import GPRM
from .game_result import GameResult, PlayerScore
from .state_machine import RLGMStateMachine
from .broadcast_router import BroadcastRouter
from .handler_base import BaseBroadcastHandler

__all__ = [
    "RLGMState",
    "RLGMEvent",
    "GPRM",
    "GameResult",
    "PlayerScore",
    "RLGMStateMachine",
    "BroadcastRouter",
    "BaseBroadcastHandler",
]

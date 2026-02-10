# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_end_season — End Season Handler
=========================================================

Handles BROADCAST_END_SEASON messages from the League Manager.
Transitions to COMPLETED state and logs season completion.
"""

import logging
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine
from .enums import RLGMEvent

logger = logging.getLogger("q21_referee.rlgm.handler.end_season")


class BroadcastEndSeasonHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_END_SEASON messages.

    When the League Manager broadcasts season end:
    1. Log season completion
    2. Transition to COMPLETED state
    """

    def __init__(self, state_machine: RLGMStateMachine):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
        """
        self.state_machine = state_machine
        self.completed_season_id: Optional[str] = None

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_END_SEASON message.

        Args:
            message: The broadcast message

        Returns:
            None (no response needed)
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_END_SEASON", broadcast_id)

        season_id = payload.get("season_id", "")
        self.completed_season_id = season_id

        logger.info(f"Season {season_id} completed")

        # Transition to COMPLETED state
        self.state_machine.transition(RLGMEvent.SEASON_END)

        # No response needed
        return None

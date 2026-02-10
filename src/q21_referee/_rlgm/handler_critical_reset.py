# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_critical_reset — Critical Reset Handler
==================================================================

Handles BROADCAST_CRITICAL_RESET messages from the League Manager.
Resets the state machine to initial state and aborts any active game.
"""

import logging
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine

logger = logging.getLogger("q21_referee.rlgm.handler.critical_reset")


class BroadcastCriticalResetHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_CRITICAL_RESET messages.

    When the League Manager sends critical reset:
    1. Reset the state machine to INIT_START_STATE
    2. Store the reset reason
    3. Abort any active game
    """

    def __init__(self, state_machine: RLGMStateMachine):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
        """
        self.state_machine = state_machine
        self.reset_reason: Optional[str] = None

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_CRITICAL_RESET message.

        Args:
            message: The broadcast message

        Returns:
            None (no response needed)
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_CRITICAL_RESET", broadcast_id)

        reason = payload.get("reason", "Unknown reason")
        self.reset_reason = reason

        logger.warning(f"Critical reset received: {reason}")

        # Reset the state machine
        self.state_machine.reset()

        # No response needed
        return None

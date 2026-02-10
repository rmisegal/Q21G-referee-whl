# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_critical_pause — Critical Pause Handler
==================================================================

Handles BROADCAST_CRITICAL_PAUSE messages from the League Manager.
Pauses the state machine and any active game.
"""

import logging
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine

logger = logging.getLogger("q21_referee.rlgm.handler.critical_pause")


class BroadcastCriticalPauseHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_CRITICAL_PAUSE messages.

    When the League Manager sends critical pause:
    1. Pause the state machine (saves current state)
    2. Store the pause reason
    3. Signal any active game to pause
    """

    def __init__(self, state_machine: RLGMStateMachine):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
        """
        self.state_machine = state_machine
        self.pause_reason: Optional[str] = None

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_CRITICAL_PAUSE message.

        Args:
            message: The broadcast message

        Returns:
            None (no response needed)
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_CRITICAL_PAUSE", broadcast_id)

        reason = payload.get("reason", "Unknown reason")
        self.pause_reason = reason

        logger.warning(f"Critical pause received: {reason}")

        # Pause the state machine
        self.state_machine.pause()

        # No response needed
        return None

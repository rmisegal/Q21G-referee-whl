# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_registration_response — Registration Response Handler
================================================================================

Handles SEASON_REGISTRATION_RESPONSE messages from the League Manager.
Transitions state based on acceptance or rejection.
"""

import logging
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine
from .enums import RLGMEvent

logger = logging.getLogger("q21_referee.rlgm.handler.registration")


class SeasonRegistrationResponseHandler(BaseBroadcastHandler):
    """
    Handler for SEASON_REGISTRATION_RESPONSE messages.

    When the League Manager responds to registration:
    - If accepted: transition to WAITING_FOR_ASSIGNMENT
    - If rejected: transition back to INIT_START_STATE
    """

    def __init__(self, state_machine: RLGMStateMachine):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
        """
        self.state_machine = state_machine

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle SEASON_REGISTRATION_RESPONSE message.

        Args:
            message: The response message

        Returns:
            None (no response needed)
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("SEASON_REGISTRATION_RESPONSE", broadcast_id)

        status = payload.get("status", "").lower()

        if status == "accepted":
            logger.info("Registration accepted - waiting for assignments")
            self.state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED, force=True)

        elif status == "rejected":
            reason = payload.get("reason", "Unknown reason")
            logger.warning(f"Registration rejected: {reason}")
            self.state_machine.transition(RLGMEvent.REGISTRATION_REJECTED, force=True)

        else:
            logger.warning(f"Unknown registration status: {status}")

        # No response needed
        return None

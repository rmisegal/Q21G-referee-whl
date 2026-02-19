# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_end_round — End Round Handler
=======================================================

Handles BROADCAST_END_LEAGUE_ROUND messages from the League Manager.
Logs round completion for tracking purposes.
"""

import logging
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine

logger = logging.getLogger("q21_referee.rlgm.handler.end_round")


class BroadcastEndRoundHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_END_LEAGUE_ROUND messages.

    When the League Manager broadcasts round end:
    1. Log round completion
    2. Store round info for reference

    Note: State transition from IN_GAME to RUNNING happens
    when GMC signals game complete, not from this broadcast.
    """

    def __init__(self, state_machine: RLGMStateMachine):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
        """
        self.state_machine = state_machine
        self.last_completed_round: Optional[int] = None
        self.last_completed_round_id: Optional[str] = None
        self.current_round_number: Optional[int] = None

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_END_LEAGUE_ROUND message.

        Args:
            message: The broadcast message

        Returns:
            None (no response needed)
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_END_LEAGUE_ROUND", broadcast_id)

        round_number = payload.get("round_number", 0)
        round_id = payload.get("round_id", "")

        self.last_completed_round = round_number
        self.last_completed_round_id = round_id

        logger.info(f"Round {round_number} ({round_id}) completed")

        # Signal abort if this round matches the active round
        if (self.current_round_number is not None
                and round_number == self.current_round_number):
            return {
                "abort_signal": True,
                "round_number": round_number,
                "round_id": round_id,
            }

        # No response needed
        return None

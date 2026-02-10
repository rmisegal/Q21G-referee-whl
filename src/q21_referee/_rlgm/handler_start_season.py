# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_start_season — Start Season Handler
=============================================================

Handles BROADCAST_START_SEASON messages from the League Manager.
Triggers state transition and sends registration request.
"""

import logging
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine
from .enums import RLGMEvent

logger = logging.getLogger("q21_referee.rlgm.handler.start_season")


class BroadcastStartSeasonHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_START_SEASON messages.

    When the League Manager broadcasts season start:
    1. Extract season_id and league_id from payload
    2. Transition state machine to WAITING_FOR_CONFIRMATION
    3. Return SEASON_REGISTRATION_REQUEST to register with LM
    """

    def __init__(self, state_machine: RLGMStateMachine, config: Dict[str, Any]):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
            config: Configuration containing referee_id, group_id, etc.
        """
        self.state_machine = state_machine
        self.config = config

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_START_SEASON message.

        Args:
            message: The broadcast message

        Returns:
            SEASON_REGISTRATION_REQUEST message
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_START_SEASON", broadcast_id)

        # Extract season info
        season_id = payload.get("season_id", "")
        league_id = payload.get("league_id", "")

        logger.info(f"Season starting: {season_id} in league {league_id}")

        # Transition state machine
        self.state_machine.transition(RLGMEvent.SEASON_START)

        # Build registration request
        return self._build_registration_request(season_id, league_id)

    def _build_registration_request(
        self, season_id: str, league_id: str
    ) -> Dict[str, Any]:
        """
        Build SEASON_REGISTRATION_REQUEST message per UNIFIED_PROTOCOL.md §5.4.

        Args:
            season_id: The season to register for
            league_id: The league ID (used for envelope, not payload)

        Returns:
            Registration request message
        """
        return {
            "message_type": "SEASON_REGISTRATION_REQUEST",
            "payload": {
                "season_id": season_id,
                "user_id": self.config.get("group_id", ""),
                "participant_id": self.config.get("referee_id", ""),
                "display_name": self.config.get("display_name", "Q21 Referee"),
            },
        }

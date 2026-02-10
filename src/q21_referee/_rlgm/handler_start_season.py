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
from .._shared.protocol import build_envelope, generate_tx_id

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
        self.state_machine = state_machine
        self.config = config
        self._last_broadcast_id: Optional[str] = None

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle BROADCAST_START_SEASON message."""
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_START_SEASON", broadcast_id)
        self._last_broadcast_id = broadcast_id

        # Extract season info
        season_id = payload.get("season_id", "")
        league_id = message.get("league_id", "")

        logger.info(f"Season starting: {season_id} in league {league_id}")

        # Transition state machine (force=True for out-of-order tolerance)
        self.state_machine.transition(RLGMEvent.SEASON_START, force=True)

        # Build registration request per UNIFIED_PROTOCOL.md §5.4
        return self._build_registration_request(season_id, league_id, broadcast_id)

    def _build_registration_request(
        self, season_id: str, league_id: str, correlation_id: str
    ) -> Dict[str, Any]:
        """Build SEASON_REGISTRATION_REQUEST envelope per protocol."""
        referee_email = self.config.get("referee_email", "")
        tx_id = generate_tx_id("sreg")

        return build_envelope(
            message_type="SEASON_REGISTRATION_REQUEST",
            payload={
                "season_id": season_id,
                "user_id": self.config.get("group_id", ""),
                "participant_id": self.config.get("referee_id", ""),
                "display_name": self.config.get("display_name", "Q21 Referee"),
            },
            sender_email=referee_email,
            sender_role="REFEREE",
            sender_logical_id=self.config.get("referee_id"),
            recipient_id="LEAGUEMANAGER",
            correlation_id=correlation_id,
            league_id=league_id,
            message_id=tx_id,
        )

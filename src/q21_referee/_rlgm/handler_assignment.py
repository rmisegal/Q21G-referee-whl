# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_assignment — Assignment Table Handler
===============================================================

Handles BROADCAST_ASSIGNMENT_TABLE messages from the League Manager.
Filters assignments by group_id and stores them for round execution.
"""

import logging
from typing import Any, Dict, List, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine
from .enums import RLGMEvent
from .._shared.protocol import build_envelope, generate_tx_id

logger = logging.getLogger("q21_referee.rlgm.handler.assignment")


class BroadcastAssignmentTableHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_ASSIGNMENT_TABLE messages.

    When the League Manager broadcasts assignments:
    1. Extract assignments from payload
    2. Filter to only our group_id
    3. Store assignments for later round execution
    4. Transition to RUNNING state
    5. Return acknowledgment
    """

    def __init__(self, state_machine: RLGMStateMachine, config: Dict[str, Any]):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
            config: Configuration containing group_id
        """
        self.state_machine = state_machine
        self.config = config
        self.assignments: List[Dict[str, Any]] = []

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_ASSIGNMENT_TABLE message.

        Args:
            message: The broadcast message

        Returns:
            RESPONSE_GROUP_ASSIGNMENT acknowledgment
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_ASSIGNMENT_TABLE", broadcast_id)

        # Extract assignments - find games where we are the referee
        all_assignments = payload.get("assignments", [])
        my_email = self.config.get("referee_email", "")

        # Find game_ids where we are assigned as referee
        my_game_ids = set()
        for a in all_assignments:
            if a.get("role") == "referee" and a.get("email") == my_email:
                my_game_ids.add(a.get("game_id"))

        # Build complete game assignments with all participants
        self.assignments = self._build_game_assignments(all_assignments, my_game_ids)

        logger.info(
            f"Received {len(all_assignments)} total assignments, "
            f"{len(self.assignments)} games for referee {my_email}"
        )

        # Only transition if we have assignments
        # Use force=True to handle out-of-order messages
        if self.assignments:
            self.state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED, force=True)

        return self._build_acknowledgment(
            season_id=payload.get("season_id", ""),
            league_id=message.get("league_id", ""),
            correlation_id=broadcast_id,
        )

    def _build_acknowledgment(
        self, season_id: str, league_id: str, correlation_id: str
    ) -> Dict[str, Any]:
        """Build RESPONSE_GROUP_ASSIGNMENT envelope per protocol."""
        referee_email = self.config.get("referee_email", "")
        tx_id = generate_tx_id("assign-ack")

        return build_envelope(
            message_type="RESPONSE_GROUP_ASSIGNMENT",
            payload={
                "status": "acknowledged",
                "referee_id": self.config.get("referee_id", ""),
                "group_id": self.config.get("group_id", ""),
                "season_id": season_id,
                "assignments_received": len(self.assignments),
            },
            sender_email=referee_email,
            sender_role="REFEREE",
            sender_logical_id=self.config.get("referee_id"),
            recipient_id="LEAGUEMANAGER",
            correlation_id=correlation_id,
            league_id=league_id,
            season_id=season_id,
            message_id=tx_id,
        )

    def _build_game_assignments(
        self, all_assignments: List[Dict], my_game_ids: set
    ) -> List[Dict[str, Any]]:
        """Build complete game assignments with all participants."""
        games = {}
        for a in all_assignments:
            game_id = a.get("game_id")
            if game_id not in my_game_ids:
                continue
            if game_id not in games:
                # Parse round from game_id (format SSRRGGG)
                try:
                    round_num = int(game_id[2:4]) if game_id and len(game_id) >= 4 else 0
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse round_number from game_id: {game_id}")
                    round_num = 0
                games[game_id] = {"game_id": game_id, "round_number": round_num}
            role = a.get("role")
            if role == "player1":
                games[game_id]["player1_email"] = a.get("email")
                games[game_id]["player1_id"] = a.get("group_id")
            elif role == "player2":
                games[game_id]["player2_email"] = a.get("email")
                games[game_id]["player2_id"] = a.get("group_id")
        return list(games.values())

    def get_assignment_for_round(self, round_number: int) -> Optional[Dict[str, Any]]:
        """Get assignment for a specific round (parsed from game_id)."""
        for assignment in self.assignments:
            if assignment.get("round_number") == round_number:
                return assignment
        return None

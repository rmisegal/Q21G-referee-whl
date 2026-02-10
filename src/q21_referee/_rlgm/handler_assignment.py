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

        # Extract and filter assignments
        all_assignments = payload.get("assignments", [])
        my_group_id = self.config.get("group_id", "")

        self.assignments = [
            a for a in all_assignments if a.get("group_id") == my_group_id
        ]

        logger.info(
            f"Received {len(all_assignments)} total assignments, "
            f"{len(self.assignments)} for group {my_group_id}"
        )

        # Only transition if we have assignments
        # Use force=True to handle out-of-order messages
        if self.assignments:
            self.state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED, force=True)

        return self._build_acknowledgment(payload.get("season_id", ""))

    def _build_acknowledgment(self, season_id: str) -> Dict[str, Any]:
        """Build RESPONSE_GROUP_ASSIGNMENT message."""
        return {
            "message_type": "RESPONSE_GROUP_ASSIGNMENT",
            "payload": {
                "status": "acknowledged",
                "referee_id": self.config.get("referee_id", ""),
                "group_id": self.config.get("group_id", ""),
                "season_id": season_id,
                "assignments_received": len(self.assignments),
            },
        }

    def get_assignment_for_round(self, round_number: int) -> Optional[Dict[str, Any]]:
        """
        Get assignment for a specific round.

        Args:
            round_number: The round number to look up

        Returns:
            Assignment dict if found, None otherwise
        """
        for assignment in self.assignments:
            if assignment.get("round_number") == round_number:
                return assignment
        return None

# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_round_results — Round Results Handler
================================================================

Handles BROADCAST_ROUND_RESULTS messages from the League Manager.
Logs round results and stores them for reference.
"""

import logging
from typing import Any, Dict, List, Optional

from .handler_base import BaseBroadcastHandler

logger = logging.getLogger("q21_referee.rlgm.handler.round_results")


class BroadcastRoundResultsHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_ROUND_RESULTS messages.

    When the League Manager broadcasts round results:
    1. Log the results
    2. Store for reference
    """

    def __init__(self):
        """Initialize handler."""
        self.last_round_number: Optional[int] = None
        self.last_round_id: Optional[str] = None
        self.last_results: List[Dict[str, Any]] = []
        self.last_standings: List[Dict[str, Any]] = []

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_ROUND_RESULTS message.

        Args:
            message: The broadcast message

        Returns:
            None (no response needed)
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_ROUND_RESULTS", broadcast_id)

        # Extract round info
        self.last_round_number = payload.get("round_number")
        self.last_round_id = payload.get("round_id", "")
        self.last_results = payload.get("results", [])
        self.last_standings = payload.get("standings", [])

        # Log results
        logger.info(
            f"Round {self.last_round_number} results: "
            f"{len(self.last_results)} matches, "
            f"{len(self.last_standings)} players in standings"
        )

        for result in self.last_results:
            match_id = result.get("match_id", "")
            winner = result.get("winner_id", "DRAW")
            logger.info(f"  Match {match_id}: winner = {winner}")

        # No response needed
        return None

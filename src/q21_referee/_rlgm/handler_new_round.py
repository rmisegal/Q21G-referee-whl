# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_new_round — New Round Handler
=======================================================

Handles BROADCAST_NEW_LEAGUE_ROUND messages from the League Manager.
Looks up assignment for the round and builds GPRM for game execution.
"""

import logging
from typing import Any, Dict, List, Optional

from .handler_base import BaseBroadcastHandler
from .state_machine import RLGMStateMachine
from .enums import RLGMEvent
from .gprm import GPRM

logger = logging.getLogger("q21_referee.rlgm.handler.new_round")


class BroadcastNewRoundHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_NEW_LEAGUE_ROUND messages.

    When the League Manager broadcasts a new round:
    1. Extract round_number and round_id
    2. Look up assignment for this round
    3. Build GPRM from assignment
    4. Transition to IN_GAME state
    5. Return GPRM for game execution
    """

    def __init__(
        self,
        state_machine: RLGMStateMachine,
        config: Dict[str, Any],
        assignments: List[Dict[str, Any]],
    ):
        """
        Initialize handler.

        Args:
            state_machine: The RLGM state machine
            config: Configuration containing season_id, game_id
            assignments: List of assignments for this referee
        """
        self.state_machine = state_machine
        self.config = config
        self.assignments = assignments

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_NEW_LEAGUE_ROUND message.

        Args:
            message: The broadcast message

        Returns:
            Dict with round info, assignment, and GPRM, or None if no assignment
        """
        broadcast_id = self.extract_broadcast_id(message)
        payload = self.extract_payload(message)

        self.log_handling("BROADCAST_NEW_LEAGUE_ROUND", broadcast_id)

        round_number = payload.get("round_number", 0)
        round_id = payload.get("round_id", "")

        logger.info(f"New round starting: {round_id} (round {round_number})")

        # Find assignment for this round
        assignment = self._get_assignment_for_round(round_number)
        if not assignment:
            logger.warning(f"No assignment found for round {round_number}")
            return None

        # Build GPRM
        gprm = self._build_gprm(assignment, round_number, round_id)

        # Transition to IN_GAME (force=True for out-of-order tolerance)
        self.state_machine.transition(RLGMEvent.ROUND_START, force=True)

        return {
            "round_number": round_number,
            "round_id": round_id,
            "assignment": assignment,
            "gprm": gprm,
        }

    def _get_assignment_for_round(self, round_number: int) -> Optional[Dict[str, Any]]:
        """Find assignment for the given round number."""
        for assignment in self.assignments:
            if assignment.get("round_number") == round_number:
                return assignment
        return None

    def _build_gprm(
        self, assignment: Dict[str, Any], round_number: int, round_id: str
    ) -> GPRM:
        """Build GPRM from assignment and config."""
        game_id = assignment.get("game_id", "")
        return GPRM(
            player1_email=assignment.get("player1_email", ""),
            player1_id=assignment.get("player1_id", ""),
            player2_email=assignment.get("player2_email", ""),
            player2_id=assignment.get("player2_id", ""),
            season_id=self.config.get("season_id", ""),
            game_id=game_id,
            match_id=game_id,  # Use game_id as match_id
            round_id=round_id,
            round_number=round_number,
        )

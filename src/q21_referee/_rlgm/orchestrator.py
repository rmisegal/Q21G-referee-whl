# Area: RLGM
# PRD: docs/prd-rlgm.md
"""Orchestrator — coordinates handlers, state machine, and GMC."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .state_machine import RLGMStateMachine
from .broadcast_router import BroadcastRouter
from .response_builder import RLGMResponseBuilder
from .handler_start_season import BroadcastStartSeasonHandler
from .handler_registration_response import SeasonRegistrationResponseHandler
from .handler_assignment import BroadcastAssignmentTableHandler
from .handler_new_round import BroadcastNewRoundHandler
from .handler_end_round import BroadcastEndRoundHandler
from .handler_end_season import BroadcastEndSeasonHandler
from .gprm import GPRM
from .enums import RLGMEvent
from .warmup_initiator import initiate_warmup
from .._gmc.gmc import GameManagementCycle
from ..callbacks import RefereeAI

logger = logging.getLogger("q21_referee.rlgm.orchestrator")


class RLGMOrchestrator:
    """Main orchestrator for RLGM season lifecycle."""

    def __init__(self, config: Dict[str, Any], ai: RefereeAI):
        self.config = config
        self.ai = ai
        self.state_machine = RLGMStateMachine()
        self.response_builder = RLGMResponseBuilder(config)
        self.router = BroadcastRouter()
        self.current_game: Optional[GameManagementCycle] = None
        self.current_round_number: Optional[int] = None
        self._assignments: List[Dict[str, Any]] = []
        self._pending_outgoing: List[Tuple[dict, str, str]] = []
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all broadcast handlers with the router."""
        reg = self.router.register_handler
        reg("BROADCAST_START_SEASON",
            BroadcastStartSeasonHandler(self.state_machine, self.config))
        reg("SEASON_REGISTRATION_RESPONSE",
            SeasonRegistrationResponseHandler(self.state_machine))
        self._assignment_handler = BroadcastAssignmentTableHandler(
            self.state_machine, self.config)
        reg("BROADCAST_ASSIGNMENT_TABLE", self._assignment_handler)
        self._new_round_handler = BroadcastNewRoundHandler(
            self.state_machine, self.config, self._assignments)
        reg("BROADCAST_NEW_LEAGUE_ROUND", self._new_round_handler)
        reg("BROADCAST_END_LEAGUE_ROUND",
            BroadcastEndRoundHandler(self.state_machine))
        reg("BROADCAST_END_SEASON",
            BroadcastEndSeasonHandler(self.state_machine))

    def handle_lm_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a message from the League Manager."""
        message_type = message.get("message_type", "")
        logger.info(f"Handling LM message: {message_type}")
        result = self.router.route(message)

        if message_type == "BROADCAST_ASSIGNMENT_TABLE":
            self._assignments = self._assignment_handler.assignments
            self._new_round_handler.assignments = self._assignments

        if message_type == "BROADCAST_NEW_LEAGUE_ROUND" and result:
            gprm = result.get("gprm")
            if gprm:
                warmup_msgs = self.start_round(gprm)
                self._pending_outgoing.extend(warmup_msgs)
            return None

        return result

    def get_pending_outgoing(self) -> List[Tuple[dict, str, str]]:
        """Get and clear pending outgoing player messages."""
        msgs = self._pending_outgoing
        self._pending_outgoing = []
        return msgs

    def start_game(self, gprm: GPRM) -> None:
        """Start a new game with the given parameters."""
        logger.info(f"Starting game: {gprm.match_id}")
        self.current_game = GameManagementCycle(
            gprm=gprm, ai=self.ai, config=self.config)

    def start_round(self, gprm: GPRM) -> List[Tuple[dict, str, str]]:
        """Start a new round: create GMC and send warmup calls.

        Idempotent — returns [] if the same round_number is already active.
        Logs a warning if overwriting an existing game (abort TBD Task 8).
        """
        if self.current_round_number == gprm.round_number:
            logger.info(f"Round {gprm.round_number} already active, skipping")
            return []

        if self.current_game is not None:
            logger.warning(
                f"Overwriting round {self.current_round_number} game "
                f"to start round {gprm.round_number}")

        self.current_round_number = gprm.round_number
        self.current_game = GameManagementCycle(
            gprm=gprm, ai=self.ai, config=self.config)
        return initiate_warmup(self.current_game, gprm, self.ai, self.config)

    def route_player_message(
        self, message_type: str, body: dict, sender_email: str,
    ) -> List[Tuple[dict, str, str]]:
        """Route a player message to the current game."""
        if not self.current_game:
            logger.warning("No active game for player message")
            return []
        outgoing = self.current_game.route_message(message_type, body, sender_email)
        if self.current_game.is_complete():
            self._on_game_complete()
        return outgoing

    def _on_game_complete(self) -> None:
        """Handle game completion."""
        if not self.current_game:
            return
        result = self.current_game.get_result()
        if result:
            logger.info(f"Game complete: {result.match_id}, winner: {result.winner_id}")
            self.state_machine.transition(RLGMEvent.GAME_COMPLETE, force=True)
        self.current_game = None

    def get_assignments(self) -> List[Dict[str, Any]]:
        """Get current assignments."""
        return self._assignments

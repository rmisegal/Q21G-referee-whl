# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.orchestrator — RLGM Orchestrator
==================================================

Main orchestrator that coordinates handlers and GMC.
Manages the RLGM lifecycle and delegates to appropriate components.
"""

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
from .game_result import GameResult
from .enums import RLGMEvent
from .._gmc.gmc import GameManagementCycle
from ..callbacks import RefereeAI

logger = logging.getLogger("q21_referee.rlgm.orchestrator")


class RLGMOrchestrator:
    """
    Main orchestrator for RLGM.

    Coordinates between League Manager messages, handlers, and GMC.
    """

    def __init__(self, config: Dict[str, Any], ai: RefereeAI):
        """
        Initialize orchestrator.

        Args:
            config: Configuration dict
            ai: Student's RefereeAI implementation
        """
        self.config = config
        self.ai = ai

        # Core components
        self.state_machine = RLGMStateMachine()
        self.response_builder = RLGMResponseBuilder(config)
        self.router = BroadcastRouter()

        # Current game (if any)
        self.current_game: Optional[GameManagementCycle] = None

        # Assignments storage
        self._assignments: List[Dict[str, Any]] = []

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all broadcast handlers."""
        self.router.register_handler(
            "BROADCAST_START_SEASON",
            BroadcastStartSeasonHandler(self.state_machine, self.config),
        )
        self.router.register_handler(
            "SEASON_REGISTRATION_RESPONSE",
            SeasonRegistrationResponseHandler(self.state_machine),
        )
        # Assignment handler needs to be created with access to store assignments
        self._assignment_handler = BroadcastAssignmentTableHandler(
            self.state_machine, self.config
        )
        self.router.register_handler(
            "BROADCAST_ASSIGNMENT_TABLE", self._assignment_handler
        )
        self.router.register_handler(
            "BROADCAST_END_LEAGUE_ROUND",
            BroadcastEndRoundHandler(self.state_machine),
        )
        self.router.register_handler(
            "BROADCAST_END_SEASON",
            BroadcastEndSeasonHandler(self.state_machine),
        )

    def handle_lm_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle a message from the League Manager.

        Args:
            message: The LM message

        Returns:
            Response message to send, or None
        """
        message_type = message.get("message_type", "")
        logger.info(f"Handling LM message: {message_type}")

        result = self.router.route(message)

        # Update assignments if we received them
        if message_type == "BROADCAST_ASSIGNMENT_TABLE":
            self._assignments = self._assignment_handler.assignments

        return result

    def start_game(self, gprm: GPRM) -> None:
        """
        Start a new game with the given parameters.

        Args:
            gprm: Game parameters
        """
        logger.info(f"Starting game: {gprm.match_id}")
        self.current_game = GameManagementCycle(
            gprm=gprm, ai=self.ai, config=self.config
        )

    def route_player_message(
        self, message_type: str, body: dict, sender_email: str
    ) -> List[Tuple[dict, str, str]]:
        """
        Route a player message to the current game.

        Args:
            message_type: Type of message
            body: Message body
            sender_email: Sender's email

        Returns:
            List of outgoing messages
        """
        if not self.current_game:
            logger.warning("No active game for player message")
            return []

        outgoing = self.current_game.route_message(message_type, body, sender_email)

        # Check if game completed
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
            self.state_machine.transition(RLGMEvent.GAME_COMPLETE)

        self.current_game = None

    def get_assignments(self) -> List[Dict[str, Any]]:
        """Get current assignments."""
        return self._assignments

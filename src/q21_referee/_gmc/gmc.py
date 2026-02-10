# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.gmc — Game Management Cycle Wrapper
====================================================

High-level wrapper that accepts GPRM from RLGM and returns GameResult.
Encapsulates the internal router, state, and builder.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .state import GameState, GamePhase, PlayerState
from .envelope_builder import EnvelopeBuilder
from .router import MessageRouter
from ..callbacks import RefereeAI
from .._rlgm.gprm import GPRM
from .._rlgm.game_result import GameResult, PlayerScore

logger = logging.getLogger("q21_referee.gmc")


class GameManagementCycle:
    """
    High-level wrapper for a single game execution.

    Accepts GPRM from RLGM, manages game flow, and returns GameResult.
    """

    def __init__(self, gprm: GPRM, ai: RefereeAI, config: Dict[str, Any]):
        """
        Initialize GMC from GPRM.

        Args:
            gprm: Game parameters from RLGM
            ai: Student's RefereeAI implementation
            config: Additional configuration (referee_email, etc.)
        """
        self.gprm = gprm
        self.ai = ai
        self.config = config
        self._result: Optional[GameResult] = None

        # Build internal state from GPRM
        self.state = GameState(
            game_id=gprm.game_id,
            match_id=gprm.match_id,
            season_id=gprm.season_id,
            league_id=config.get("league_id", ""),
            player1=PlayerState(
                email=gprm.player1_email,
                participant_id=gprm.player1_id,
            ),
            player2=PlayerState(
                email=gprm.player2_email,
                participant_id=gprm.player2_id,
            ),
        )

        # Build envelope builder
        self.builder = EnvelopeBuilder(
            referee_email=config.get("referee_email", ""),
            referee_id=config.get("referee_id", ""),
            league_id=config.get("league_id", ""),
            season_id=gprm.season_id,
        )

        # Build router
        self.router = MessageRouter(
            ai=ai,
            state=self.state,
            builder=self.builder,
            config=config,
        )

    def initiate_game(self) -> List[Tuple[dict, str, str]]:
        """
        Initiate the game by sending warmup calls to both players.

        Called by RLGM orchestrator after creating the GMC.

        Returns:
            List of (envelope, subject, recipient) tuples for warmup calls
        """
        # Build a synthetic message body with round info from GPRM
        body = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "payload": {
                "round_id": self.gprm.round_id,
                "round_number": self.gprm.round_number,
            },
        }
        return self.router.route("BROADCAST_NEW_LEAGUE_ROUND", body, "")

    def route_message(
        self, message_type: str, body: dict, sender_email: str
    ) -> List[Tuple[dict, str, str]]:
        """
        Route an incoming message through the game flow.

        Args:
            message_type: Type of incoming message
            body: Message body
            sender_email: Sender's email

        Returns:
            List of (envelope, subject, recipient) tuples to send
        """
        outgoing = self.router.route(message_type, body, sender_email)

        # Check if game is complete
        if self.state.phase == GamePhase.MATCH_REPORTED:
            self._result = self._build_game_result()

        return outgoing

    def is_complete(self) -> bool:
        """Check if the game has completed."""
        return self._result is not None

    def get_result(self) -> Optional[GameResult]:
        """
        Get the game result.

        Returns:
            GameResult if game is complete, None otherwise
        """
        return self._result

    def _build_game_result(self) -> GameResult:
        """Build GameResult from current state."""
        p1 = self.state.player1
        p2 = self.state.player2

        # Determine winner
        if p1.league_points > p2.league_points:
            winner_id = p1.participant_id
            is_draw = False
        elif p2.league_points > p1.league_points:
            winner_id = p2.participant_id
            is_draw = False
        else:
            winner_id = None
            is_draw = True

        return GameResult(
            game_id=self.gprm.game_id,
            match_id=self.gprm.match_id,
            round_id=self.gprm.round_id,
            season_id=self.gprm.season_id,
            player1=PlayerScore(
                player_id=p1.participant_id,
                player_email=p1.email,
                score=p1.league_points,
                questions_answered=len(p1.questions) if p1.questions else 0,
                correct_answers=0,  # Would need tracking
            ),
            player2=PlayerScore(
                player_id=p2.participant_id,
                player_email=p2.email,
                score=p2.league_points,
                questions_answered=len(p2.questions) if p2.questions else 0,
                correct_answers=0,
            ),
            winner_id=winner_id,
            is_draw=is_draw,
        )

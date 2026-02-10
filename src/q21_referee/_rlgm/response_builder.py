# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.response_builder — RLGM Response Builder
==========================================================

Builds protocol-compliant response messages for the League Manager.
Ensures all responses have the correct structure and required fields.
"""

from typing import Any, Dict
from .game_result import GameResult


class RLGMResponseBuilder:
    """
    Builds response messages for League Manager communication.

    All responses follow the Q21 protocol format with message_type
    and payload fields.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize builder with config.

        Args:
            config: Configuration containing referee_id, group_id, etc.
        """
        self.config = config

    def build_registration_request(
        self, season_id: str, league_id: str
    ) -> Dict[str, Any]:
        """
        Build SEASON_REGISTRATION_REQUEST message per UNIFIED_PROTOCOL.md §5.4.

        Args:
            season_id: Season to register for
            league_id: League ID (used for envelope, not payload)

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

    def build_group_assignment_response(
        self, season_id: str, assignments_received: int
    ) -> Dict[str, Any]:
        """
        Build RESPONSE_GROUP_ASSIGNMENT message.

        Args:
            season_id: Season ID
            assignments_received: Number of assignments received

        Returns:
            Assignment acknowledgment message
        """
        return {
            "message_type": "RESPONSE_GROUP_ASSIGNMENT",
            "payload": {
                "status": "acknowledged",
                "season_id": season_id,
                "referee_id": self.config.get("referee_id", ""),
                "group_id": self.config.get("group_id", ""),
                "assignments_received": assignments_received,
            },
        }

    def build_match_result_report(self, game_result: GameResult) -> Dict[str, Any]:
        """
        Build MATCH_RESULT_REPORT message.

        Args:
            game_result: The completed game result

        Returns:
            Match result report message
        """
        return {
            "message_type": "MATCH_RESULT_REPORT",
            "payload": {
                "game_id": game_result.game_id,
                "match_id": game_result.match_id,
                "round_id": game_result.round_id,
                "season_id": game_result.season_id,
                "referee_id": self.config.get("referee_id", ""),
                "winner_id": game_result.winner_id,
                "is_draw": game_result.is_draw,
                "player1": self._build_player_score(game_result.player1),
                "player2": self._build_player_score(game_result.player2),
            },
        }

    def _build_player_score(self, player) -> Dict[str, Any]:
        """Build player score dict from PlayerScore."""
        return {
            "player_id": player.player_id,
            "player_email": player.player_email,
            "score": player.score,
            "questions_answered": player.questions_answered,
            "correct_answers": player.correct_answers,
        }

    def build_keep_alive_response(self) -> Dict[str, Any]:
        """
        Build RESPONSE_KEEP_ALIVE message.

        Returns:
            Keep-alive response message
        """
        return {
            "message_type": "RESPONSE_KEEP_ALIVE",
            "payload": {
                "referee_id": self.config.get("referee_id", ""),
                "status": "alive",
            },
        }

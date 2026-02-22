# Area: GMC
# PRD: docs/prd-rlgm.md
"""Build callback context dicts (dynamic + service sections)."""

from __future__ import annotations
from typing import Any, Dict, Optional
import logging

from .state import GameState, PlayerState
from .context_service import SERVICE_DEFINITIONS

logger = logging.getLogger("q21_referee.context")


class ContextBuilder:
    """Builds context dicts for student callbacks."""

    def __init__(self, config: Dict[str, Any], state: GameState):
        self.config = config
        self.state = state

    def _base_dynamic(self) -> Dict[str, Any]:
        """Build common dynamic fields present in all contexts."""
        return {
            "season_id": self.state.season_id,
            "league_id": self.state.league_id,
            "game_id": self.state.game_id,
            "match_id": self.state.match_id,
            "referee_id": self.config.get("referee_id"),
        }

    def _player_info(self, player: Optional[PlayerState]) -> dict:
        """Extract player id/email, returning None values if player is None."""
        if player is None:
            return {"id": None, "email": None}
        return {"id": player.participant_id, "email": player.email}

    def build_warmup_question_ctx(self, incoming_body: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for get_warmup_question callback."""
        payload = incoming_body.get("payload", {})
        p1 = self._player_info(self.state.player1)
        p2 = self._player_info(self.state.player2)

        dynamic = self._base_dynamic()
        dynamic.update({
            "round_number": payload.get("round_number"),
            "round_id": payload.get("round_id"),
            "assignment_table_id": payload.get("assignment_table_id"),
            "player_a_id": p1["id"],
            "player_a_email": p1["email"],
            "player_b_id": p2["id"],
            "player_b_email": p2["email"],
        })

        return {
            "dynamic": dynamic,
            "service": SERVICE_DEFINITIONS["warmup_question"].copy(),
        }

    def build_round_start_info_ctx(self) -> Dict[str, Any]:
        """Build context for get_round_start_info callback."""
        dynamic = self._base_dynamic()
        dynamic.update({
            "round_number": self.state.round_number,
            "round_id": self.state.round_id,
            "assignment_table_id": self.config.get("assignment_table_id"),
            "player_a": {
                "id": self.state.player1.participant_id if self.state.player1 else None,
                "email": self.state.player1.email if self.state.player1 else None,
                "warmup_answer": self.state.player1.warmup_answer if self.state.player1 else None,
            },
            "player_b": {
                "id": self.state.player2.participant_id if self.state.player2 else None,
                "email": self.state.player2.email if self.state.player2 else None,
                "warmup_answer": self.state.player2.warmup_answer if self.state.player2 else None,
            },
        })

        return {
            "dynamic": dynamic,
            "service": SERVICE_DEFINITIONS["round_start_info"].copy(),
        }

    def build_answers_ctx(self, player: PlayerState, questions: list) -> Dict[str, Any]:
        """Build context for get_answers callback."""
        dynamic = self._base_dynamic()
        dynamic.update({
            "round_number": self.state.round_number,
            "round_id": self.state.round_id,
            "assignment_table_id": self.config.get("assignment_table_id"),
            "player_id": player.participant_id,
            "player_email": player.email,
            "book_name": self.state.book_name,
            "book_hint": self.state.book_hint,
            "association_word": self.state.association_word,
            "questions": questions,
        })

        return {
            "dynamic": dynamic,
            "service": SERVICE_DEFINITIONS["answers"].copy(),
        }

    def build_score_feedback_ctx(
        self,
        player: PlayerState,
        guess: Dict[str, Any],
        actual_opening_sentence: Optional[str] = None,
        actual_associative_word: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build context for get_score_feedback callback."""
        dynamic = self._base_dynamic()
        dynamic.update({
            "round_number": self.state.round_number,
            "round_id": self.state.round_id,
            "assignment_table_id": self.config.get("assignment_table_id"),
            "player_id": player.participant_id,
            "player_email": player.email,
            "book_name": self.state.book_name,
            "book_hint": self.state.book_hint,
            "association_word": self.state.association_word,
            "actual_opening_sentence": actual_opening_sentence or self.config.get("actual_opening_sentence"),
            "actual_associative_word": actual_associative_word or self.config.get("actual_associative_word"),
            "player_guess": {
                "opening_sentence": guess.get("opening_sentence", ""),
                "sentence_justification": guess.get("sentence_justification", ""),
                "associative_word": guess.get("associative_word", ""),
                "word_justification": guess.get("word_justification", ""),
                "confidence": guess.get("confidence"),
            },
        })

        return {
            "dynamic": dynamic,
            "service": SERVICE_DEFINITIONS["score_feedback"].copy(),
        }

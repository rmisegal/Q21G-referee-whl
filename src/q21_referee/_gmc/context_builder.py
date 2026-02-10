# Area: GMC
# PRD: docs/prd-rlgm.md
# NOTE: This file is 257 lines - will be split in Part 22
"""
q21_referee._gmc.context_builder — Build callback context dicts
===============================================================

Constructs the ctx dicts passed to student callbacks.
Each ctx has two sections:
- dynamic: Data extracted from incoming messages
- service: Description of what LLM service to call
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import logging

from .state import GameState, PlayerState

logger = logging.getLogger("q21_referee.context")


# ══════════════════════════════════════════════════════════════
# SERVICE DEFINITIONS
# ══════════════════════════════════════════════════════════════

SERVICE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "warmup_question": {
        "name": "warmup_question",
        "description": "Generate a simple question to verify player connectivity",
        "required_output_fields": ["warmup_question"],
        "deadline_seconds": 30,
    },
    "round_start_info": {
        "name": "round_start_info",
        "description": "Select a book, write a hint, and choose an association word",
        "required_output_fields": ["book_name", "book_hint", "association_word"],
        "deadline_seconds": 60,
    },
    "answers": {
        "name": "answers",
        "description": "Answer each multiple-choice question with A, B, C, D, or 'Not Relevant'",
        "required_output_fields": ["answers"],
        "deadline_seconds": 120,
    },
    "score_feedback": {
        "name": "score_feedback",
        "description": "Score the player's guess and provide 150-200 word feedback for each component",
        "required_output_fields": ["league_points", "private_score", "breakdown", "feedback"],
        "deadline_seconds": 180,
    },
}


# ══════════════════════════════════════════════════════════════
# CONTEXT BUILDER CLASS
# ══════════════════════════════════════════════════════════════

class ContextBuilder:
    """
    Builds context dicts for student callbacks.

    Each context has:
    - dynamic: Data from incoming message / game state
    - service: LLM service request info
    """

    def __init__(self, config: Dict[str, Any], state: GameState):
        """
        Initialize the context builder.

        Parameters
        ----------
        config : dict
            The runner configuration dict.
        state : GameState
            The current game state.
        """
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

    # ── Callback 1: get_warmup_question ───────────────────────

    def build_warmup_question_ctx(self, incoming_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context for get_warmup_question callback.

        Called when BROADCAST_NEW_LEAGUE_ROUND is received.

        Parameters
        ----------
        incoming_body : dict
            The incoming message body.

        Returns
        -------
        dict
            Context with dynamic and service sections.
        """
        payload = incoming_body.get("payload", {})

        dynamic = self._base_dynamic()
        dynamic.update({
            "round_number": payload.get("round_number"),
            "round_id": payload.get("round_id"),
            "assignment_table_id": payload.get("assignment_table_id"),
            "player_a_id": self.state.player1.participant_id if self.state.player1 else None,
            "player_a_email": self.state.player1.email if self.state.player1 else None,
            "player_b_id": self.state.player2.participant_id if self.state.player2 else None,
            "player_b_email": self.state.player2.email if self.state.player2 else None,
        })

        return {
            "dynamic": dynamic,
            "service": SERVICE_DEFINITIONS["warmup_question"].copy(),
        }

    # ── Callback 2: get_round_start_info ──────────────────────

    def build_round_start_info_ctx(self) -> Dict[str, Any]:
        """
        Build context for get_round_start_info callback.

        Called when both players have responded to warmup.

        Returns
        -------
        dict
            Context with dynamic and service sections.
        """
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

    # ── Callback 3: get_answers ───────────────────────────────

    def build_answers_ctx(
        self,
        player: PlayerState,
        questions: list,
    ) -> Dict[str, Any]:
        """
        Build context for get_answers callback.

        Called when a player submits Q21QUESTIONSBATCH.

        Parameters
        ----------
        player : PlayerState
            The player who submitted questions.
        questions : list
            The list of questions from the player.

        Returns
        -------
        dict
            Context with dynamic and service sections.
        """
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

    # ── Callback 4: get_score_feedback ────────────────────────

    def build_score_feedback_ctx(
        self,
        player: PlayerState,
        guess: Dict[str, Any],
        actual_opening_sentence: Optional[str] = None,
        actual_associative_word: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build context for get_score_feedback callback.

        Called when a player submits Q21GUESSSUBMISSION.

        Parameters
        ----------
        player : PlayerState
            The player who submitted the guess.
        guess : dict
            The player's guess data.
        actual_opening_sentence : str, optional
            The actual opening sentence of the book.
        actual_associative_word : str, optional
            The actual associative word.

        Returns
        -------
        dict
            Context with dynamic and service sections.
        """
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

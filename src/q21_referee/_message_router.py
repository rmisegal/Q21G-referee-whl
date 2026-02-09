"""
q21_referee.message_router — Incoming → State → Callback → Outgoing
=====================================================================

The heart of the package. Routes each validated incoming message to
the correct handler, manages game state transitions, calls student
callbacks with clean context dicts, and returns outgoing messages.
"""

from __future__ import annotations
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple

from ._state import GameState, GamePhase, PlayerState
from .callbacks import RefereeAI
from ._envelope_builder import EnvelopeBuilder
from ._context_builder import ContextBuilder, SERVICE_DEFINITIONS
from ._callback_executor import execute_callback

logger = logging.getLogger("q21_referee.router")


class MessageRouter:
    """
    Stateful message router for one game.

    Given a validated incoming message:
    1. Updates GameState
    2. Checks if a callback should fire (e.g., both players responded)
    3. Calls the student's RefereeAI callback with a clean context dict
    4. Uses EnvelopeBuilder to construct outgoing messages
    5. Returns list of (envelope, subject, recipient_email) to send
    """

    def __init__(self, ai: RefereeAI, state: GameState,
                 builder: EnvelopeBuilder, config: dict):
        self.ai = ai
        self.state = state
        self.builder = builder
        self.config = config
        self.context_builder = ContextBuilder(config, state)

    def route(self, message_type: str, body: dict,
              sender_email: str) -> List[Tuple[dict, str, str]]:
        """
        Route an incoming message. Returns list of (envelope, subject, recipient_email)
        tuples to be sent.
        """
        outgoing = []

        if message_type == "BROADCAST_NEW_LEAGUE_ROUND":
            outgoing = self._handle_new_round(body)

        elif message_type == "Q21WARMUPRESPONSE":
            outgoing = self._handle_warmup_response(body, sender_email)

        elif message_type == "Q21QUESTIONSBATCH":
            outgoing = self._handle_questions(body, sender_email)

        elif message_type == "Q21GUESSSUBMISSION":
            outgoing = self._handle_guess(body, sender_email)

        else:
            logger.debug(f"No handler for message_type={message_type}")

        return outgoing

    # ── Handler 1: New Round → call get_warmup_question() → send Q21WARMUPCALL ──

    def _handle_new_round(self, body: dict) -> List[Tuple[dict, str, str]]:
        payload = body.get("payload", {})
        self.state.round_id = payload.get("round_id")
        self.state.round_number = payload.get("round_number")
        self.state.auth_token = f"tok_{uuid.uuid4().hex[:8]}"

        # Reset player state for new round
        self.state.reset_for_new_round()
        # Re-set round info after reset
        self.state.round_id = payload.get("round_id")
        self.state.round_number = payload.get("round_number")
        self.state.auth_token = f"tok_{uuid.uuid4().hex[:8]}"

        # Build context for student callback
        ctx = self.context_builder.build_warmup_question_ctx(body)

        # ── CALL STUDENT CALLBACK 1 ──
        service = SERVICE_DEFINITIONS["warmup_question"]
        result = execute_callback(
            callback_fn=self.ai.get_warmup_question,
            callback_name="warmup_question",
            ctx=ctx,
            deadline_seconds=service["deadline_seconds"],
        )
        warmup_q = result.get("warmup_question", "What is 2 + 2?")

        # Build and return warmup calls for both players
        outgoing = []
        for player in [self.state.player1, self.state.player2]:
            env, subject = self.builder.build_warmup_call(
                player_id=player.participant_id,
                game_id=self.state.game_id,
                match_id=self.state.match_id,
                warmup_question=warmup_q,
                auth_token=self.state.auth_token,
            )
            player.warmup_message_id = env["message_id"]
            outgoing.append((env, subject, player.email))

        self.state.advance_phase(GamePhase.WARMUP_SENT)
        return outgoing

    # ── Handler 2: Warmup Response → when both arrive, call get_round_start_info() ──

    def _handle_warmup_response(self, body: dict,
                                sender_email: str) -> List[Tuple[dict, str, str]]:
        payload = body.get("payload", {})
        player = self.state.get_player_by_email(sender_email)
        if not player:
            logger.warning(f"Warmup response from unknown player: {sender_email}")
            return []

        player.warmup_answer = payload.get("answer", "")
        logger.info(f"Warmup response from {player.participant_id}: '{player.warmup_answer}'")

        # Wait for BOTH players
        if not self.state.both_warmups_received():
            logger.info("Waiting for other player's warmup response...")
            return []

        self.state.advance_phase(GamePhase.WARMUP_COMPLETE)

        # Build context for student callback
        ctx = self.context_builder.build_round_start_info_ctx()

        # ── CALL STUDENT CALLBACK 2 ──
        service = SERVICE_DEFINITIONS["round_start_info"]
        result = execute_callback(
            callback_fn=self.ai.get_round_start_info,
            callback_name="round_start_info",
            ctx=ctx,
            deadline_seconds=service["deadline_seconds"],
        )

        self.state.book_name = result.get("book_name", "Unknown Book")
        self.state.book_hint = result.get("book_hint", "A famous book")
        self.state.association_word = result.get("association_word", "thing")

        # Send Q21ROUNDSTART to both players
        outgoing = []
        for player in [self.state.player1, self.state.player2]:
            env, subject = self.builder.build_round_start(
                player_id=player.participant_id,
                game_id=self.state.game_id,
                match_id=self.state.match_id,
                book_name=self.state.book_name,
                book_hint=self.state.book_hint,
                association_word=self.state.association_word,
                auth_token=self.state.auth_token,
            )
            player.questions_message_id = env["message_id"]
            outgoing.append((env, subject, player.email))

        self.state.advance_phase(GamePhase.ROUND_STARTED)
        return outgoing

    # ── Handler 3: Questions Batch → call get_answers() per player ──

    def _handle_questions(self, body: dict,
                          sender_email: str) -> List[Tuple[dict, str, str]]:
        payload = body.get("payload", {})
        player = self.state.get_player_by_email(sender_email)
        if not player:
            logger.warning(f"Questions from unknown player: {sender_email}")
            return []

        player.questions = payload.get("questions", [])
        correlation_id = body.get("message_id")

        # Build context for student callback
        ctx = self.context_builder.build_answers_ctx(player, player.questions)

        # ── CALL STUDENT CALLBACK 3 (per player, not waiting for both) ──
        service = SERVICE_DEFINITIONS["answers"]
        result = execute_callback(
            callback_fn=self.ai.get_answers,
            callback_name="answers",
            ctx=ctx,
            deadline_seconds=service["deadline_seconds"],
        )

        answers = result.get("answers", [])

        env, subject = self.builder.build_answers_batch(
            player_id=player.participant_id,
            game_id=self.state.game_id,
            match_id=self.state.match_id,
            answers=answers,
            auth_token=self.state.auth_token,
            correlation_id=correlation_id,
        )
        player.answers_sent = True
        player.guess_message_id = env["message_id"]

        self.state.advance_phase(GamePhase.ANSWERS_SENT)
        return [(env, subject, player.email)]

    # ── Handler 4: Guess → call get_score_feedback() per player ──

    def _handle_guess(self, body: dict,
                      sender_email: str) -> List[Tuple[dict, str, str]]:
        payload = body.get("payload", {})
        player = self.state.get_player_by_email(sender_email)
        if not player:
            logger.warning(f"Guess from unknown player: {sender_email}")
            return []

        player.guess = payload
        correlation_id = body.get("message_id")

        # Build context for student callback
        ctx = self.context_builder.build_score_feedback_ctx(player, payload)

        # ── CALL STUDENT CALLBACK 4 (per player) ──
        service = SERVICE_DEFINITIONS["score_feedback"]
        result = execute_callback(
            callback_fn=self.ai.get_score_feedback,
            callback_name="score_feedback",
            ctx=ctx,
            deadline_seconds=service["deadline_seconds"],
        )

        league_points = result.get("league_points", 0)
        private_score = result.get("private_score", 0.0)
        breakdown = result.get("breakdown", {
            "opening_sentence_score": 0,
            "sentence_justification_score": 0,
            "associative_word_score": 0,
            "word_justification_score": 0,
        })
        feedback = result.get("feedback")

        player.league_points = league_points
        player.private_score = private_score
        player.feedback = feedback  # Store feedback for match result
        player.score_sent = True

        # Send Q21SCOREFEEDBACK to this player
        env, subject = self.builder.build_score_feedback(
            player_id=player.participant_id,
            game_id=self.state.game_id,
            match_id=self.state.match_id,
            league_points=league_points,
            private_score=private_score,
            breakdown=breakdown,
            feedback=feedback,
            correlation_id=correlation_id,
        )

        outgoing = [(env, subject, player.email)]

        # If BOTH players have been scored → send MATCH_RESULT_REPORT
        if self.state.both_scores_sent():
            outgoing.extend(self._build_match_result())
            self.state.advance_phase(GamePhase.MATCH_REPORTED)
        else:
            self.state.advance_phase(GamePhase.SCORING_COMPLETE)

        return outgoing

    # ── Build MATCH_RESULT_REPORT after both players scored ──

    def _build_match_result(self) -> List[Tuple[dict, str, str]]:
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

        # Include feedback in scores per PRD
        scores = [
            {
                "participant_id": p1.participant_id,
                "email": p1.email,
                "league_points": p1.league_points,
                "private_score": p1.private_score,
                "feedback": p1.feedback,
            },
            {
                "participant_id": p2.participant_id,
                "email": p2.email,
                "league_points": p2.league_points,
                "private_score": p2.private_score,
                "feedback": p2.feedback,
            },
        ]

        env, subject = self.builder.build_match_result(
            game_id=self.state.game_id,
            match_id=self.state.match_id,
            round_id=self.state.round_id,
            winner_id=winner_id,
            is_draw=is_draw,
            scores=scores,
        )

        lm_email = self.config.get("league_manager_email", "server@example.com")
        logger.info(f"Match result: winner={'DRAW' if is_draw else winner_id}")
        return [(env, subject, lm_email)]

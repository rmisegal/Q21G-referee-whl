# Area: GMC
# PRD: docs/prd-rlgm.md
"""
GMC Scoring Handler
===================

Handler for Q21GUESSSUBMISSION messages and match result building.
"""

import logging
from typing import List, Tuple

from ..state import GamePhase
from ..context_service import SERVICE_DEFINITIONS
from ..callback_executor import execute_callback
from ..match_result_builder import build_match_result as _build_match_result

logger = logging.getLogger("q21_referee.router")

_ZERO_SCORE_DEFAULTS = {
    "league_points": 0,
    "private_score": 0.0,
    "breakdown": {},
    "feedback": None,
}


def handle_guess(ctx) -> List[Tuple[dict, str, str]]:
    """
    Handle Q21GUESSSUBMISSION message.

    Calls get_score_feedback callback and sends Q21SCOREFEEDBACK.
    When both players scored, also sends MATCH_RESULT_REPORT.
    """
    body = ctx.body
    payload = body.get("payload", {})
    player = ctx.state.get_player_by_email(ctx.sender_email)

    if not player:
        logger.warning(f"Guess from unknown player: {ctx.sender_email}")
        return []
    if player.score_sent:
        logger.info(f"Duplicate guess from {player.participant_id}, ignoring")
        return []
    if ctx.state.phase not in (GamePhase.ANSWERS_SENT, GamePhase.GUESSES_COLLECTING):
        logger.warning(f"Guess in wrong phase {ctx.state.phase.value}, ignoring")
        return []

    ctx.deadline_tracker.cancel(ctx.sender_email)
    player.guess = payload
    correlation_id = body.get("message_id")

    # Build context for student callback
    callback_ctx = ctx.context_builder.build_score_feedback_ctx(player, payload)

    # Call student callback
    service = SERVICE_DEFINITIONS["score_feedback"]
    try:
        result = execute_callback(
            callback_fn=ctx.ai.get_score_feedback,
            callback_name="score_feedback",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
    except Exception:
        logger.error(
            "Scoring callback failed for %s — using zero defaults",
            player.participant_id,
            exc_info=True,
        )
        result = dict(_ZERO_SCORE_DEFAULTS)

    league_points = result.get("league_points", 0)
    private_score = result.get("private_score", 0.0)
    breakdown = result.get("breakdown", {})
    feedback = result.get("feedback")

    player.league_points = league_points
    player.private_score = private_score
    player.feedback = feedback
    player.score_sent = True

    # Send Q21SCOREFEEDBACK
    env, subject = ctx.builder.build_score_feedback(
        player_id=player.participant_id,
        game_id=ctx.state.game_id,
        match_id=ctx.state.match_id,
        league_points=league_points,
        private_score=private_score,
        breakdown=breakdown,
        feedback=feedback,
        correlation_id=correlation_id,
    )

    outgoing = [(env, subject, player.email)]

    # If both players scored, send MATCH_RESULT_REPORT
    if ctx.state.both_scores_sent():
        outgoing.extend(_build_match_result(ctx))
        ctx.state.advance_phase(GamePhase.MATCH_REPORTED)
    else:
        ctx.state.advance_phase(GamePhase.GUESSES_COLLECTING)

    return outgoing

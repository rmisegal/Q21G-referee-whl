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
from ..context_builder import SERVICE_DEFINITIONS
from ..callback_executor import execute_callback

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
    breakdown = result.get("breakdown", {
        "opening_sentence_score": 0,
        "sentence_justification_score": 0,
        "associative_word_score": 0,
        "word_justification_score": 0,
    })
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


def _build_match_result(ctx) -> List[Tuple[dict, str, str]]:
    """Build MATCH_RESULT_REPORT after both players scored."""
    p1 = ctx.state.player1
    p2 = ctx.state.player2

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

    env, subject = ctx.builder.build_match_result(
        game_id=ctx.state.game_id,
        match_id=ctx.state.match_id,
        round_id=ctx.state.round_id,
        winner_id=winner_id,
        is_draw=is_draw,
        scores=scores,
    )

    lm_email = ctx.config.get("league_manager_email", "server@example.com")
    logger.info(f"Match result: winner={'DRAW' if is_draw else winner_id}")
    return [(env, subject, lm_email)]

# Area: GMC
# PRD: docs/prd-rlgm.md
"""
GMC Questions Handler
=====================

Handler for Q21QUESTIONSBATCH messages.
"""

import logging
from typing import List, Tuple

from ..state import GamePhase
from ..context_builder import SERVICE_DEFINITIONS
from ..callback_executor import execute_callback

logger = logging.getLogger("q21_referee.router")


def handle_questions(ctx) -> List[Tuple[dict, str, str]]:
    """
    Handle Q21QUESTIONSBATCH message.

    Calls get_answers callback and sends Q21ANSWERSBATCH to the player.
    """
    body = ctx.body
    payload = body.get("payload", {})
    player = ctx.state.get_player_by_email(ctx.sender_email)

    if not player:
        logger.warning(f"Questions from unknown player: {ctx.sender_email}")
        return []

    player.questions = payload.get("questions", [])
    correlation_id = body.get("message_id")

    # Build context for student callback
    callback_ctx = ctx.context_builder.build_answers_ctx(player, player.questions)

    # Call student callback
    service = SERVICE_DEFINITIONS["answers"]
    result = execute_callback(
        callback_fn=ctx.ai.get_answers,
        callback_name="answers",
        ctx=callback_ctx,
        deadline_seconds=service["deadline_seconds"],
    )

    answers = result.get("answers", [])

    env, subject = ctx.builder.build_answers_batch(
        player_id=player.participant_id,
        game_id=ctx.state.game_id,
        match_id=ctx.state.match_id,
        answers=answers,
        auth_token=ctx.state.auth_token,
        correlation_id=correlation_id,
    )
    player.answers_sent = True
    player.guess_message_id = env["message_id"]

    if ctx.state.both_answers_sent():
        ctx.state.advance_phase(GamePhase.ANSWERS_SENT)
    else:
        ctx.state.advance_phase(GamePhase.QUESTIONS_COLLECTING)
    return [(env, subject, player.email)]

# Area: GMC
# PRD: docs/prd-rlgm.md
"""
GMC Warmup Handlers
===================

Handler for warmup response messages.
"""

import logging
from typing import List, Tuple

from ..state import GamePhase
from ..context_builder import SERVICE_DEFINITIONS
from ..callback_executor import execute_callback

logger = logging.getLogger("q21_referee.router")


def handle_warmup_response(ctx) -> List[Tuple[dict, str, str]]:
    """
    Handle Q21WARMUPRESPONSE message.

    When both players respond, calls get_round_start_info and sends Q21ROUNDSTART.
    """
    body = ctx.body
    payload = body.get("payload", {})
    player = ctx.state.get_player_by_email(ctx.sender_email)

    if not player:
        logger.warning(f"Warmup response from unknown player: {ctx.sender_email}")
        return []

    player.warmup_answer = payload.get("answer", "")
    logger.info(f"Warmup response from {player.participant_id}: '{player.warmup_answer}'")

    if not ctx.state.both_warmups_received():
        logger.info("Waiting for other player's warmup response...")
        return []

    ctx.state.advance_phase(GamePhase.WARMUP_COMPLETE)

    # Build context for student callback
    callback_ctx = ctx.context_builder.build_round_start_info_ctx()

    # Call student callback
    service = SERVICE_DEFINITIONS["round_start_info"]
    result = execute_callback(
        callback_fn=ctx.ai.get_round_start_info,
        callback_name="round_start_info",
        ctx=callback_ctx,
        deadline_seconds=service["deadline_seconds"],
    )

    ctx.state.book_name = result.get("book_name", "Unknown Book")
    ctx.state.book_hint = result.get("book_hint", "A famous book")
    ctx.state.association_word = result.get("association_word", "thing")

    # Send Q21ROUNDSTART to both players
    outgoing = []
    for player in [ctx.state.player1, ctx.state.player2]:
        env, subject = ctx.builder.build_round_start(
            player_id=player.participant_id,
            game_id=ctx.state.game_id,
            match_id=ctx.state.match_id,
            book_name=ctx.state.book_name,
            book_hint=ctx.state.book_hint,
            association_word=ctx.state.association_word,
            auth_token=ctx.state.auth_token,
        )
        player.questions_message_id = env["message_id"]
        outgoing.append((env, subject, player.email))

    ctx.state.advance_phase(GamePhase.ROUND_STARTED)
    return outgoing

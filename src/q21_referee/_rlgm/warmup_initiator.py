# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.warmup_initiator — Builds warmup calls for new rounds
========================================================================

Extracts the warmup initiation logic from orchestrator to keep files
under 150 lines. Called by orchestrator.start_round().
"""

import uuid
import logging
from typing import Any, Dict, List, Tuple

from .._gmc.gmc import GameManagementCycle
from .._gmc.state import GamePhase
from .._gmc.context_builder import ContextBuilder, SERVICE_DEFINITIONS
from .._gmc.callback_executor import execute_callback
from ..callbacks import RefereeAI
from .gprm import GPRM

logger = logging.getLogger("q21_referee.rlgm.warmup_initiator")


def initiate_warmup(
    gmc: GameManagementCycle,
    gprm: GPRM,
    ai: RefereeAI,
    config: Dict[str, Any],
) -> List[Tuple[dict, str, str]]:
    """
    Build warmup calls for both players and advance GMC to WARMUP_SENT.

    Args:
        gmc: The GameManagementCycle instance
        gprm: Game parameters
        ai: Student's RefereeAI implementation
        config: Configuration dict

    Returns:
        List of (envelope, subject, recipient) tuples
    """
    # Build callback context
    ctx_builder = ContextBuilder(config, gmc.state)
    body = {
        "payload": {
            "round_id": gprm.round_id,
            "round_number": gprm.round_number,
        }
    }
    callback_ctx = ctx_builder.build_warmup_question_ctx(body)

    # Call student callback
    service = SERVICE_DEFINITIONS["warmup_question"]
    result = execute_callback(
        callback_fn=ai.get_warmup_question,
        callback_name="warmup_question",
        ctx=callback_ctx,
        deadline_seconds=service["deadline_seconds"],
    )
    warmup_q = result.get("warmup_question", "What is 2 + 2?")

    # Set game state
    gmc.state.round_id = gprm.round_id
    gmc.state.round_number = gprm.round_number
    gmc.state.auth_token = f"tok_{uuid.uuid4().hex[:8]}"

    # Build warmup calls for both players
    outgoing = []
    for player in [gmc.state.player1, gmc.state.player2]:
        if player is None:
            logger.warning("Skipping warmup for None player")
            continue
        env, subject = gmc.builder.build_warmup_call(
            player_id=player.participant_id,
            game_id=gmc.state.game_id,
            match_id=gmc.state.match_id,
            warmup_question=warmup_q,
            auth_token=gmc.state.auth_token,
        )
        player.warmup_message_id = env["message_id"]
        outgoing.append((env, subject, player.email))

    gmc.state.advance_phase(GamePhase.WARMUP_SENT)
    return outgoing

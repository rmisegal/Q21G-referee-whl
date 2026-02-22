# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.abort_handler — Game abort logic
===================================================

Handles scoring and reporting when a game is force-aborted.
"""

import logging
from typing import Any, Dict, List, Tuple

from .._gmc.gmc import GameManagementCycle
from .._gmc.state import PlayerState
from .._gmc.context_builder import ContextBuilder
from .._gmc.context_service import SERVICE_DEFINITIONS
from .._gmc.callback_executor import execute_callback_safe
from ..callbacks import RefereeAI

logger = logging.getLogger("q21_referee.rlgm.abort")

_ABORT_SCORE_DEFAULTS = {
    "league_points": 0,
    "private_score": 0.0,
    "breakdown": {},
    "feedback": None,
}


def score_player_on_abort(
    gmc: GameManagementCycle,
    player: PlayerState,
    ai: RefereeAI,
    config: Dict[str, Any],
) -> List[Tuple[dict, str, str]]:
    """Score a player who submitted a guess during an aborted game."""
    ctx_builder = ContextBuilder(config, gmc.state)
    callback_ctx = ctx_builder.build_score_feedback_ctx(player, player.guess)

    service = SERVICE_DEFINITIONS["score_feedback"]
    try:
        result = execute_callback_safe(
            callback_fn=ai.get_score_feedback,
            callback_name="score_feedback",
            ctx=callback_ctx,
            deadline_seconds=service["deadline_seconds"],
        )
    except Exception:
        logger.error(
            "Abort scoring failed for %s — using zero defaults",
            player.participant_id,
            exc_info=True,
        )
        result = dict(_ABORT_SCORE_DEFAULTS)

    league_points = result.get("league_points", 0)
    private_score = result.get("private_score", 0.0)
    breakdown = result.get("breakdown", {})
    feedback = result.get("feedback")

    player.league_points = league_points
    player.private_score = private_score
    player.score_sent = True

    env, subject = gmc.builder.build_score_feedback(
        player_id=player.participant_id,
        game_id=gmc.state.game_id,
        match_id=gmc.state.match_id,
        league_points=league_points,
        private_score=private_score,
        breakdown=breakdown,
        feedback=feedback,
    )
    return [(env, subject, player.email)]


def determine_abort_winner(gmc: GameManagementCycle):
    """Determine winner for an aborted game (same logic as normal)."""
    p1, p2 = gmc.state.player1, gmc.state.player2
    if not p1 or not p2:
        return None
    if p1.league_points > p2.league_points:
        return p1.participant_id
    if p2.league_points > p1.league_points:
        return p2.participant_id
    return None


def is_abort_draw(gmc: GameManagementCycle) -> bool:
    """Check if aborted game is a draw."""
    p1, p2 = gmc.state.player1, gmc.state.player2
    if not p1 or not p2:
        return True
    return p1.league_points == p2.league_points


def build_abort_scores(gmc: GameManagementCycle) -> list:
    """Build scores list for aborted game match result."""
    scores = []
    for player in [gmc.state.player1, gmc.state.player2]:
        if player is None:
            continue
        scores.append({
            "participant_id": player.participant_id,
            "email": player.email,
            "league_points": player.league_points,
            "private_score": player.private_score,
        })
    return scores


Msgs = List[Tuple[dict, str, str]]


def build_abort_report(
    gmc: GameManagementCycle,
    reason: str,
    ai: RefereeAI,
    config: Dict[str, Any],
) -> Msgs:
    """Build the full abort report: score unscored players, send match result.

    Returns list of outgoing (envelope, subject, recipient) tuples.
    """
    outgoing: Msgs = []
    snapshot = gmc.get_state_snapshot()
    for key in ["player1", "player2"]:
        player = getattr(gmc.state, key)
        if player is not None and player.guess is not None and not player.score_sent:
            outgoing.extend(score_player_on_abort(gmc, player, ai, config))
    env, subj = gmc.builder.build_match_result(
        game_id=gmc.gprm.game_id, match_id=gmc.gprm.match_id,
        round_id=gmc.gprm.round_id, winner_id=determine_abort_winner(gmc),
        is_draw=is_abort_draw(gmc), scores=build_abort_scores(gmc),
        status="aborted", abort_reason=reason,
        player_states={"player1": snapshot["player1"],
                       "player2": snapshot["player2"]})
    outgoing.append((env, subj, config.get("league_manager_email", "")))
    return outgoing

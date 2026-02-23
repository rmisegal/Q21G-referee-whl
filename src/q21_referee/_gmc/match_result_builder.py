# Area: GMC
# PRD: docs/prd-rlgm.md
"""
Build MATCH_RESULT_REPORT envelope after scoring completes.

Extracted from handlers/scoring.py to support single-player mode.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger("q21_referee.router")

_ROLE_TO_LABEL = {"player1": "PLAYER_A", "player2": "PLAYER_B"}


def build_match_result(ctx) -> List[Tuple[dict, str, str]]:
    """Build MATCH_RESULT_REPORT after scoring completes."""
    p1 = ctx.state.player1
    p2 = ctx.state.player2

    winner_id, is_draw = _determine_winner(p1, p2)
    scores = _build_scores(p1, p2, ctx.state)

    kwargs = dict(
        game_id=ctx.state.game_id,
        match_id=ctx.state.match_id,
        round_id=ctx.state.round_id,
        winner_id=winner_id,
        is_draw=is_draw,
        scores=scores,
    )

    if ctx.state.single_player_mode:
        kwargs["status"] = "COMPLETED_SINGLE_PLAYER"
        kwargs["single_player_mode"] = True
        kwargs["missing_player"] = _ROLE_TO_LABEL[ctx.state.missing_player_role]
        kwargs["missing_player_email"] = ctx.state.missing_player_email
        kwargs["missing_reason"] = "MALFUNCTION"

    env, subject = ctx.builder.build_match_result(**kwargs)

    lm_email = ctx.config.get("league_manager_email", "")
    logger.info("Match result: winner=%s", "DRAW" if is_draw else winner_id)
    return [(env, subject, lm_email)]


def _determine_winner(p1, p2):
    """Return (winner_id, is_draw) based on league points."""
    if p1.league_points > p2.league_points:
        return p1.participant_id, False
    if p2.league_points > p1.league_points:
        return p2.participant_id, False
    return None, True


def _build_scores(p1, p2, state):
    """Build scores list, adding score_reason for missing player."""
    scores = []
    for role, player in [("player1", p1), ("player2", p2)]:
        entry = {
            "participant_id": player.participant_id,
            "email": player.email,
            "league_points": player.league_points,
            "private_score": player.private_score,
            "feedback": player.feedback,
        }
        if state.single_player_mode and role == state.missing_player_role:
            entry["score_reason"] = "TECHNICAL_LOSS_MALFUNCTION"
        scores.append(entry)
    return scores

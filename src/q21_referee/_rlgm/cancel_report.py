# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.cancel_report — Cancelled match report
=========================================================

Builds MATCH_RESULT_REPORT for matches cancelled due to both players
being absent (malfunctioned).
"""

import logging
from typing import Any, Dict, List, Tuple

from .gprm import GPRM
from .._gmc.envelope_builder import EnvelopeBuilder

logger = logging.getLogger("q21_referee.rlgm.cancel")

Msgs = List[Tuple[dict, str, str]]


def build_cancel_report(gprm: GPRM, config: Dict[str, Any]) -> Msgs:
    """Build MATCH_RESULT_REPORT for a cancelled match (both players missing).

    Returns a single-element list of (envelope, subject, recipient) tuples
    addressed to the league manager.
    """
    builder = EnvelopeBuilder(
        referee_email=config.get("referee_email", ""),
        referee_id=config.get("referee_id", ""),
        league_id=config.get("league_id", ""),
        season_id=gprm.season_id,
    )
    env, subj = builder.build_match_result(
        game_id=gprm.game_id,
        match_id=gprm.match_id,
        round_id=gprm.round_id,
        winner_id=None,
        is_draw=True,
        scores=[],
        status="CANCELLED_ALL_PLAYERS_MALFUNCTION",
    )
    lm_email = config.get("league_manager_email", "")
    logger.info("Match %s cancelled — both players missing", gprm.match_id)
    return [(env, subj, lm_email)]

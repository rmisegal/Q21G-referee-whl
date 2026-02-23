# Area: RLGM
# PRD: docs/prd-rlgm.md
"""Pre-game malfunction detection from participant lookup table."""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("q21_referee.rlgm.malfunction")


def detect_malfunctions(
    lookup_table: Optional[List[str]],
    player1_email: str,
    player2_email: str,
) -> Dict[str, Any]:
    """Detect player malfunctions from the participant lookup table.

    Compares the lookup table (list of emails that checked in) against
    the expected player emails for this game.

    Args:
        lookup_table: List of emails from participant_lookup_table,
                      or None if not provided in payload.
        player1_email: Expected email for player 1.
        player2_email: Expected email for player 2.

    Returns:
        Dict with 'status' key: NORMAL, SINGLE_PLAYER, or CANCELLED.
        SINGLE_PLAYER includes missing_player_role and missing_player_email.
    """
    if lookup_table is None:
        return {"status": "NORMAL", "missing_players": []}

    lookup_set = {e.lower() for e in lookup_table}
    missing, missing_roles = [], []

    if player1_email.lower() not in lookup_set:
        missing.append(player1_email)
        missing_roles.append("player1")
    if player2_email.lower() not in lookup_set:
        missing.append(player2_email)
        missing_roles.append("player2")

    if len(missing) == 0:
        return {"status": "NORMAL", "missing_players": []}

    if len(missing) == 2:
        return {"status": "CANCELLED", "missing_players": missing}

    return {
        "status": "SINGLE_PLAYER",
        "missing_players": missing,
        "missing_player_role": missing_roles[0],
        "missing_player_email": missing[0],
    }

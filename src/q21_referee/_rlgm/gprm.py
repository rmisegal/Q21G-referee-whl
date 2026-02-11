# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.gprm — Game Parameters (GPRM) Dataclass
=========================================================

Defines the GPRM (Game Parameters) dataclass that is passed from RLGM
to GMC when starting a new game. Contains all the context needed for
GMC to execute a single match.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GPRM:
    """
    Game Parameters passed from RLGM to GMC.

    This is a frozen (immutable) dataclass containing all the information
    GMC needs to execute a single game between two players. Once created,
    the game_id and other fields cannot be modified.

    Attributes:
        player1_email: Email address of player 1
        player1_id: Unique identifier for player 1
        player2_email: Email address of player 2
        player2_id: Unique identifier for player 2
        season_id: Current season identifier
        game_id: Unique game identifier
        match_id: Match identifier within the round
        round_id: Current round identifier
        round_number: Numeric round number (1-based)
    """

    player1_email: str
    player1_id: str
    player2_email: str
    player2_id: str
    season_id: str
    game_id: str
    match_id: str
    round_id: str
    round_number: int

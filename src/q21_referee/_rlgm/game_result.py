# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.game_result — Game Result Dataclasses
=======================================================

Defines the GameResult and PlayerScore dataclasses that GMC returns
to RLGM after a game completes. These are then reported to the
League Manager.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PlayerScore:
    """
    Individual player's score and statistics from a game.

    Attributes:
        player_id: Unique identifier for the player
        player_email: Email address of the player
        score: Final score achieved
        questions_answered: Total questions answered
        correct_answers: Number of correct answers
    """

    player_id: str
    player_email: str
    score: int
    questions_answered: int
    correct_answers: int


@dataclass
class GameResult:
    """
    Complete result of a game between two players.

    Returned by GMC to RLGM after a match completes. Contains
    both players' scores and the winner determination.

    Attributes:
        game_id: Unique game identifier
        match_id: Match identifier within the round
        round_id: Round identifier
        season_id: Season identifier
        player1: Player 1's score and statistics
        player2: Player 2's score and statistics
        winner_id: ID of the winning player, or None if draw
        is_draw: True if the game ended in a draw
        status: Game completion status ('completed' or 'aborted')
        abort_reason: Reason for abort, if status is 'aborted'
        player_states: Per-player state snapshots at time of abort
    """

    game_id: str
    match_id: str
    round_id: str
    season_id: str
    player1: PlayerScore
    player2: PlayerScore
    winner_id: Optional[str]
    is_draw: bool
    status: str = "completed"
    abort_reason: Optional[str] = None
    player_states: Optional[dict] = None

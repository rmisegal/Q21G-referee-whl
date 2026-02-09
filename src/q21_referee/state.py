"""
q21_referee.state — Game state tracker
=======================================

Tracks the lifecycle of a single game across all Q21 phases.
Knows which players have responded at each stage, stores the
referee's chosen book/hint/word, and determines when both players
are ready for the next step.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger("q21_referee.state")


class GamePhase(Enum):
    """Current phase of the Q21 game within a single round."""
    IDLE                    = "idle"                     # Waiting for BROADCAST_NEW_LEAGUE_ROUND
    WARMUP_SENT             = "warmup_sent"              # Q21WARMUPCALL sent, waiting for responses
    WARMUP_COMPLETE         = "warmup_complete"          # Both players responded to warmup
    ROUND_STARTED           = "round_started"            # Q21ROUNDSTART sent to both players
    QUESTIONS_COLLECTING    = "questions_collecting"     # Collecting Q21QUESTIONSBATCH from players
    ANSWERS_SENT            = "answers_sent"             # Q21ANSWERSBATCH sent (per-player)
    GUESSES_COLLECTING      = "guesses_collecting"       # Collecting Q21GUESSSUBMISSION from players
    SCORING_COMPLETE        = "scoring_complete"         # Q21SCOREFEEDBACK sent to both
    MATCH_REPORTED          = "match_reported"           # MATCH_RESULT_REPORT sent to LM


@dataclass
class PlayerState:
    """Tracks one player's progress through the game."""
    email: str
    participant_id: str
    warmup_answer: Optional[str] = None
    warmup_message_id: Optional[str] = None         # correlation_id for response
    questions: Optional[list] = None
    questions_message_id: Optional[str] = None       # correlation_id for answers
    guess: Optional[Dict[str, Any]] = None
    guess_message_id: Optional[str] = None           # correlation_id for score
    answers_sent: bool = False
    score_sent: bool = False
    league_points: int = 0
    private_score: float = 0.0
    feedback: Optional[Dict[str, str]] = None  # {opening_sentence, associative_word}


@dataclass
class GameState:
    """
    Full state of one game (one round, one match between two players).

    The package maintains this internally. Students never see it.
    """
    game_id: str
    match_id: str
    season_id: str
    league_id: str
    round_id: Optional[str] = None
    round_number: Optional[int] = None
    phase: GamePhase = GamePhase.IDLE

    # The two players
    player1: Optional[PlayerState] = None
    player2: Optional[PlayerState] = None

    # Referee's chosen content (from callback 2)
    book_name: Optional[str] = None
    book_hint: Optional[str] = None
    association_word: Optional[str] = None

    # Auth token for this game session
    auth_token: Optional[str] = None

    # Message IDs for correlation
    warmup_call_message_ids: Dict[str, str] = field(default_factory=dict)
    round_start_message_ids: Dict[str, str] = field(default_factory=dict)

    # ── Phase transition helpers ─────────────────────────────

    def both_warmups_received(self) -> bool:
        return (self.player1 is not None and self.player1.warmup_answer is not None
                and self.player2 is not None and self.player2.warmup_answer is not None)

    def get_player_by_email(self, email: str) -> Optional[PlayerState]:
        if self.player1 and self.player1.email == email:
            return self.player1
        if self.player2 and self.player2.email == email:
            return self.player2
        return None

    def both_scores_sent(self) -> bool:
        return (self.player1 is not None and self.player1.score_sent
                and self.player2 is not None and self.player2.score_sent)

    def advance_phase(self, new_phase: GamePhase):
        logger.info(f"[{self.game_id}] Phase: {self.phase.value} → {new_phase.value}")
        self.phase = new_phase

    def reset_for_new_round(self):
        """Reset player state for a new round while keeping player info."""
        logger.info(f"[{self.game_id}] Resetting state for new round")
        for player in [self.player1, self.player2]:
            if player:
                player.warmup_answer = None
                player.warmup_message_id = None
                player.questions = None
                player.questions_message_id = None
                player.guess = None
                player.guess_message_id = None
                player.answers_sent = False
                player.score_sent = False
                player.league_points = 0
                player.private_score = 0.0
                player.feedback = None

        self.book_name = None
        self.book_hint = None
        self.association_word = None
        self.auth_token = None
        self.warmup_call_message_ids.clear()
        self.round_start_message_ids.clear()
        self.phase = GamePhase.IDLE

# Area: Student Callbacks
# PRD: docs/prd-rlgm.md
"""Callback context/response TypedDicts. Contexts are wrapped:
{"dynamic": <data>, "service": <metadata>}. Access: ctx.get("dynamic", ctx)"""
from typing import TypedDict, List, Literal, Optional

class ServiceDefinition(TypedDict):
    """Service metadata passed alongside dynamic context."""
    name: str
    description: str
    required_output_fields: List[str]
    deadline_seconds: int

class CallbackContext(TypedDict):
    """Outer wrapper: {"dynamic": <data>, "service": <metadata>}."""
    dynamic: dict
    service: ServiceDefinition

class WarmupContext(TypedDict):
    """Dynamic section of get_warmup_question() context."""
    season_id: str
    league_id: str
    game_id: str
    match_id: str
    referee_id: str
    round_number: int
    round_id: str
    assignment_table_id: str
    player_a_id: Optional[str]
    player_a_email: Optional[str]
    player_b_id: Optional[str]
    player_b_email: Optional[str]

class WarmupResponse(TypedDict):
    """Return from get_warmup_question(): a simple connectivity question."""
    warmup_question: str
class PlayerWithWarmup(TypedDict):
    """Player info with warmup answer (used in RoundStartContext)."""
    id: Optional[str]
    email: Optional[str]
    warmup_answer: Optional[str]

class RoundStartContext(TypedDict):
    """Dynamic section of get_round_start_info() context."""
    season_id: str
    league_id: str
    game_id: str
    match_id: str
    referee_id: str
    round_number: int
    round_id: str
    assignment_table_id: str
    player_a: PlayerWithWarmup
    player_b: PlayerWithWarmup

class RoundStartResponse(TypedDict):
    """Return from get_round_start_info()."""
    book_name: str          # Actual book title (secret)
    book_hint: str          # 15-word hint for players
    association_word: str   # Thematic word related to book

class QuestionOptions(TypedDict):
    """Multiple choice options A-D."""
    A: str
    B: str
    C: str
    D: str

class PlayerQuestion(TypedDict):
    """A single question from the player."""
    question_number: int
    question_text: str
    options: QuestionOptions

class AnswersContext(TypedDict):
    """Dynamic section of get_answers() context."""
    season_id: str
    league_id: str
    game_id: str
    match_id: str
    referee_id: str
    round_number: int
    round_id: str
    assignment_table_id: str
    player_id: str
    player_email: str
    book_name: str
    book_hint: str
    association_word: str
    questions: List[PlayerQuestion]

class Answer(TypedDict):
    """An answer to one player question."""
    question_number: int  # 1-20
    answer: Literal["A", "B", "C", "D", "Not Relevant"]
class AnswersResponse(TypedDict):
    """Return from get_answers()."""
    answers: List[Answer]
class PlayerGuess(TypedDict):
    """Player's guess data nested in ScoreFeedbackContext."""
    opening_sentence: str
    sentence_justification: str
    associative_word: str
    word_justification: str
    confidence: Optional[float]

class ScoreFeedbackContext(TypedDict):
    """Dynamic section of get_score_feedback() context."""
    season_id: str
    league_id: str
    game_id: str
    match_id: str
    referee_id: str
    round_number: int
    round_id: str
    assignment_table_id: str
    player_id: str
    player_email: str
    book_name: str                          # Actual book name
    book_hint: str
    association_word: str                    # Actual association word
    actual_opening_sentence: Optional[str]
    actual_associative_word: Optional[str]
    player_guess: PlayerGuess

class ScoreBreakdown(TypedDict):
    """Score breakdown (0-100). Weights: sentence 50%, sent_just 20%, word 20%, word_just 10%."""
    opening_sentence_score: float
    sentence_justification_score: float
    associative_word_score: float
    word_justification_score: float

class FeedbackMessages(TypedDict):
    """Human-readable feedback (150-200 words each)."""
    opening_sentence: str
    associative_word: str
class ScoreFeedbackResponse(TypedDict):
    """Return from get_score_feedback(). league_points: 3 if >=80, 2 if >=60, 1 if >=40, else 0."""
    league_points: Literal[0, 1, 2, 3]
    private_score: float        # 0.0-100.0
    breakdown: ScoreBreakdown
    feedback: FeedbackMessages

__all__ = [  # noqa: E501
    "ServiceDefinition", "CallbackContext", "WarmupContext", "WarmupResponse",
    "PlayerWithWarmup", "RoundStartContext", "RoundStartResponse", "QuestionOptions",
    "PlayerQuestion", "AnswersContext", "Answer", "AnswersResponse", "PlayerGuess",
    "ScoreFeedbackContext", "ScoreBreakdown", "FeedbackMessages", "ScoreFeedbackResponse",
]

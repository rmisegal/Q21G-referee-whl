"""
q21_referee.types — TypedDict schemas for callback inputs/outputs
==================================================================

This module documents the exact structure of context dictionaries
passed to each RefereeAI callback method and the expected return formats.

Students should reference these types when implementing their AI logic.
All types are exported from the main package:

    from q21_referee import WarmupContext, AnswersContext, ...

Use __annotations__ to inspect fields:

    >>> WarmupContext.__annotations__
    {'round_number': int, 'round_id': str, 'game_id': str, 'players': List[PlayerInfo]}
"""

from typing import TypedDict, List, Literal


# ============================================
# get_warmup_question() Input/Output
# ============================================

class PlayerInfo(TypedDict):
    """Information about a player in the match."""
    email: str              # e.g., "player1@example.com"
    participant_id: str     # e.g., "P001"


class WarmupContext(TypedDict):
    """Context passed to get_warmup_question().

    Fields
    ------
    round_number : int
        The round number (1, 2, 3, ...).
    round_id : str
        Round identifier, e.g., "ROUND_1".
    game_id : str
        Game identifier, e.g., "0101001".
    players : List[PlayerInfo]
        List of two players in this match.
    """
    round_number: int
    round_id: str
    game_id: str
    players: List[PlayerInfo]


class WarmupResponse(TypedDict):
    """Expected return from get_warmup_question().

    Fields
    ------
    warmup_question : str
        A simple question to verify player connectivity.
        Example: "What is the capital of France?"
    """
    warmup_question: str


# ============================================
# get_round_start_info() Input/Output
# ============================================

class PlayerWithWarmup(TypedDict):
    """Player info including their warmup answer."""
    email: str              # e.g., "player1@example.com"
    participant_id: str     # e.g., "P001"
    warmup_answer: str      # Their answer to the warmup question


class RoundStartContext(TypedDict):
    """Context passed to get_round_start_info().

    Fields
    ------
    round_number : int
        The round number.
    game_id : str
        Game identifier.
    match_id : str
        Match identifier, e.g., "SEASON_0101001".
    player1 : PlayerWithWarmup
        First player's info including their warmup answer.
    player2 : PlayerWithWarmup
        Second player's info including their warmup answer.
    """
    round_number: int
    game_id: str
    match_id: str
    player1: PlayerWithWarmup
    player2: PlayerWithWarmup


class RoundStartResponse(TypedDict):
    """Expected return from get_round_start_info().

    Fields
    ------
    book_name : str
        The actual book title (kept secret from players).
        Example: "The Great Gatsby"
    book_hint : str
        A 15-word description hint for the players.
        Example: "A novel about the American Dream in the 1920s Jazz Age"
    association_word : str
        A thematic word related to the book.
        Example: "green"
    """
    book_name: str
    book_hint: str
    association_word: str


# ============================================
# get_answers() Input/Output
# ============================================

class QuestionOptions(TypedDict):
    """Multiple choice options for a question."""
    A: str      # e.g., "Yes"
    B: str      # e.g., "No"
    C: str      # e.g., "Partially"
    D: str      # e.g., "Unknown"


class PlayerQuestion(TypedDict):
    """A single question from the player.

    Fields
    ------
    question_number : int
        Question number from 1 to 20.
    question_text : str
        The question the player is asking about the book.
        Example: "Is this book set in America?"
    options : QuestionOptions
        The four multiple choice options (A, B, C, D).
    """
    question_number: int
    question_text: str
    options: QuestionOptions


class AnswersContext(TypedDict):
    """Context passed to get_answers().

    This is called when a player submits their 20 questions.
    You have access to the book info you chose earlier.

    Fields
    ------
    match_id : str
        Match identifier.
    game_id : str
        Game identifier.
    player_email : str
        Email of the player who submitted questions.
    player_id : str
        Participant ID of the player.
    book_name : str
        The book YOU chose in get_round_start_info().
    book_hint : str
        The hint YOU provided.
    association_word : str
        The association word YOU chose.
    questions : List[PlayerQuestion]
        List of 20 questions from the player.
    """
    match_id: str
    game_id: str
    player_email: str
    player_id: str
    book_name: str
    book_hint: str
    association_word: str
    questions: List[PlayerQuestion]


class Answer(TypedDict):
    """An answer to a player's question.

    Fields
    ------
    question_number : int
        The question number being answered (1-20).
    answer : Literal["A", "B", "C", "D", "Not Relevant"]
        The chosen answer. Use "Not Relevant" for inappropriate questions.
    """
    question_number: int
    answer: Literal["A", "B", "C", "D", "Not Relevant"]


class AnswersResponse(TypedDict):
    """Expected return from get_answers().

    Fields
    ------
    answers : List[Answer]
        List of 20 answers, one for each question.
    """
    answers: List[Answer]


# ============================================
# get_score_feedback() Input/Output
# ============================================

class ScoreFeedbackContext(TypedDict):
    """Context passed to get_score_feedback().

    This is called when a player submits their final guess.
    Compare their guess to the actual book/word you chose.

    Fields
    ------
    match_id : str
        Match identifier.
    game_id : str
        Game identifier.
    player_email : str
        Email of the player who submitted the guess.
    player_id : str
        Participant ID of the player.
    book_name : str
        The ACTUAL book name (what you chose).
    book_hint : str
        The hint you provided.
    association_word : str
        The ACTUAL association word (what you chose).
    opening_sentence : str
        Player's GUESSED opening sentence of the book.
    sentence_justification : str
        Player's reasoning for their sentence guess (30-50 words).
    associative_word : str
        Player's GUESSED association word.
        NOTE: Compare this to 'association_word' (the actual).
    word_justification : str
        Player's reasoning for their word guess (20-30 words).
    confidence : float
        Player's confidence in their guess (0.0 to 1.0).
    """
    match_id: str
    game_id: str
    player_email: str
    player_id: str
    book_name: str
    book_hint: str
    association_word: str
    opening_sentence: str
    sentence_justification: str
    associative_word: str
    word_justification: str
    confidence: float


class ScoreBreakdown(TypedDict):
    """Detailed score breakdown (0-100 each).

    Fields
    ------
    opening_sentence_score : float
        How close is their guessed sentence to the actual? (50% weight)
    sentence_justification_score : float
        Quality of their reasoning for the sentence. (20% weight)
    associative_word_score : float
        How close is their guessed word to the actual? (20% weight)
    word_justification_score : float
        Quality of their reasoning for the word. (10% weight)
    """
    opening_sentence_score: float
    sentence_justification_score: float
    associative_word_score: float
    word_justification_score: float


class FeedbackMessages(TypedDict):
    """Human-readable feedback for the player.

    Fields
    ------
    opening_sentence : str
        Feedback about their sentence guess (150-200 words).
        Example: "Excellent! You got the opening sentence exactly right!"
    associative_word : str
        Feedback about their word guess (150-200 words).
        Example: "Close! The word was 'green' (the green light), not 'money'."
    """
    opening_sentence: str
    associative_word: str


class ScoreFeedbackResponse(TypedDict):
    """Expected return from get_score_feedback().

    Scoring Guide
    -------------
    - league_points: 3 if private_score >= 80, 2 if >= 60, 1 if >= 40, else 0
    - private_score: Weighted average of breakdown scores

    Fields
    ------
    league_points : Literal[0, 1, 2, 3]
        Points awarded for the league standings.
    private_score : float
        Overall score from 0.0 to 100.0.
    breakdown : ScoreBreakdown
        Detailed breakdown of each scoring component.
    feedback : FeedbackMessages
        Human-readable feedback for the player.
    """
    league_points: Literal[0, 1, 2, 3]
    private_score: float
    breakdown: ScoreBreakdown
    feedback: FeedbackMessages


# ============================================
# Export all types
# ============================================

__all__ = [
    # Warmup types
    "PlayerInfo",
    "WarmupContext",
    "WarmupResponse",
    # Round start types
    "PlayerWithWarmup",
    "RoundStartContext",
    "RoundStartResponse",
    # Answers types
    "QuestionOptions",
    "PlayerQuestion",
    "AnswersContext",
    "Answer",
    "AnswersResponse",
    # Score feedback types
    "ScoreFeedbackContext",
    "ScoreBreakdown",
    "FeedbackMessages",
    "ScoreFeedbackResponse",
]

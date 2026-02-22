# Area: Student Callbacks
# PRD: docs/prd-rlgm.md
"""
q21_referee.callbacks — The 4 callback functions students implement
===================================================================

Students subclass RefereeAI and implement the 4 methods.
Each method receives a context dict and returns a result dict.

The package calls these methods at the right time based on incoming
protocol messages. Students never see envelopes or protocol details.

Type Definitions
----------------
All input/output types are defined in types.py and can be imported:

    from q21_referee import (
        WarmupContext, WarmupResponse,
        RoundStartContext, RoundStartResponse,
        AnswersContext, AnswersResponse,
        ScoreFeedbackContext, ScoreFeedbackResponse,
    )

Inspect field types:
    >>> WarmupContext.__annotations__
    {'round_number': int, 'round_id': str, ...}
"""

from abc import ABC, abstractmethod
from .types import (
    WarmupContext, WarmupResponse,
    RoundStartContext, RoundStartResponse,
    AnswersContext, AnswersResponse,
    ScoreFeedbackContext, ScoreFeedbackResponse,
)


class RefereeAI(ABC):
    """
    Abstract base class for the Q21 Referee AI.

    Subclass this and implement all 4 methods. The package will call
    each method when the corresponding trigger message arrives.

    Every method receives a `ctx` dict with the relevant game context
    and must return a result dict with the required fields.

    See types.py for complete TypedDict definitions of all inputs/outputs.
    """

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 1: Generate a warmup question
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_warmup_question(self, ctx: WarmupContext) -> WarmupResponse:
        """
        Called when BROADCAST_NEW_LEAGUE_ROUND is received.
        You must return a simple question to verify player connectivity.

        Parameters
        ----------
        ctx : WarmupContext
            {
                "round_number": int,        # e.g. 1
                "round_id": str,            # e.g. "ROUND_1"
                "game_id": str,             # e.g. "0101001"
                "players": [                # list of player info
                    {"email": str, "participant_id": str},
                    {"email": str, "participant_id": str}
                ]
            }

        Returns
        -------
        WarmupResponse
            {
                "warmup_question": str      # e.g. "What is the capital of France?"
            }

        Example
        -------
        >>> def get_warmup_question(self, ctx):
        ...     return {"warmup_question": "What is 2 + 2?"}

        LLM Tip
        -------
        Use this to assess player knowledge or just provide a fun trivia
        question. The answer doesn't affect scoring - it's just a connectivity
        check. You can generate creative questions with an LLM or use hardcoded
        ones.
        """
        ...

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 2: Provide the book, hint, and association word
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_round_start_info(self, ctx: RoundStartContext) -> RoundStartResponse:
        """
        Called when BOTH players have responded to the warmup
        (Q21WARMUPRESPONSE received from both).

        You must select a book, write a hint, and choose an association word.

        Parameters
        ----------
        ctx : RoundStartContext
            {
                "round_number": int,
                "game_id": str,
                "match_id": str,
                "player1": {
                    "email": str,
                    "participant_id": str,
                    "warmup_answer": str    # their answer to the warmup question
                },
                "player2": {
                    "email": str,
                    "participant_id": str,
                    "warmup_answer": str
                }
            }

        Returns
        -------
        RoundStartResponse
            {
                "book_name": str,           # e.g. "The Great Gatsby"
                "book_hint": str,           # 15-word description of the book
                "association_word": str      # domain word, e.g. "color"
            }

        Example
        -------
        >>> def get_round_start_info(self, ctx):
        ...     return {
        ...         "book_name": "1984",
        ...         "book_hint": "Dystopian novel about totalitarian surveillance",
        ...         "association_word": "number"
        ...     }

        LLM Tip
        -------
        Choose a book you can answer questions about accurately. Use an LLM
        to generate creative book selections and hints. The hint should be
        helpful but not give away the title. The association_word should
        relate thematically to the book (e.g., "green" for The Great Gatsby).

        Prompt idea:
            "Select a well-known book and provide:
             1. The exact title
             2. A 15-word hint that describes the theme without revealing the title
             3. A single word that thematically relates to the book"
        """
        ...

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 3: Answer the player's 20 questions
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_answers(self, ctx: AnswersContext) -> AnswersResponse:
        """
        Called when a player submits Q21QUESTIONSBATCH.
        Called ONCE PER PLAYER (not waiting for both).

        You must answer each multiple-choice question with A, B, C, D,
        or "Not Relevant".

        Parameters
        ----------
        ctx : AnswersContext
            {
                "match_id": str,
                "game_id": str,
                "player_email": str,
                "player_id": str,
                "book_name": str,           # the book you chose in callback 2
                "book_hint": str,
                "association_word": str,
                "questions": [              # list of question dicts
                    {
                        "question_number": int,     # 1-20
                        "question_text": str,
                        "options": {
                            "A": str,
                            "B": str,
                            "C": str,
                            "D": str
                        }
                    },
                    ...
                ]
            }

        Returns
        -------
        AnswersResponse
            {
                "answers": [
                    {"question_number": int, "answer": str},
                    ...    # answer must be "A", "B", "C", "D", or "Not Relevant"
                ]
            }

        Example
        -------
        >>> def get_answers(self, ctx):
        ...     # Use an LLM to answer based on the book
        ...     answers = []
        ...     for q in ctx["questions"]:
        ...         choice = my_llm_answer(ctx["book_name"], q)
        ...         answers.append({"question_number": q["question_number"],
        ...                         "answer": choice})
        ...     return {"answers": answers}

        LLM Tip
        -------
        Answer accurately based on the book YOU chose. Structure your prompt
        to include the book context and each question with its options.

        Prompt idea:
            "You are answering questions about the book '{book_name}'.
             For each question, choose A, B, C, D, or 'Not Relevant'.

             Question {n}: {question_text}
             A: {options['A']}
             B: {options['B']}
             C: {options['C']}
             D: {options['D']}

             Answer only with the letter or 'Not Relevant'."

        If a question is inappropriate or unanswerable, use "Not Relevant".
        """
        ...

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 4: Score the player's guess
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_score_feedback(self, ctx: ScoreFeedbackContext) -> ScoreFeedbackResponse:
        """
        Called when a player submits Q21GUESSSUBMISSION.
        Called ONCE PER PLAYER (not waiting for both).

        You must score the player's guess and provide feedback.
        Private score is 0-100, league points are 0-3.

        Parameters
        ----------
        ctx : ScoreFeedbackContext
            {
                "match_id": str,
                "game_id": str,
                "player_email": str,
                "player_id": str,
                "book_name": str,               # ACTUAL book (what you chose)
                "book_hint": str,
                "association_word": str,        # ACTUAL word (what you chose)
                "opening_sentence": str,        # player's GUESSED sentence
                "sentence_justification": str,  # player's reasoning (30-50 words)
                "associative_word": str,        # player's GUESSED word
                "word_justification": str,      # player's reasoning (20-30 words)
                "confidence": float             # player's confidence (0.0-1.0)
            }

        Returns
        -------
        ScoreFeedbackResponse
            {
                "league_points": int,       # 0-3
                "private_score": float,     # 0.0-100.0
                "breakdown": {
                    "opening_sentence_score": float,        # 0-100 (50% weight)
                    "sentence_justification_score": float,  # 0-100 (20% weight)
                    "associative_word_score": float,        # 0-100 (20% weight)
                    "word_justification_score": float       # 0-100 (10% weight)
                },
                "feedback": {
                    "opening_sentence": str,    # 150-200 word feedback
                    "associative_word": str     # 150-200 word feedback
                }
            }

        Example
        -------
        >>> def get_score_feedback(self, ctx):
        ...     sentence_score = my_llm_score(ctx["opening_sentence"], ...)
        ...     return {
        ...         "league_points": 2,
        ...         "private_score": 72.5,
        ...         "breakdown": {
        ...             "opening_sentence_score": 80.0,
        ...             "sentence_justification_score": 70.0,
        ...             "associative_word_score": 60.0,
        ...             "word_justification_score": 80.0
        ...         },
        ...         "feedback": {
        ...             "opening_sentence": "Good attempt at ...",
        ...             "associative_word": "The word choice was ..."
        ...         }
        ...     }

        Scoring Guide
        -------------
        - league_points: 3 if private_score >= 80, 2 if >= 60, 1 if >= 40, else 0
        - private_score = (opening_sentence_score * 0.5 +
                          sentence_justification_score * 0.2 +
                          associative_word_score * 0.2 +
                          word_justification_score * 0.1)

        LLM Tip
        -------
        Compare the player's guesses to the actual values you chose.
        Use the LLM to:
        1. Compare guessed sentence to actual opening sentence
        2. Compare guessed word to your association_word
        3. Evaluate the quality of their justifications
        4. Generate constructive feedback

        Prompt idea:
            "The actual book is '{book_name}'.
             The actual opening sentence is: '{actual_sentence}'
             The player guessed: '{opening_sentence}'

             Score similarity from 0-100 and explain why."

        Remember: 'association_word' is YOUR word, 'associative_word' is
        the player's guess. Compare them for scoring.
        """
        ...

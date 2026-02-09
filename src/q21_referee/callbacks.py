"""
q21_referee.callbacks — The 4 callback functions students implement
===================================================================

Students subclass RefereeAI and implement the 4 methods.
Each method receives a context dict and returns a result dict.

The package calls these methods at the right time based on incoming
protocol messages. Students never see envelopes or protocol details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class RefereeAI(ABC):
    """
    Abstract base class for the Q21 Referee AI.

    Subclass this and implement all 4 methods. The package will call
    each method when the corresponding trigger message arrives.

    Every method receives a `ctx` dict with the relevant game context
    and must return a result dict with the required fields.
    """

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 1: Generate a warmup question
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_warmup_question(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when BROADCAST_NEW_LEAGUE_ROUND is received.
        You must return a simple question to verify player connectivity.

        Parameters
        ----------
        ctx : dict
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
        dict
            {
                "warmup_question": str      # e.g. "What is the capital of France?"
            }

        Example
        -------
        >>> def get_warmup_question(self, ctx):
        ...     return {"warmup_question": "What is 2 + 2?"}
        """
        ...

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 2: Provide the book, hint, and association word
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_round_start_info(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when BOTH players have responded to the warmup
        (Q21WARMUPRESPONSE received from both).

        You must select a book, write a hint, and choose an association word.

        Parameters
        ----------
        ctx : dict
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
        dict
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
        """
        ...

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 3: Answer the player's 20 questions
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_answers(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when a player submits Q21QUESTIONSBATCH.
        Called ONCE PER PLAYER (not waiting for both).

        You must answer each multiple-choice question with A, B, C, D,
        or "Not Relevant".

        Parameters
        ----------
        ctx : dict
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
        dict
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
        """
        ...

    # ──────────────────────────────────────────────────────────────
    # CALLBACK 4: Score the player's guess
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def get_score_feedback(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when a player submits Q21GUESSSUBMISSION.
        Called ONCE PER PLAYER (not waiting for both).

        You must score the player's guess and provide feedback.
        Private score is 0-100, league points are 0-3.

        Parameters
        ----------
        ctx : dict
            {
                "match_id": str,
                "game_id": str,
                "player_email": str,
                "player_id": str,
                "book_name": str,
                "book_hint": str,
                "association_word": str,
                "opening_sentence": str,        # player's guessed sentence
                "sentence_justification": str,  # player's reasoning (30-50 words)
                "associative_word": str,        # player's guessed word
                "word_justification": str,      # player's reasoning (20-30 words)
                "confidence": float | None      # player's confidence (0.0-1.0)
            }

        Returns
        -------
        dict
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
        """
        ...

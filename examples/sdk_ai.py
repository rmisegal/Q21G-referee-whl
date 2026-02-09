"""
sdk_ai.py — Reference implementation using the shared LLM SDK
==============================================================

This example shows how to use the shared sdk/llm_sdk to implement
the RefereeAI callbacks. The SDK handles:
- Warmup question generation
- Round start info (book selection)
- Answer generation for player questions
- Score calculation and feedback

Usage:
    from examples.sdk_ai import SDKRefereeAI
    ai = SDKRefereeAI()
"""

from q21_referee import RefereeAI

# Import from shared SDK at project root
from sdk.llm_sdk import (
    get_warmup_question,
    get_round_start_info,
    get_answers,
    get_score_feedback,
    configure,
)


class SDKRefereeAI(RefereeAI):
    """RefereeAI implementation using the shared LLM SDK."""

    def __init__(self, mode: str = "auto", demo_path: str = None):
        """Initialize with SDK configuration.

        Args:
            mode: "auto" (LLM with fallback), "llm", or "demo"
            demo_path: Path to demo files for demo mode
        """
        configure(mode=mode, demo_path=demo_path)

    def get_warmup_question(self, ctx):
        """Generate warmup question using SDK."""
        result = get_warmup_question()
        return {"warmup_question": result.get("warmup_question", "What is 2+2?")}

    def get_round_start_info(self, ctx):
        """Get book info using SDK."""
        result = get_round_start_info()
        return {
            "book_name": result.get("book_name", "Unknown"),
            "book_hint": result.get("book_hint", "A famous book"),
            "association_word": result.get("association_word", "thing"),
        }

    def get_answers(self, ctx):
        """Answer player questions using SDK."""
        dynamic = ctx.get("dynamic", ctx)
        questions = dynamic.get("questions", [])

        result = get_answers(
            questions=questions,
            book_name=dynamic.get("book_name"),
            actual_opening_sentence=dynamic.get("actual_opening_sentence"),
            actual_associative_word=dynamic.get("actual_associative_word"),
        )
        return {"answers": result.get("answers", [])}

    def get_score_feedback(self, ctx):
        """Calculate scores using SDK."""
        dynamic = ctx.get("dynamic", ctx)
        guess = dynamic.get("player_guess", dynamic)

        result = get_score_feedback(
            actual_opening_sentence=dynamic.get("actual_opening_sentence", ""),
            actual_associative_word=dynamic.get("actual_associative_word", ""),
            opening_sentence_guess=guess.get("opening_sentence", ""),
            sentence_justification=guess.get("sentence_justification", ""),
            associative_word_guess=guess.get("associative_word", ""),
            word_justification=guess.get("word_justification", ""),
        )

        return {
            "league_points": result.get("league_points", 0),
            "private_score": result.get("private_score", 0.0),
            "breakdown": result.get("breakdown", {}),
            "feedback": result.get("feedback", {}),
        }

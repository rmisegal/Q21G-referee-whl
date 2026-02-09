"""
Q21 LLM SDK
===========
Generate Q21 game content using LLM or demo files.

Usage
-----
    from sdk import (
        get_warmup_question,
        get_round_start_info,
        get_answers,
        get_score_feedback,
    )

    # Simple usage (uses demo mode or fallback)
    warmup = get_warmup_question()
    # {"warmup_question": "What is 2 + 2?"}

    round_info = get_round_start_info()
    # {"book_name": "...", "book_hint": "...", "association_word": "..."}

    answers = get_answers(questions=[...])
    # {"answers": [{"question_number": 1, "answer": "A"}, ...]}

    scores = get_score_feedback(
        actual_opening_sentence="Call me Ishmael.",
        actual_associative_word="whale",
        opening_sentence_guess="Call me Ishmael.",
        sentence_justification="...",
        associative_word_guess="whale",
        word_justification="...",
    )
    # {"league_points": 3, "private_score": 95.0, "breakdown": {...}, "feedback": {...}}
"""

import json
from typing import Any, Dict, List, Optional

from .core import (
    AnthropicClient,
    BaseLLMClient,
    GeneratorMode,
    GeneratorType,
    ScoreCalculator,
    SDKError,
    ValidationResult,
)
from .generators import (
    WarmupQuestionGenerator,
    RoundStartInfoGenerator,
    AnswersGenerator,
    ScoreFeedbackGenerator,
)


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

_config: Dict[str, Any] = {
    "mode": "auto",  # "auto", "llm", "demo"
    "demo_path": None,
    "llm_client": None,
}


def configure(
    mode: str = "auto",
    demo_path: Optional[str] = None,
    llm_client: Optional[BaseLLMClient] = None,
) -> None:
    """Configure the SDK.

    Args:
        mode: "auto" (try LLM, fall back to demo), "llm", or "demo"
        demo_path: Path to demo markdown files
        llm_client: Custom LLM client (defaults to AnthropicClient)
    """
    _config["mode"] = mode
    _config["demo_path"] = demo_path
    _config["llm_client"] = llm_client


def _get_llm_client() -> Optional[BaseLLMClient]:
    """Get configured or default LLM client."""
    if _config["llm_client"]:
        return _config["llm_client"]

    if _config["mode"] in ("auto", "llm"):
        client = AnthropicClient()
        if client.is_available():
            return client

    return None


def _get_demo_path() -> Optional[str]:
    """Get configured demo path."""
    return _config["demo_path"]


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def get_warmup_question() -> Dict[str, Any]:
    """Generate a warmup question for Q21WARMUPCALL.

    Returns:
        {"warmup_question": "..."}

    Example:
        >>> result = get_warmup_question()
        >>> print(result["warmup_question"])
        "What is 2 + 2?"
    """
    generator = WarmupQuestionGenerator(
        llm_client=_get_llm_client(),
        demo_path=_get_demo_path(),
    )
    result = generator.generate()

    validation = generator.validate(result)
    if not validation.is_valid:
        raise SDKError("warmup_question", "Validation failed", validation)

    return result


def get_round_start_info() -> Dict[str, Any]:
    """Generate round start info for Q21ROUNDSTART.

    Returns:
        {
            "book_name": "...",
            "book_hint": "...",
            "association_word": "..."
        }

    Example:
        >>> result = get_round_start_info()
        >>> print(result["book_name"])
        "The Great Gatsby"
    """
    generator = RoundStartInfoGenerator(
        llm_client=_get_llm_client(),
        demo_path=_get_demo_path(),
    )
    result = generator.generate()

    validation = generator.validate(result)
    if not validation.is_valid:
        raise SDKError("round_start_info", "Validation failed", validation)

    return result


def get_answers(
    questions: Optional[List[Dict[str, Any]]] = None,
    book_name: Optional[str] = None,
    actual_opening_sentence: Optional[str] = None,
    actual_associative_word: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate answers for Q21ANSWERSBATCH.

    Args:
        questions: List of question objects from player
        book_name: Book title (for LLM context)
        actual_opening_sentence: The actual opening sentence (for LLM context)
        actual_associative_word: The actual associative word (for LLM context)

    Returns:
        {"answers": [{"question_number": 1, "answer": "A"}, ...]}

    Example:
        >>> result = get_answers(questions=[
        ...     {"question_number": 1, "question_text": "Is it fiction?", "options": {...}}
        ... ])
        >>> print(result["answers"][0])
        {"question_number": 1, "answer": "A"}
    """
    generator = AnswersGenerator(
        llm_client=_get_llm_client(),
        demo_path=_get_demo_path(),
    )
    result = generator.generate(
        questions=questions,
        book_name=book_name,
        actual_opening_sentence=actual_opening_sentence,
        actual_associative_word=actual_associative_word,
    )

    validation = generator.validate(result)
    if not validation.is_valid:
        raise SDKError("answers", "Validation failed", validation)

    return result


def get_score_feedback(
    player: Optional[str] = None,
    actual_opening_sentence: Optional[str] = None,
    actual_associative_word: Optional[str] = None,
    opening_sentence_guess: Optional[str] = None,
    sentence_justification: Optional[str] = None,
    associative_word_guess: Optional[str] = None,
    word_justification: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate score feedback for Q21SCOREFEEDBACK.

    Can operate in two modes:
    1. Demo mode: Pass player="A" or "B" to read from demo files
    2. Calculator mode: Pass actual values and guesses to calculate scores

    Args:
        player: "A" or "B" (for demo mode)
        actual_opening_sentence: The actual opening sentence
        actual_associative_word: The actual associative word
        opening_sentence_guess: Player's sentence guess
        sentence_justification: Player's sentence justification
        associative_word_guess: Player's word guess
        word_justification: Player's word justification

    Returns:
        {
            "league_points": 0-3,
            "private_score": 0-100,
            "breakdown": {
                "opening_sentence_score": 0-100,
                "sentence_justification_score": 0-100,
                "associative_word_score": 0-100,
                "word_justification_score": 0-100
            },
            "feedback": {
                "opening_sentence": "...",
                "associative_word": "..."
            }
        }

    Example:
        >>> result = get_score_feedback(
        ...     actual_opening_sentence="Call me Ishmael.",
        ...     actual_associative_word="whale",
        ...     opening_sentence_guess="Call me Ishmael.",
        ...     sentence_justification="Based on the maritime theme...",
        ...     associative_word_guess="whale",
        ...     word_justification="The hunting theme suggests...",
        ... )
        >>> print(result["league_points"])
        3
    """
    generator = ScoreFeedbackGenerator(
        llm_client=_get_llm_client(),
        demo_path=_get_demo_path(),
    )
    result = generator.generate(
        player=player,
        actual_opening_sentence=actual_opening_sentence,
        actual_associative_word=actual_associative_word,
        opening_sentence_guess=opening_sentence_guess,
        sentence_justification=sentence_justification,
        associative_word_guess=associative_word_guess,
        word_justification=word_justification,
    )

    validation = generator.validate(result)
    if not validation.is_valid:
        raise SDKError("score_feedback", "Validation failed", validation)

    return result


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────

def calculate_scores(
    actual_opening_sentence: str,
    actual_associative_word: str,
    opening_sentence_guess: str,
    sentence_justification: str,
    associative_word_guess: str,
    word_justification: str,
) -> Dict[str, Any]:
    """Calculate scores directly using ScoreCalculator.

    This is a lower-level function that just calculates scores
    without any LLM or demo file interaction.

    Returns:
        {
            "opening_sentence_score": 0-100,
            "sentence_justification_score": 0-100,
            "associative_word_score": 0-100,
            "word_justification_score": 0-100,
            "private_score": 0-100,
            "league_points": 0-3
        }
    """
    calculator = ScoreCalculator()
    return calculator.calculate_player_scores(
        actual_sentence=actual_opening_sentence,
        actual_word=actual_associative_word,
        opening_sentence_guess=opening_sentence_guess,
        sentence_justification=sentence_justification,
        associative_word_guess=associative_word_guess,
        word_justification=word_justification,
    )


def determine_winner(
    player_a_private_score: float,
    player_b_private_score: float,
) -> Dict[str, Any]:
    """Determine the winner based on private scores.

    Returns:
        {"winner": "A" | "B" | None, "is_draw": bool}
    """
    calculator = ScoreCalculator()
    return calculator.determine_winner(player_a_private_score, player_b_private_score)


def list_generators() -> List[str]:
    """List all available generator types."""
    return [g.value for g in GeneratorType]


def get_current_mode() -> str:
    """Get the current SDK mode."""
    return _config["mode"]


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def _print_help():
    print("Q21 LLM SDK")
    print("=" * 40)
    print("\nUsage: python sdk.py <command> [options]")
    print("\nCommands:")
    print("  warmup              Generate warmup question")
    print("  round-start         Generate round start info")
    print("  answers             Generate default answers")
    print("  score               Calculate scores (interactive)")
    print("  list                List all generators")
    print("\nOptions:")
    print("  --demo-path <path>  Path to demo markdown files")
    print("  --mode <mode>       Mode: auto, llm, demo")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _print_help()
        sys.exit(0)

    cmd = sys.argv[1]

    # Parse options
    demo_path = None
    mode = "auto"
    for i, arg in enumerate(sys.argv):
        if arg == "--demo-path" and i + 1 < len(sys.argv):
            demo_path = sys.argv[i + 1]
        if arg == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]

    configure(mode=mode, demo_path=demo_path)

    try:
        if cmd == "warmup":
            result = get_warmup_question()
            print(json.dumps(result, indent=2))

        elif cmd == "round-start":
            result = get_round_start_info()
            print(json.dumps(result, indent=2))

        elif cmd == "answers":
            result = get_answers()
            print(json.dumps(result, indent=2))

        elif cmd == "score":
            print("Score calculation (using defaults):")
            result = get_score_feedback(
                actual_opening_sentence="Call me Ishmael.",
                actual_associative_word="whale",
                opening_sentence_guess="Call me Ishmael.",
                sentence_justification="The maritime theme and first-person narrative strongly suggest this classic opening.",
                associative_word_guess="whale",
                word_justification="The hunting theme and oceanic setting point to this word.",
            )
            print(json.dumps(result, indent=2))

        elif cmd == "list":
            print("Available generators:")
            for g in list_generators():
                print(f"  - {g}")

        else:
            print(f"Unknown command: {cmd}")
            _print_help()
            sys.exit(1)

    except SDKError as e:
        print(json.dumps(e.to_dict(), indent=2))
        sys.exit(1)

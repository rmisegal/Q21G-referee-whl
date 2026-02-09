"""
Q21 LLM SDK
===========
Generate Q21 game content using LLM or demo files.

Four generators:
  - get_warmup_question()   → Q21WARMUPCALL payload
  - get_round_start_info()  → Q21ROUNDSTART payload
  - get_answers()           → Q21ANSWERSBATCH payload
  - get_score_feedback()    → Q21SCOREFEEDBACK payload
"""

from .sdk import (
    # Main generators
    get_warmup_question,
    get_round_start_info,
    get_answers,
    get_score_feedback,
    # Utility functions
    calculate_scores,
    determine_winner,
    # Configuration
    configure,
    list_generators,
    get_current_mode,
)

from .core import (
    # Clients
    BaseLLMClient,
    AnthropicClient,
    MockLLMClient,
    # Calculator
    ScoreCalculator,
    # Errors
    SDKError,
    ValidationResult,
    FieldError,
    # Enums
    GeneratorMode,
    GeneratorType,
)

__all__ = [
    # Main API
    "get_warmup_question",
    "get_round_start_info",
    "get_answers",
    "get_score_feedback",
    # Utilities
    "calculate_scores",
    "determine_winner",
    "configure",
    "list_generators",
    "get_current_mode",
    # Classes
    "BaseLLMClient",
    "AnthropicClient",
    "MockLLMClient",
    "ScoreCalculator",
    # Errors
    "SDKError",
    "ValidationResult",
    "FieldError",
    # Enums
    "GeneratorMode",
    "GeneratorType",
]

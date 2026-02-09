"""
q21_referee — Q21 League Referee Package
=========================================

Students only need to import two things:

    from q21_referee import RefereeRunner, RefereeAI

Then subclass RefereeAI, implement 4 methods, and call RefereeRunner.run().

Type Definitions
----------------
All input/output types are available for import:

    from q21_referee import (
        WarmupContext, WarmupResponse,
        AnswersContext, AnswersResponse,
        ScoreFeedbackContext, ScoreFeedbackResponse,
    )

Inspect fields with __annotations__:

    >>> WarmupContext.__annotations__
    {'round_number': int, 'round_id': str, 'game_id': str, ...}
"""

from .callbacks import RefereeAI
from .runner import RefereeRunner
from .errors import (
    Q21RefereeError,
    CallbackTimeoutError,
    InvalidJSONResponseError,
    SchemaValidationError,
)
from .types import (
    # Warmup types
    PlayerInfo,
    WarmupContext,
    WarmupResponse,
    # Round start types
    PlayerWithWarmup,
    RoundStartContext,
    RoundStartResponse,
    # Answers types
    QuestionOptions,
    PlayerQuestion,
    AnswersContext,
    Answer,
    AnswersResponse,
    # Score feedback types
    ScoreFeedbackContext,
    ScoreBreakdown,
    FeedbackMessages,
    ScoreFeedbackResponse,
)

__all__ = [
    # Main classes
    "RefereeAI",
    "RefereeRunner",
    # Errors
    "Q21RefereeError",
    "CallbackTimeoutError",
    "InvalidJSONResponseError",
    "SchemaValidationError",
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
__version__ = "1.0.0"

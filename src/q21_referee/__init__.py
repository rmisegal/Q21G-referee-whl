"""
q21_referee — Q21 League Referee Package
=========================================

Two operating modes:

1. Season Mode (RLGMRunner) - Full league integration:
    from q21_referee import RLGMRunner, RefereeAI

2. Single-Game Mode (RefereeRunner) - For testing:
    from q21_referee import RefereeRunner, RefereeAI

Subclass RefereeAI, implement 4 methods, and call runner.run().

Type Definitions
----------------
All input/output types are available for import:

    from q21_referee import (
        WarmupContext, WarmupResponse,
        AnswersContext, AnswersResponse,
        ScoreFeedbackContext, ScoreFeedbackResponse,
    )
"""

from .callbacks import RefereeAI
from .runner import RefereeRunner
from .rlgm_runner import RLGMRunner
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
    "RLGMRunner",
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
__version__ = "2.0.0"

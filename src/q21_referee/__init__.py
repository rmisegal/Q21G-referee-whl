"""
q21_referee — Q21 League Referee Package
=========================================

Quick Start (no implementation needed):
    from q21_referee import DemoAI, RLGMRunner
    runner = RLGMRunner(config=config, ai=DemoAI())
    runner.run()

Custom Implementation:
    from q21_referee import RefereeAI, RLGMRunner
    class MyAI(RefereeAI): ...  # Implement 4 methods
    runner = RLGMRunner(config=config, ai=MyAI())
    runner.run()

Two operating modes:
1. Season Mode (RLGMRunner) - Full league integration
2. Single-Game Mode (RefereeRunner) - For testing

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
from .demo_ai import DemoAI
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
    "DemoAI",
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

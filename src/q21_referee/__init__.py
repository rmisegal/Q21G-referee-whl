"""
q21_referee — Q21 League Referee Package
=========================================

Students only need to import two things:

    from q21_referee import RefereeRunner, RefereeAI

Then subclass RefereeAI, implement 4 methods, and call RefereeRunner.run().
"""

from .callbacks import RefereeAI
from .runner import RefereeRunner
from .errors import (
    Q21RefereeError,
    CallbackTimeoutError,
    InvalidJSONResponseError,
    SchemaValidationError,
)

__all__ = [
    "RefereeAI",
    "RefereeRunner",
    "Q21RefereeError",
    "CallbackTimeoutError",
    "InvalidJSONResponseError",
    "SchemaValidationError",
]
__version__ = "1.0.0"

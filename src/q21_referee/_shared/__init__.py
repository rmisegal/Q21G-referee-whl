# Area: Shared
# PRD: docs/prd-rlgm.md
"""
Shared utilities used by both RLGM and GMC.

This package contains:
- Email client for Gmail communication
- Logging configuration
"""

from .email_client import EmailClient
from .logging_config import setup_logging, log_and_terminate, log_callback_error

__all__ = [
    "EmailClient",
    "setup_logging",
    "log_and_terminate",
    "log_callback_error",
]

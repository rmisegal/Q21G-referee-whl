# Area: Shared
# PRD: docs/prd-rlgm.md
"""
Shared utilities used by both RLGM and GMC.

This package contains:
- Email client for Gmail communication
- Logging configuration
- Protocol helpers for message formatting
"""

from .email_client import EmailClient
from .logging_config import setup_logging, log_and_terminate, log_callback_error
from .protocol import (
    LEAGUE_PROTOCOL,
    Q21_PROTOCOL,
    build_envelope,
    build_subject,
    generate_tx_id,
    generate_message_id,
    current_timestamp,
)

__all__ = [
    "EmailClient",
    "setup_logging",
    "log_and_terminate",
    "log_callback_error",
    "LEAGUE_PROTOCOL",
    "Q21_PROTOCOL",
    "build_envelope",
    "build_subject",
    "generate_tx_id",
    "generate_message_id",
    "current_timestamp",
]

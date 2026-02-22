# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee._shared.logging_formatters — Logging formatters and filters
=======================================================================

Contains formatter/filter classes and protocol mode flag/functions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

# Flag to control protocol-only terminal output
_protocol_mode_enabled = False


class ProtocolFilter(logging.Filter):
    """Filter that suppresses all logs when protocol mode is enabled.

    In protocol mode, we use direct print() for formatted protocol output
    instead of the standard logging handlers.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        global _protocol_mode_enabled
        # Suppress all terminal logs in protocol mode
        # (protocol output is handled via direct print())
        return not _protocol_mode_enabled


class TerminalFormatter(logging.Formatter):
    """Colored formatter for terminal output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for file output."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def enable_protocol_mode() -> None:
    """Enable protocol logging mode.

    In protocol mode:
    - Standard INFO logs are suppressed from terminal
    - Only protocol messages (green) and callbacks (orange) are shown
    - File logging remains unchanged for debugging
    """
    global _protocol_mode_enabled
    _protocol_mode_enabled = True


def disable_protocol_mode() -> None:
    """Disable protocol logging mode (restore standard logging)."""
    global _protocol_mode_enabled
    _protocol_mode_enabled = False


def is_protocol_mode_enabled() -> bool:
    """Check if protocol mode is enabled."""
    return _protocol_mode_enabled

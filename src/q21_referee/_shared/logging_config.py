# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee._shared.logging_config — Structured logging setup
=============================================================

Configures dual logging: terminal (colored) + file (JSON).
Provides error logging and termination functions.
Protocol logging mode suppresses standard logs on terminal.
"""

from __future__ import annotations
import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..errors import Q21RefereeError

# Package logger
logger = logging.getLogger("q21_referee")

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


def setup_logging(
    log_file_path: str = "q21_referee.log",
    level: int = logging.INFO,
) -> None:
    """
    Configure logging for the package.

    Parameters
    ----------
    log_file_path : str
        Path to the log file. Defaults to 'q21_referee.log' in current dir.
    level : int
        Logging level. Defaults to INFO.
    """
    # Get package logger
    pkg_logger = logging.getLogger("q21_referee")
    pkg_logger.setLevel(level)

    # Remove existing handlers
    pkg_logger.handlers.clear()

    # Terminal handler with colors
    terminal_handler = logging.StreamHandler(sys.stdout)
    terminal_handler.setLevel(level)
    terminal_handler.setFormatter(TerminalFormatter(
        fmt="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    ))
    # Add filter to suppress logs in protocol mode
    terminal_handler.addFilter(ProtocolFilter())
    pkg_logger.addHandler(terminal_handler)

    # File handler with JSON
    try:
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())
        pkg_logger.addHandler(file_handler)
    except Exception as e:
        pkg_logger.warning(f"Could not create log file: {e}")

    # Prevent propagation to root logger
    pkg_logger.propagate = False


def log_callback_error(error: "Q21RefereeError") -> None:
    """
    Log a callback error in the structured format.

    Parameters
    ----------
    error : Q21RefereeError
        The error to log (CallbackTimeoutError, InvalidJSONResponseError,
        or SchemaValidationError).
    """
    # Get formatted error block
    error_block = error.format_error_log()

    # Print to terminal (bypassing logger for exact formatting)
    print(error_block, file=sys.stderr)

    # Also log to file via logger
    logger.error(
        f"Callback error: {error.__class__.__name__}",
        extra={
            "callback_name": getattr(error, "callback_name", None),
            "error_type": error.__class__.__name__,
        },
    )


def log_and_terminate(error: "Q21RefereeError", exit_code: int = 1) -> None:
    """
    Log the error and terminate the process.

    Parameters
    ----------
    error : Q21RefereeError
        The error to log.
    exit_code : int
        Exit code for the process. Defaults to 1.
    """
    log_callback_error(error)
    logger.critical("Process terminated due to callback error")
    sys.exit(exit_code)


def enable_protocol_mode() -> None:
    """
    Enable protocol logging mode.

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

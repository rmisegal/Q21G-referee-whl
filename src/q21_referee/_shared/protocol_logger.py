# Area: Shared
# PRD: docs/LOGGER_OUTPUT_REFEREE.md
"""
q21_referee._shared.protocol_logger — Protocol message logging
================================================================

Structured logging for protocol messages and callbacks.
Shows colored output with game context, expected responses, and deadlines.
"""

from __future__ import annotations
import sys
from datetime import datetime, timedelta
from typing import Optional

from .protocol_display import (
    GREEN, ORANGE, RED, RESET,
    RECEIVE_DISPLAY_NAMES, SEND_DISPLAY_NAMES,
    EXPECTED_RESPONSES, DEFAULT_DEADLINES, CALLBACK_DISPLAY_NAMES,
)


class ProtocolLogger:
    """Logger for protocol messages and callbacks."""

    def __init__(self, role_active: bool = False):
        # Default to INACTIVE - only ACTIVE when assigned to current round
        self.role_active = role_active
        self._current_game_id: str = "0000000"

    def set_game_id(self, game_id: str) -> None:
        """Set current game ID for logging context."""
        self._current_game_id = game_id or "0000000"

    def set_role_active(self, active: bool) -> None:
        """Set whether referee is active for current round."""
        self.role_active = active

    def _is_unknown_round(self, game_id: str) -> bool:
        """Check if game_id indicates unknown round (RR=99 in positions 2-3)."""
        if not game_id or len(game_id) < 4:
            return True
        return game_id[2:4] == "99"

    def _get_role(self, game_id: str = None) -> str:
        """Get role string. Empty if unknown round (99), else ACTIVE/INACTIVE."""
        gid = game_id or self._current_game_id
        if self._is_unknown_round(gid):
            return ""
        return "REFEREE-ACTIVE" if self.role_active else "REFEREE-INACTIVE"

    def _now(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _now_ms(self) -> str:
        return datetime.now().strftime("%H:%M:%S:%f")[:-3]

    def _deadline(self, seconds: int) -> str:
        if seconds <= 0:
            return "N/A"
        deadline_time = datetime.now() + timedelta(seconds=seconds)
        return deadline_time.strftime("%H:%M:%S")

    def log_received(
        self,
        email: str,
        message_type: str,
        deadline_seconds: int = 0,
        game_id: Optional[str] = None,
    ) -> None:
        """Log a received protocol message."""
        # Ensure no None values reach format strings
        gid = game_id or self._current_game_id or "0000000"
        email = email or "unknown"
        message_type = message_type or "UNKNOWN"
        display = RECEIVE_DISPLAY_NAMES.get(message_type, message_type)
        expected = EXPECTED_RESPONSES.get(message_type, "Unknown")
        deadline = self._deadline(deadline_seconds)

        role = self._get_role(gid)
        role_part = f"ROLE: {role}" if role else "ROLE:"
        line = (
            f"{GREEN}{self._now()} | GAME-ID: {gid:7} | RECEIVED | "
            f"from {email:30} | {display:20} | EXPECTED-RESPONSE: {expected:25} | "
            f"{role_part:24} | DEADLINE: {deadline}{RESET}"
        )
        print(line, file=sys.stdout)

    def log_sent(
        self,
        email: str,
        message_type: str,
        deadline_seconds: int = 0,
        game_id: Optional[str] = None,
    ) -> None:
        """Log a sent protocol message."""
        # Ensure no None values reach format strings
        gid = game_id or self._current_game_id or "0000000"
        email = email or "unknown"
        message_type = message_type or "UNKNOWN"
        display = SEND_DISPLAY_NAMES.get(message_type, message_type)
        expected = EXPECTED_RESPONSES.get(message_type, "Unknown")
        deadline = self._deadline(deadline_seconds or DEFAULT_DEADLINES.get(message_type, 0))

        role = self._get_role(gid)
        role_part = f"ROLE: {role}" if role else "ROLE:"
        line = (
            f"{GREEN}{self._now()} | GAME-ID: {gid:7} | SENT     | "
            f"to   {email:30} | {display:20} | EXPECTED-RESPONSE: {expected:25} | "
            f"{role_part:24} | DEADLINE: {deadline}{RESET}"
        )
        print(line, file=sys.stdout)

    def log_callback_call(self, callback_name: str) -> None:
        """Log a callback invocation."""
        callback_name = callback_name or "unknown"
        display = CALLBACK_DISPLAY_NAMES.get(callback_name, callback_name)
        line = (
            f"{ORANGE}{self._now_ms()} | CALLBACK: {display:20} | "
            f"CALL     | ROLE: REFEREE{RESET}"
        )
        print(line, file=sys.stdout)

    def log_callback_response(self, callback_name: str) -> None:
        """Log a callback response."""
        callback_name = callback_name or "unknown"
        display = CALLBACK_DISPLAY_NAMES.get(callback_name, callback_name)
        line = (
            f"{ORANGE}{self._now_ms()} | CALLBACK: {display:20} | "
            f"RESPONSE | ROLE: REFEREE{RESET}"
        )
        print(line, file=sys.stdout)

    def log_error(self, description: str) -> None:
        """Log an error."""
        line = f"{RED}[ERROR] {self._now()} | {description}{RESET}"
        print(line, file=sys.stderr)


# Global singleton instance
_protocol_logger: Optional[ProtocolLogger] = None


def get_protocol_logger() -> ProtocolLogger:
    """Get or create the global protocol logger instance."""
    global _protocol_logger
    if _protocol_logger is None:
        _protocol_logger = ProtocolLogger()
    return _protocol_logger

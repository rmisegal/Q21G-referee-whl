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
from datetime import datetime, timezone, timedelta
from typing import Optional

# ══════════════════════════════════════════════════════════════
# ANSI COLOR CODES
# ══════════════════════════════════════════════════════════════

GREEN = "\033[32m"       # Protocol messages
ORANGE = "\033[38;5;208m"  # Callbacks
RED = "\033[31m"         # Errors
RESET = "\033[0m"

# ══════════════════════════════════════════════════════════════
# MESSAGE TYPE → DISPLAY NAME MAPPINGS (Referee)
# ══════════════════════════════════════════════════════════════

# Messages referee RECEIVES
RECEIVE_DISPLAY_NAMES = {
    "BROADCAST_START_SEASON": "START-SEASON",
    "SEASON_REGISTRATION_RESPONSE": "SIGNUP-RESPONSE",
    "BROADCAST_ASSIGNMENT_TABLE": "ASSIGNMENT-TABLE",
    "BROADCAST_NEW_LEAGUE_ROUND": "START-ROUND",
    "Q21WARMUPRESPONSE": "PING-RESPONSE",
    "Q21_WARMUP_RESPONSE": "PING-RESPONSE",
    "Q21QUESTIONSBATCH": "ASK-20-QUESTIONS",
    "Q21_QUESTIONS_BATCH": "ASK-20-QUESTIONS",
    "Q21GUESSSUBMISSION": "MY-GUESS",
    "Q21_GUESS_SUBMISSION": "MY-GUESS",
    "LEAGUE_COMPLETED": "SEASON-ENDED",
}

# Messages referee SENDS
SEND_DISPLAY_NAMES = {
    "SEASON_REGISTRATION_REQUEST": "SEASON-SIGNUP",
    "Q21WARMUPCALL": "PING-CALL",
    "Q21ROUNDSTART": "START-GAME",
    "Q21ANSWERSBATCH": "QUESTION-ANSWERS",
    "Q21SCOREFEEDBACK": "ROUND-SCORE-REPORT",
    "MATCH_RESULT_REPORT": "SEASON-RESULTS",
}

# Expected response for each received message type
EXPECTED_RESPONSES = {
    "BROADCAST_START_SEASON": "SEASON-SIGNUP",
    "SEASON_REGISTRATION_RESPONSE": "Wait for ASSIGNMENT-TABLE",
    "BROADCAST_ASSIGNMENT_TABLE": "Wait for START-ROUND",
    "BROADCAST_NEW_LEAGUE_ROUND": "Send PING-CALL",
    "Q21WARMUPRESPONSE": "Wait for both, then START-GAME",
    "Q21_WARMUP_RESPONSE": "Wait for both, then START-GAME",
    "Q21QUESTIONSBATCH": "QUESTION-ANSWERS",
    "Q21_QUESTIONS_BATCH": "QUESTION-ANSWERS",
    "Q21GUESSSUBMISSION": "ROUND-SCORE-REPORT",
    "Q21_GUESS_SUBMISSION": "ROUND-SCORE-REPORT",
    "LEAGUE_COMPLETED": "None (terminal)",
    # Sent messages
    "SEASON_REGISTRATION_REQUEST": "SIGNUP-RESPONSE",
    "Q21WARMUPCALL": "PING-RESPONSE",
    "Q21ROUNDSTART": "ASK-20-QUESTIONS",
    "Q21ANSWERSBATCH": "MY-GUESS",
    "Q21SCOREFEEDBACK": "None (terminal)",
    "MATCH_RESULT_REPORT": "None",
}

# Default deadline in seconds per message type
DEFAULT_DEADLINES = {
    "Q21WARMUPCALL": 120,
    "Q21ROUNDSTART": 300,
    "Q21ANSWERSBATCH": 120,
    "Q21SCOREFEEDBACK": 0,
}

# Callback internal name → display name
CALLBACK_DISPLAY_NAMES = {
    "warmup_question": "generate_warmup",
    "round_start_info": "select_book",
    "answers": "answer_questions",
    "score_feedback": "calculate_score",
}


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

    def _get_role(self) -> str:
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
        gid = game_id or self._current_game_id
        display = RECEIVE_DISPLAY_NAMES.get(message_type, message_type)
        expected = EXPECTED_RESPONSES.get(message_type, "Unknown")
        deadline = self._deadline(deadline_seconds)

        line = (
            f"{GREEN}{self._now()} | GAME-ID: {gid:7} | RECEIVED | "
            f"from {email:30} | {display:20} | EXPECTED-RESPONSE: {expected:25} | "
            f"ROLE: {self._get_role()} | DEADLINE: {deadline}{RESET}"
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
        gid = game_id or self._current_game_id
        display = SEND_DISPLAY_NAMES.get(message_type, message_type)
        expected = EXPECTED_RESPONSES.get(message_type, "Unknown")
        deadline = self._deadline(deadline_seconds or DEFAULT_DEADLINES.get(message_type, 0))

        line = (
            f"{GREEN}{self._now()} | GAME-ID: {gid:7} | SENT     | "
            f"to   {email:30} | {display:20} | EXPECTED-RESPONSE: {expected:25} | "
            f"ROLE: {self._get_role()} | DEADLINE: {deadline}{RESET}"
        )
        print(line, file=sys.stdout)

    def log_callback_call(self, callback_name: str) -> None:
        """Log a callback invocation."""
        display = CALLBACK_DISPLAY_NAMES.get(callback_name, callback_name)
        line = (
            f"{ORANGE}{self._now_ms()} | CALLBACK: {display:20} | "
            f"CALL     | ROLE: REFEREE{RESET}"
        )
        print(line, file=sys.stdout)

    def log_callback_response(self, callback_name: str) -> None:
        """Log a callback response."""
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

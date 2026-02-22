# Area: Shared
# PRD: docs/LOGGER_OUTPUT_REFEREE.md
"""
q21_referee._shared.protocol_display — Display constants for protocol logging
=============================================================================

ANSI color codes and message type display name mappings
used by ProtocolLogger for structured output.
"""

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
    "RESPONSE_GROUP_ASSIGNMENT": "ASSIGNMENT-ACK",
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
    "RESPONSE_GROUP_ASSIGNMENT": "Wait for START-ROUND",
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

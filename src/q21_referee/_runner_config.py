# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee._runner_config — Runner Configuration
==================================================

Configuration validation and constants for RefereeRunner.
"""

import logging

logger = logging.getLogger("q21_referee")

# Message types the referee cares about
INCOMING_MESSAGE_TYPES = {
    # League Manager broadcasts
    "BROADCAST_START_SEASON",
    "SEASON_REGISTRATION_RESPONSE",
    "BROADCAST_ASSIGNMENT_TABLE",
    "BROADCAST_NEW_LEAGUE_ROUND",
    "BROADCAST_END_LEAGUE_ROUND",
    "BROADCAST_END_SEASON",
    "BROADCAST_KEEP_ALIVE",
    "BROADCAST_CRITICAL_PAUSE",
    "BROADCAST_CRITICAL_RESET",
    "BROADCAST_ROUND_RESULTS",
    # Player messages (protocol: no underscores, but accept both for compatibility)
    "Q21WARMUPRESPONSE",
    "Q21_WARMUP_RESPONSE",
    "Q21QUESTIONSBATCH",
    "Q21_QUESTIONS_BATCH",
    "Q21GUESSSUBMISSION",
    "Q21_GUESS_SUBMISSION",
    # End
    "LEAGUE_COMPLETED",
}

# Required config keys (OAuth credentials loaded from env vars if not in config)
REQUIRED_CONFIG_KEYS = [
    "referee_id",
    "league_manager_email",
]


def validate_config(config: dict) -> None:
    """
    Validate required configuration keys.

    Args:
        config: Configuration dict

    Raises:
        ValueError: If required keys are missing
    """
    missing = [k for k in REQUIRED_CONFIG_KEYS if k not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")


def is_lm_message(message_type: str) -> bool:
    """Check if message is from League Manager."""
    return message_type.startswith("BROADCAST_") or message_type == "SEASON_REGISTRATION_RESPONSE"


def is_player_message(message_type: str) -> bool:
    """Check if message is from a player."""
    return message_type in {
        "Q21WARMUPRESPONSE",
        "Q21_WARMUP_RESPONSE",
        "Q21QUESTIONSBATCH",
        "Q21_QUESTIONS_BATCH",
        "Q21GUESSSUBMISSION",
        "Q21_GUESS_SUBMISSION",
    }

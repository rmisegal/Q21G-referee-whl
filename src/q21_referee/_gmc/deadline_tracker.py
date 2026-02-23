# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.deadline_tracker — Player response deadline tracking
=====================================================================

Tracks per-player deadlines for game phases (warmup, questions, scoring).
When the referee sends a message, a deadline is set. If the player doesn't
respond before it expires, the game can be aborted.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List

logger = logging.getLogger("q21_referee.deadline_tracker")


class DeadlineTracker:
    """
    Tracks player response deadlines keyed by player email.

    Each deadline stores the phase it was set for, the player email,
    and the monotonic timestamp at which it expires.
    """

    def __init__(self) -> None:
        self._deadlines: Dict[str, dict] = {}

    def set_deadline(
        self, phase: str, player_email: str, deadline_seconds: float
    ) -> None:
        """Set (or overwrite) a deadline for a player."""
        expires_at = time.monotonic() + deadline_seconds
        self._deadlines[player_email] = {
            "phase": phase,
            "player_email": player_email,
            "expires_at": expires_at,
        }
        logger.debug(
            "Deadline set: %s for %s (%.1fs)",
            phase, player_email, deadline_seconds,
        )

    def check_expired(self) -> List[dict]:
        """
        Return list of expired deadlines and remove them from tracking.

        Each returned dict contains 'phase' and 'player_email'.
        """
        now = time.monotonic()
        expired: List[dict] = []

        expired_keys: List[str] = []
        for email, entry in self._deadlines.items():
            if now >= entry["expires_at"]:
                expired.append({
                    "phase": entry["phase"],
                    "player_email": entry["player_email"],
                })
                expired_keys.append(email)

        for key in expired_keys:
            del self._deadlines[key]

        if expired:
            logger.info("Expired deadlines: %s", expired)

        return expired

    def cancel(self, player_email: str) -> None:
        """Cancel a player's deadline. No-op if not found."""
        if player_email in self._deadlines:
            logger.debug("Deadline cancelled for %s", player_email)
            del self._deadlines[player_email]

    def clear(self) -> None:
        """Remove all tracked deadlines."""
        self._deadlines.clear()
        logger.debug("All deadlines cleared")

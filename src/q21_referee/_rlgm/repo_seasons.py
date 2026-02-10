# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.repo_seasons — Seasons Repository
====================================================

Repository for managing referee_seasons table operations.
Tracks season registration and lifecycle status.
"""

from typing import Any, Dict, List, Optional
from .database import BaseRepository


class SeasonRepository(BaseRepository):
    """
    Repository for referee_seasons table.

    Handles saving, retrieving, and updating season records.
    """

    def save_season(
        self, season_id: str, league_id: str, status: str = "pending"
    ) -> None:
        """
        Save a new season record.

        Args:
            season_id: Unique season identifier
            league_id: League identifier
            status: Initial status (default: pending)
        """
        query = """
            INSERT OR REPLACE INTO referee_seasons
            (season_id, league_id, status)
            VALUES (?, ?, ?)
        """
        self._execute(query, (season_id, league_id, status))

    def get_season(self, season_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a season by ID.

        Args:
            season_id: Season identifier to look up

        Returns:
            Season record dict or None if not found
        """
        query = "SELECT * FROM referee_seasons WHERE season_id = ?"
        return self._execute_one(query, (season_id,))

    def update_status(self, season_id: str, status: str) -> None:
        """
        Update a season's status.

        Args:
            season_id: Season identifier
            status: New status value
        """
        query = "UPDATE referee_seasons SET status = ? WHERE season_id = ?"
        self._execute(query, (status, season_id))

    def get_all_seasons(self) -> List[Dict[str, Any]]:
        """
        Get all seasons.

        Returns:
            List of all season records
        """
        query = "SELECT * FROM referee_seasons ORDER BY created_at DESC"
        return self._execute(query, fetch=True) or []

    def mark_registered(self, season_id: str) -> None:
        """Mark season as registered."""
        query = """
            UPDATE referee_seasons
            SET status = 'registered', registered_at = CURRENT_TIMESTAMP
            WHERE season_id = ?
        """
        self._execute(query, (season_id,))

    def mark_completed(self, season_id: str) -> None:
        """Mark season as completed."""
        query = """
            UPDATE referee_seasons
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE season_id = ?
        """
        self._execute(query, (season_id,))

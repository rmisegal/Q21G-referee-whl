# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.repo_assignments — Assignments Repository
===========================================================

Repository for managing round_assignments table operations.
Tracks match assignments for each round in a season.
"""

from typing import Any, Dict, List, Optional
from .database import BaseRepository


class AssignmentRepository(BaseRepository):
    """
    Repository for round_assignments table.

    Handles saving, retrieving, and updating assignment records.
    """

    def save_assignment(self, assignment: Dict[str, Any]) -> None:
        """
        Save a single assignment.

        Args:
            assignment: Assignment data dict
        """
        query = """
            INSERT OR REPLACE INTO round_assignments
            (season_id, round_number, round_id, match_id, group_id,
             player1_id, player1_email, player2_id, player2_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(query, (
            assignment["season_id"],
            assignment["round_number"],
            assignment["round_id"],
            assignment["match_id"],
            assignment["group_id"],
            assignment["player1_id"],
            assignment["player1_email"],
            assignment["player2_id"],
            assignment["player2_email"],
        ))

    def save_assignments(self, assignments: List[Dict[str, Any]]) -> None:
        """
        Save multiple assignments.

        Args:
            assignments: List of assignment data dicts
        """
        for assignment in assignments:
            self.save_assignment(assignment)

    def get_assignment(
        self, season_id: str, round_number: int, match_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific assignment.

        Args:
            season_id: Season identifier
            round_number: Round number
            match_id: Match identifier

        Returns:
            Assignment record or None
        """
        query = """
            SELECT * FROM round_assignments
            WHERE season_id = ? AND round_number = ? AND match_id = ?
        """
        return self._execute_one(query, (season_id, round_number, match_id))

    def get_assignments_for_round(
        self, season_id: str, round_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get all assignments for a round.

        Args:
            season_id: Season identifier
            round_number: Round number

        Returns:
            List of assignment records
        """
        query = """
            SELECT * FROM round_assignments
            WHERE season_id = ? AND round_number = ?
        """
        return self._execute(query, (season_id, round_number), fetch=True) or []

    def get_all_assignments(self, season_id: str) -> List[Dict[str, Any]]:
        """Get all assignments for a season."""
        query = "SELECT * FROM round_assignments WHERE season_id = ?"
        return self._execute(query, (season_id,), fetch=True) or []

    def update_status(self, season_id: str, match_id: str, status: str) -> None:
        """Update assignment status."""
        query = """
            UPDATE round_assignments SET status = ?
            WHERE season_id = ? AND match_id = ?
        """
        self._execute(query, (status, season_id, match_id))

    def mark_completed(self, season_id: str, match_id: str) -> None:
        """Mark assignment as completed."""
        query = """
            UPDATE round_assignments
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE season_id = ? AND match_id = ?
        """
        self._execute(query, (season_id, match_id))

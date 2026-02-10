# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.repo_broadcasts — Broadcasts Repository
=========================================================

Repository for managing broadcasts_received table operations.
Used for idempotency checking to prevent duplicate processing.
"""

from typing import Any, Dict, List, Optional
from .database import BaseRepository


class BroadcastRepository(BaseRepository):
    """
    Repository for broadcasts_received table.

    Handles saving and checking broadcast processing status
    for idempotency.
    """

    def save_broadcast(self, broadcast_id: str, message_type: str) -> None:
        """
        Save a processed broadcast.

        Args:
            broadcast_id: Unique broadcast identifier
            message_type: Type of broadcast message
        """
        query = """
            INSERT OR IGNORE INTO broadcasts_received
            (broadcast_id, message_type)
            VALUES (?, ?)
        """
        self._execute(query, (broadcast_id, message_type))

    def is_processed(self, broadcast_id: str) -> bool:
        """
        Check if a broadcast has been processed.

        Args:
            broadcast_id: Broadcast identifier to check

        Returns:
            True if already processed, False otherwise
        """
        query = "SELECT 1 FROM broadcasts_received WHERE broadcast_id = ?"
        result = self._execute_one(query, (broadcast_id,))
        return result is not None

    def get_broadcast(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        """
        Get broadcast record by ID.

        Args:
            broadcast_id: Broadcast identifier

        Returns:
            Broadcast record or None
        """
        query = "SELECT * FROM broadcasts_received WHERE broadcast_id = ?"
        return self._execute_one(query, (broadcast_id,))

    def get_broadcasts_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """
        Get all broadcasts of a specific type.

        Args:
            message_type: Message type to filter by

        Returns:
            List of broadcast records
        """
        query = """
            SELECT * FROM broadcasts_received
            WHERE message_type = ?
            ORDER BY received_at DESC
        """
        return self._execute(query, (message_type,), fetch=True) or []

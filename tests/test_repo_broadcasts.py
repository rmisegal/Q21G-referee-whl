# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for Broadcasts Repository."""

import pytest
import tempfile
import os
from q21_referee._rlgm.repo_broadcasts import BroadcastRepository
from q21_referee._rlgm.database import init_database


class TestBroadcastRepository:
    """Tests for BroadcastRepository class."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_database(path)
        yield path
        os.unlink(path)

    @pytest.fixture
    def repo(self, db_path):
        """Create repository with test database."""
        return BroadcastRepository(db_path)

    def test_save_broadcast(self, repo):
        """Test saving a broadcast."""
        repo.save_broadcast("BC001", "BROADCAST_START_SEASON")

        assert repo.is_processed("BC001") is True

    def test_is_processed_true(self, repo):
        """Test is_processed returns True for processed broadcast."""
        repo.save_broadcast("BC001", "BROADCAST_START_SEASON")

        assert repo.is_processed("BC001") is True

    def test_is_processed_false(self, repo):
        """Test is_processed returns False for unknown broadcast."""
        assert repo.is_processed("UNKNOWN") is False

    def test_get_broadcast(self, repo):
        """Test retrieving broadcast record."""
        repo.save_broadcast("BC001", "BROADCAST_START_SEASON")

        broadcast = repo.get_broadcast("BC001")

        assert broadcast is not None
        assert broadcast["broadcast_id"] == "BC001"
        assert broadcast["message_type"] == "BROADCAST_START_SEASON"
        assert broadcast["processed"] == 1

    def test_get_broadcasts_by_type(self, repo):
        """Test retrieving broadcasts by message type."""
        repo.save_broadcast("BC001", "BROADCAST_START_SEASON")
        repo.save_broadcast("BC002", "BROADCAST_START_SEASON")
        repo.save_broadcast("BC003", "BROADCAST_END_SEASON")

        start_broadcasts = repo.get_broadcasts_by_type("BROADCAST_START_SEASON")
        end_broadcasts = repo.get_broadcasts_by_type("BROADCAST_END_SEASON")

        assert len(start_broadcasts) == 2
        assert len(end_broadcasts) == 1

    def test_duplicate_broadcast_ignored(self, repo):
        """Test that duplicate broadcasts are handled gracefully."""
        repo.save_broadcast("BC001", "BROADCAST_START_SEASON")
        repo.save_broadcast("BC001", "BROADCAST_START_SEASON")  # Duplicate

        # Should still only have one record
        broadcasts = repo.get_broadcasts_by_type("BROADCAST_START_SEASON")
        assert len(broadcasts) == 1

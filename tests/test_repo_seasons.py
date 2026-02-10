# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for Seasons Repository."""

import pytest
import tempfile
import os
from q21_referee._rlgm.repo_seasons import SeasonRepository
from q21_referee._rlgm.database import init_database


class TestSeasonRepository:
    """Tests for SeasonRepository class."""

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
        return SeasonRepository(db_path)

    def test_save_season(self, repo):
        """Test saving a new season."""
        repo.save_season(
            season_id="SEASON_2026_Q1",
            league_id="LEAGUE001",
            status="registered",
        )

        season = repo.get_season("SEASON_2026_Q1")
        assert season is not None
        assert season["season_id"] == "SEASON_2026_Q1"
        assert season["league_id"] == "LEAGUE001"
        assert season["status"] == "registered"

    def test_get_season_by_id(self, repo):
        """Test retrieving a season by ID."""
        repo.save_season("SEASON_A", "LEAGUE001", "pending")
        repo.save_season("SEASON_B", "LEAGUE001", "active")

        season_a = repo.get_season("SEASON_A")
        season_b = repo.get_season("SEASON_B")

        assert season_a["season_id"] == "SEASON_A"
        assert season_b["season_id"] == "SEASON_B"
        assert season_b["status"] == "active"

    def test_get_season_not_found(self, repo):
        """Test retrieving non-existent season returns None."""
        season = repo.get_season("NONEXISTENT")
        assert season is None

    def test_update_status(self, repo):
        """Test updating season status."""
        repo.save_season("SEASON_2026_Q1", "LEAGUE001", "pending")

        repo.update_status("SEASON_2026_Q1", "active")

        season = repo.get_season("SEASON_2026_Q1")
        assert season["status"] == "active"

    def test_update_status_nonexistent(self, repo):
        """Test updating non-existent season does not raise."""
        # Should not raise, just do nothing
        repo.update_status("NONEXISTENT", "active")

    def test_get_all_seasons(self, repo):
        """Test retrieving all seasons."""
        repo.save_season("SEASON_A", "LEAGUE001", "completed")
        repo.save_season("SEASON_B", "LEAGUE001", "active")

        seasons = repo.get_all_seasons()

        assert len(seasons) == 2
        season_ids = [s["season_id"] for s in seasons]
        assert "SEASON_A" in season_ids
        assert "SEASON_B" in season_ids

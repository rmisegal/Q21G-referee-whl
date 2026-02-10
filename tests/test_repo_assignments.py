# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for Assignments Repository."""

import pytest
import tempfile
import os
from q21_referee._rlgm.repo_assignments import AssignmentRepository
from q21_referee._rlgm.database import init_database


class TestAssignmentRepository:
    """Tests for AssignmentRepository class."""

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
        return AssignmentRepository(db_path)

    def create_assignment(self, round_number=1, match_id="R1M1"):
        """Create sample assignment dict."""
        return {
            "season_id": "SEASON_2026_Q1",
            "round_number": round_number,
            "round_id": f"ROUND_{round_number}",
            "match_id": match_id,
            "group_id": "GROUP_A",
            "player1_id": "P001",
            "player1_email": "p1@test.com",
            "player2_id": "P002",
            "player2_email": "p2@test.com",
        }

    def test_save_assignment(self, repo):
        """Test saving a new assignment."""
        assignment = self.create_assignment()
        repo.save_assignment(assignment)

        result = repo.get_assignment("SEASON_2026_Q1", 1, "R1M1")
        assert result is not None
        assert result["match_id"] == "R1M1"
        assert result["player1_id"] == "P001"

    def test_get_assignments_for_round(self, repo):
        """Test retrieving all assignments for a round."""
        repo.save_assignment(self.create_assignment(round_number=1, match_id="R1M1"))
        repo.save_assignment(self.create_assignment(round_number=1, match_id="R1M2"))
        repo.save_assignment(self.create_assignment(round_number=2, match_id="R2M1"))

        round_1 = repo.get_assignments_for_round("SEASON_2026_Q1", 1)
        round_2 = repo.get_assignments_for_round("SEASON_2026_Q1", 2)

        assert len(round_1) == 2
        assert len(round_2) == 1

    def test_update_status(self, repo):
        """Test updating assignment status."""
        repo.save_assignment(self.create_assignment())

        repo.update_status("SEASON_2026_Q1", "R1M1", "in_progress")

        assignment = repo.get_assignment("SEASON_2026_Q1", 1, "R1M1")
        assert assignment["status"] == "in_progress"

    def test_mark_completed(self, repo):
        """Test marking assignment as completed."""
        repo.save_assignment(self.create_assignment())

        repo.mark_completed("SEASON_2026_Q1", "R1M1")

        assignment = repo.get_assignment("SEASON_2026_Q1", 1, "R1M1")
        assert assignment["status"] == "completed"
        assert assignment["completed_at"] is not None

    def test_save_multiple_assignments(self, repo):
        """Test saving multiple assignments at once."""
        assignments = [
            self.create_assignment(round_number=1, match_id="R1M1"),
            self.create_assignment(round_number=1, match_id="R1M2"),
            self.create_assignment(round_number=2, match_id="R2M1"),
        ]

        repo.save_assignments(assignments)

        all_assignments = repo.get_all_assignments("SEASON_2026_Q1")
        assert len(all_assignments) == 3

# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_ROUND_RESULTS handler."""

import pytest
from unittest.mock import patch
from q21_referee._rlgm.handler_round_results import BroadcastRoundResultsHandler


class TestBroadcastRoundResultsHandler:
    """Tests for BroadcastRoundResultsHandler."""

    def create_handler(self):
        """Create handler."""
        return BroadcastRoundResultsHandler()

    def create_round_results_message(self):
        """Create sample round results message."""
        return {
            "message_type": "BROADCAST_ROUND_RESULTS",
            "broadcast_id": "RR001",
            "payload": {
                "round_number": 1,
                "round_id": "ROUND_1",
                "season_id": "SEASON_2026_Q1",
                "results": [
                    {
                        "match_id": "R1M1",
                        "winner_id": "P001",
                        "player1_score": 21,
                        "player2_score": 15,
                    },
                    {
                        "match_id": "R1M2",
                        "winner_id": None,
                        "player1_score": 18,
                        "player2_score": 18,
                    },
                ],
                "standings": [
                    {"player_id": "P001", "points": 3},
                    {"player_id": "P002", "points": 1},
                ],
            },
        }

    def test_logs_round_results(self):
        """Test that round results are logged."""
        handler = self.create_handler()
        message = self.create_round_results_message()

        with patch("q21_referee._rlgm.handler_round_results.logger") as mock_logger:
            handler.handle(message)
            mock_logger.info.assert_called()

    def test_stores_results_for_reference(self):
        """Test that results are stored for reference."""
        handler = self.create_handler()
        message = self.create_round_results_message()

        handler.handle(message)

        assert handler.last_round_number == 1
        assert handler.last_round_id == "ROUND_1"
        assert len(handler.last_results) == 2
        assert len(handler.last_standings) == 2

    def test_returns_none(self):
        """Test that handler returns None (no response needed)."""
        handler = self.create_handler()
        message = self.create_round_results_message()

        result = handler.handle(message)

        assert result is None

    def test_extracts_round_info(self):
        """Test that round info is correctly extracted."""
        handler = self.create_handler()
        message = self.create_round_results_message()

        handler.handle(message)

        assert handler.last_round_number == 1
        assert handler.last_round_id == "ROUND_1"

    def test_handles_empty_results(self):
        """Test handling message with empty results."""
        handler = self.create_handler()
        message = {
            "message_type": "BROADCAST_ROUND_RESULTS",
            "broadcast_id": "RR002",
            "payload": {
                "round_number": 2,
                "round_id": "ROUND_2",
                "results": [],
                "standings": [],
            },
        }

        handler.handle(message)

        assert handler.last_round_number == 2
        assert handler.last_results == []
        assert handler.last_standings == []

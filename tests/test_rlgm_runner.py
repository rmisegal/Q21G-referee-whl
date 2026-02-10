# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM Runner integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from q21_referee.rlgm_runner import RLGMRunner
from q21_referee.callbacks import RefereeAI
from q21_referee._rlgm.enums import RLGMState


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}

    def get_round_start_info(self, ctx):
        return {"book_name": "Test", "book_hint": "A test", "association_word": "test"}

    def get_answers(self, ctx):
        return {"answers": ["A", "B", "C"]}

    def get_score_feedback(self, ctx):
        return {"league_points": 10, "private_score": 5.0, "breakdown": {}}


class TestRLGMRunner:
    """Tests for RLGMRunner class."""

    def create_config(self):
        """Create sample config."""
        return {
            "referee_id": "REF001",
            "referee_email": "ref@test.com",
            "referee_password": "password",
            "group_id": "GROUP_A",
            "league_id": "LEAGUE001",
            "season_id": "SEASON_2026_Q1",
            "league_manager_email": "lm@test.com",
        }

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_rlgm_runner_creation(self, mock_email):
        """Test RLGM runner can be created."""
        config = self.create_config()
        ai = MockRefereeAI()

        runner = RLGMRunner(config=config, ai=ai)

        assert runner.orchestrator is not None
        assert runner.orchestrator.state_machine.current_state == RLGMState.INIT_START_STATE

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_lm_messages_routed_to_rlgm(self, mock_email):
        """Test that LM messages are routed to orchestrator."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        message = {
            "message_type": "BROADCAST_START_SEASON",
            "broadcast_id": "BC001",
            "payload": {"season_id": "SEASON_2026_Q1", "league_id": "LEAGUE001"},
        }

        outgoing = runner._route_message("BROADCAST_START_SEASON", message, "lm@test.com")

        # Should return registration request
        assert len(outgoing) == 1
        assert outgoing[0][0]["message_type"] == "SEASON_REGISTRATION_REQUEST"
        assert runner.orchestrator.state_machine.current_state == RLGMState.WAITING_FOR_CONFIRMATION

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_player_messages_routed_to_gmc(self, mock_email):
        """Test that player messages are routed to current game."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        # No game active, should return empty
        outgoing = runner._route_message(
            "Q21WARMUPRESPONSE",
            {"message_type": "Q21WARMUPRESPONSE", "payload": {}},
            "p1@test.com",
        )
        assert outgoing == []

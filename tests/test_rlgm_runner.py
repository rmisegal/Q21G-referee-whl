# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM Runner integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from q21_referee.rlgm_runner import RLGMRunner
from q21_referee.callbacks import RefereeAI
from q21_referee._rlgm.enums import RLGMState
from q21_referee._rlgm.runner_protocol_context import (
    update_context_before_routing,
    update_context_after_routing,
)


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


class TestProtocolLoggerContext:
    """Tests for protocol logger context updates in RLGMRunner."""

    def create_config(self, season_id="01"):
        """Create sample config."""
        return {
            "referee_id": "REF001",
            "referee_email": "ref@test.com",
            "referee_password": "password",
            "group_id": "GROUP_A",
            "league_id": "LEAGUE001",
            "season_id": season_id,
            "league_manager_email": "lm@test.com",
        }

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_season_level_message_uses_0199999(self, mock_email):
        """Test that season-level messages set game_id to 0199999."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        # BROADCAST_START_SEASON is season-level
        body = {"message_type": "BROADCAST_START_SEASON", "payload": {}}
        update_context_before_routing(
            runner.orchestrator, "BROADCAST_START_SEASON", body, runner._protocol_logger
        )

        assert runner._protocol_logger._current_game_id == "0199999"

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_season_registration_response_uses_0199999(self, mock_email):
        """Test that SEASON_REGISTRATION_RESPONSE sets game_id to 0199999."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        body = {"message_type": "SEASON_REGISTRATION_RESPONSE", "payload": {}}
        update_context_before_routing(
            runner.orchestrator, "SEASON_REGISTRATION_RESPONSE", body,
            runner._protocol_logger
        )

        assert runner._protocol_logger._current_game_id == "0199999"

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_assignment_table_uses_0199999(self, mock_email):
        """Test that BROADCAST_ASSIGNMENT_TABLE sets game_id to 0199999."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        body = {
            "message_type": "BROADCAST_ASSIGNMENT_TABLE",
            "payload": {"assignments": []},
        }
        update_context_before_routing(
            runner.orchestrator, "BROADCAST_ASSIGNMENT_TABLE", body,
            runner._protocol_logger
        )

        assert runner._protocol_logger._current_game_id == "0199999"

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_new_round_without_assignment_uses_round_format(self, mock_email):
        """Test BROADCAST_NEW_LEAGUE_ROUND with no assignment uses 01RR999."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        body = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "payload": {"round_number": 3},
        }
        update_context_before_routing(
            runner.orchestrator, "BROADCAST_NEW_LEAGUE_ROUND", body,
            runner._protocol_logger
        )

        # Format: 01 (season) + 03 (round) + 999 (no game)
        assert runner._protocol_logger._current_game_id == "0103999"
        # Not assigned, so inactive
        assert runner._protocol_logger.role_active is False

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_new_round_with_assignment_uses_game_id(self, mock_email):
        """Test BROADCAST_NEW_LEAGUE_ROUND with assignment uses assigned game_id."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        # Setup: add an assignment for round 2 via orchestrator's _assignments
        runner.orchestrator._assignments = [
            {"round_number": 2, "game_id": "0102001", "player1_email": "p1@test.com"}
        ]

        body = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "payload": {"round_number": 2},
        }
        update_context_before_routing(
            runner.orchestrator, "BROADCAST_NEW_LEAGUE_ROUND", body,
            runner._protocol_logger
        )

        assert runner._protocol_logger._current_game_id == "0102001"
        assert runner._protocol_logger.role_active is True

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_active_game_uses_gprm_game_id(self, mock_email):
        """Test that when a game is active, its GPRM game_id is used."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        # Setup: create a mock game with GPRM
        mock_game = Mock()
        mock_gprm = Mock()
        mock_gprm.game_id = "0105003"
        mock_game.gprm = mock_gprm
        runner.orchestrator.current_game = mock_game

        body = {"message_type": "Q21WARMUPRESPONSE", "payload": {}}
        update_context_before_routing(
            runner.orchestrator, "Q21WARMUPRESPONSE", body,
            runner._protocol_logger
        )

        assert runner._protocol_logger._current_game_id == "0105003"
        assert runner._protocol_logger.role_active is True

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_league_completed_uses_0199999(self, mock_email):
        """Test that LEAGUE_COMPLETED sets game_id to 0199999."""
        config = self.create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        body = {"message_type": "LEAGUE_COMPLETED", "payload": {}}
        update_context_before_routing(
            runner.orchestrator, "LEAGUE_COMPLETED", body,
            runner._protocol_logger
        )

        assert runner._protocol_logger._current_game_id == "0199999"

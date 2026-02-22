# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for protocol logger context updates in RLGMRunner."""

from unittest.mock import Mock, patch
from q21_referee.rlgm_runner import RLGMRunner
from q21_referee.callbacks import RefereeAI
from q21_referee._rlgm.runner_protocol_context import update_context_before_routing


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""
    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}
    def get_round_start_info(self, ctx):
        return {"book_name": "T", "book_hint": "A", "association_word": "t"}
    def get_answers(self, ctx):
        return {"answers": ["A", "B", "C"]}
    def get_score_feedback(self, ctx):
        return {"league_points": 10, "private_score": 5.0, "breakdown": {}}


def _make_runner(season_id="01"):
    """Create runner with patched EmailClient."""
    cfg = {
        "referee_id": "REF001", "referee_email": "ref@test.com",
        "referee_password": "pw", "group_id": "GROUP_A",
        "league_id": "LEAGUE001", "season_id": season_id,
        "league_manager_email": "lm@test.com",
    }
    return RLGMRunner(config=cfg, ai=MockRefereeAI())


def _route(runner, msg_type, body):
    """Helper to call update_context_before_routing."""
    update_context_before_routing(
        runner.orchestrator, msg_type, body, runner._protocol_logger)


class TestProtocolLoggerContext:
    """Tests for protocol logger context updates in RLGMRunner."""

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_season_level_message_uses_0199999(self, mock_email):
        runner = _make_runner()
        _route(runner, "BROADCAST_START_SEASON",
               {"message_type": "BROADCAST_START_SEASON", "payload": {}})
        assert runner._protocol_logger._current_game_id == "0199999"

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_season_registration_response_uses_0199999(self, mock_email):
        runner = _make_runner()
        _route(runner, "SEASON_REGISTRATION_RESPONSE",
               {"message_type": "SEASON_REGISTRATION_RESPONSE", "payload": {}})
        assert runner._protocol_logger._current_game_id == "0199999"

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_assignment_table_uses_0199999(self, mock_email):
        runner = _make_runner()
        body = {"message_type": "BROADCAST_ASSIGNMENT_TABLE",
                "payload": {"assignments": []}}
        _route(runner, "BROADCAST_ASSIGNMENT_TABLE", body)
        assert runner._protocol_logger._current_game_id == "0199999"

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_new_round_without_assignment_uses_round_format(self, mock_email):
        runner = _make_runner()
        body = {"message_type": "BROADCAST_NEW_LEAGUE_ROUND",
                "payload": {"round_number": 3}}
        _route(runner, "BROADCAST_NEW_LEAGUE_ROUND", body)
        assert runner._protocol_logger._current_game_id == "0103999"
        assert runner._protocol_logger.role_active is False

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_new_round_with_assignment_uses_game_id(self, mock_email):
        runner = _make_runner()
        runner.orchestrator._assignments = [
            {"round_number": 2, "game_id": "0102001",
             "player1_email": "p1@test.com"}
        ]
        body = {"message_type": "BROADCAST_NEW_LEAGUE_ROUND",
                "payload": {"round_number": 2}}
        _route(runner, "BROADCAST_NEW_LEAGUE_ROUND", body)
        assert runner._protocol_logger._current_game_id == "0102001"
        assert runner._protocol_logger.role_active is True

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_active_game_uses_gprm_game_id(self, mock_email):
        runner = _make_runner()
        mock_game = Mock()
        mock_gprm = Mock()
        mock_gprm.game_id = "0105003"
        mock_game.gprm = mock_gprm
        runner.orchestrator.current_game = mock_game
        body = {"message_type": "Q21WARMUPRESPONSE", "payload": {}}
        _route(runner, "Q21WARMUPRESPONSE", body)
        assert runner._protocol_logger._current_game_id == "0105003"
        assert runner._protocol_logger.role_active is True

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_league_completed_uses_0199999(self, mock_email):
        runner = _make_runner()
        _route(runner, "LEAGUE_COMPLETED",
               {"message_type": "LEAGUE_COMPLETED", "payload": {}})
        assert runner._protocol_logger._current_game_id == "0199999"

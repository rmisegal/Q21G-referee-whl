# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM Runner integration."""

from unittest.mock import Mock, patch
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


def create_config():
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


class TestRLGMRunner:
    """Tests for RLGMRunner class."""

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_rlgm_runner_creation(self, mock_email):
        """Test RLGM runner can be created."""
        config = create_config()
        ai = MockRefereeAI()

        runner = RLGMRunner(config=config, ai=ai)

        assert runner.orchestrator is not None
        assert runner.orchestrator.state_machine.current_state == RLGMState.INIT_START_STATE

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_lm_messages_routed_to_rlgm(self, mock_email):
        """Test that LM messages are routed to orchestrator."""
        config = create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        message = {
            "message_type": "BROADCAST_START_SEASON",
            "broadcast_id": "BC001",
            "payload": {"season_id": "SEASON_2026_Q1", "league_id": "LEAGUE001"},
        }

        outgoing = runner._route_message("BROADCAST_START_SEASON", message, "lm@test.com")

        assert len(outgoing) == 1
        assert outgoing[0][0]["message_type"] == "SEASON_REGISTRATION_REQUEST"
        assert runner.orchestrator.state_machine.current_state == RLGMState.WAITING_FOR_CONFIRMATION

    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_player_messages_routed_to_gmc(self, mock_email):
        """Test that player messages are routed to current game."""
        config = create_config()
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)

        outgoing = runner._route_message(
            "Q21WARMUPRESPONSE",
            {"message_type": "Q21WARMUPRESPONSE", "payload": {}},
            "p1@test.com",
        )
        assert outgoing == []


class TestSendMessages:
    """Tests for email send retry logic."""

    def create_runner(self):
        config = {
            "referee_id": "REF001", "referee_email": "ref@test.com",
            "group_id": "GROUP_A", "league_id": "LEAGUE001",
            "season_id": "S01", "league_manager_email": "lm@test.com",
        }
        ai = MockRefereeAI()
        runner = RLGMRunner(config=config, ai=ai)
        return runner

    @patch("q21_referee.rlgm_runner.time")
    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_send_failure_logged(self, mock_email_cls, mock_time):
        """Send failure is logged."""
        runner = self.create_runner()
        runner.email_client = Mock()
        runner.email_client.send.return_value = False

        envelope = {"message_type": "Q21WARMUPCALL"}
        runner._send_messages([(envelope, "SUBJ", "p1@test.com")])

        runner.email_client.send.assert_called_once()

    @patch("q21_referee.rlgm_runner.time")
    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_match_result_retried_on_failure(self, mock_email_cls, mock_time):
        """MATCH_RESULT_REPORT gets one retry on send failure."""
        runner = self.create_runner()
        runner.email_client = Mock()
        runner.email_client.send.side_effect = [False, True]

        envelope = {"message_type": "MATCH_RESULT_REPORT"}
        runner._send_messages([(envelope, "SUBJ", "lm@test.com")])

        assert runner.email_client.send.call_count == 2
        mock_time.sleep.assert_called_once_with(2)

    @patch("q21_referee.rlgm_runner.time")
    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_match_result_retry_success_no_error(self, mock_email_cls, mock_time):
        """MATCH_RESULT_REPORT retry succeeds - no error logged."""
        runner = self.create_runner()
        runner.email_client = Mock()
        runner.email_client.send.side_effect = [False, True]

        envelope = {"message_type": "MATCH_RESULT_REPORT"}
        runner._send_messages([(envelope, "SUBJ", "lm@test.com")])

        assert runner.email_client.send.call_count == 2

    @patch("q21_referee.rlgm_runner.time")
    @patch("q21_referee.rlgm_runner.EmailClient")
    def test_successful_send_no_retry(self, mock_email_cls, mock_time):
        """Successful send should not trigger retry."""
        runner = self.create_runner()
        runner.email_client = Mock()
        runner.email_client.send.return_value = True

        envelope = {"message_type": "MATCH_RESULT_REPORT"}
        runner._send_messages([(envelope, "SUBJ", "lm@test.com")])

        runner.email_client.send.assert_called_once()
        mock_time.sleep.assert_not_called()

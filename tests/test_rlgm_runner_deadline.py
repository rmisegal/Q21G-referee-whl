# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for deadline checking wired into the RLGM polling loop."""

from unittest.mock import Mock, patch, MagicMock
from q21_referee.rlgm_runner import RLGMRunner


def _make_runner():
    """Create an RLGMRunner with __init__ bypassed."""
    with patch.object(RLGMRunner, "__init__", lambda self: None):
        runner = RLGMRunner.__new__(RLGMRunner)
    runner.email_client = Mock()
    runner.orchestrator = Mock()
    runner._protocol_logger = Mock()
    runner._send_messages = Mock()
    return runner


class TestPollDeadlines:
    """Verify check_deadlines is called each poll cycle."""

    def test_poll_and_process_calls_check_deadlines(self):
        """check_deadlines is called once even when no emails arrive."""
        runner = _make_runner()
        runner.email_client.poll.return_value = []
        runner.orchestrator.check_deadlines.return_value = []

        runner._poll_and_process()

        runner.orchestrator.check_deadlines.assert_called_once()

    def test_poll_and_process_sends_deadline_abort_messages(self):
        """Abort messages from check_deadlines are forwarded via _send_messages."""
        runner = _make_runner()
        runner.email_client.poll.return_value = []
        abort_msg = (
            {"message_type": "MATCH_RESULT_REPORT"},
            "SUBJECT",
            "lm@test.com",
        )
        runner.orchestrator.check_deadlines.return_value = [abort_msg]

        runner._poll_and_process()

        runner._send_messages.assert_called_with([abort_msg])

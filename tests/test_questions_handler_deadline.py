# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for questions handler deadline setting after sending Q21ANSWERSBATCH."""

from unittest.mock import MagicMock, patch

from q21_referee._gmc.handlers.questions import handle_questions
from q21_referee._gmc.state import GamePhase, GameState, PlayerState
from q21_referee._gmc.deadline_tracker import DeadlineTracker


def _make_state():
    """Build a 2-player GameState in ROUND_STARTED phase."""
    return GameState(
        game_id="0101001",
        match_id="0101001",
        season_id="S01",
        league_id="Q21G",
        phase=GamePhase.ROUND_STARTED,
        player1=PlayerState(email="p1@test.com", participant_id="P1"),
        player2=PlayerState(email="p2@test.com", participant_id="P2"),
        auth_token="tok_123",
    )


def _make_ctx(state, deadline_tracker):
    """Build a mock HandlerContext with a real DeadlineTracker."""
    ctx = MagicMock()
    ctx.state = state
    ctx.sender_email = "p1@test.com"
    ctx.body = {
        "message_id": "msg-123",
        "payload": {"questions": [{"q": "What?"}]},
    }
    ctx.config = {"player_response_timeout_seconds": 40}
    ctx.deadline_tracker = deadline_tracker
    ctx.ai.get_answers.return_value = {"answers": ["A"]}
    ctx.builder.build_answers_batch.return_value = (
        {"message_id": "ans-1", "message_type": "Q21ANSWERSBATCH"},
        "Q21ANSWERSBATCH",
    )
    ctx.context_builder.build_answers_ctx.return_value = {}
    return ctx


class TestQuestionsHandlerSetsDeadlines:
    """Verify questions handler sets deadlines after sending Q21ANSWERSBATCH."""

    @patch("q21_referee._gmc.handlers.questions.execute_callback")
    def test_deadline_set_for_player(self, mock_exec):
        """After sending answers, a deadline is set for the player's guess."""
        mock_exec.return_value = {"answers": ["A"]}
        state = _make_state()
        base_time = 1000.0

        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            tracker = DeadlineTracker()
            ctx = _make_ctx(state, tracker)

            handle_questions(ctx)

            # Advance time past deadline
            mock_time.monotonic.return_value = base_time + 41.0
            expired = tracker.check_expired()

        assert len(expired) == 1
        assert expired[0]["player_email"] == "p1@test.com"
        assert expired[0]["phase"] == "guess"

    @patch("q21_referee._gmc.handlers.questions.execute_callback")
    def test_deadline_uses_config_timeout(self, mock_exec):
        """Deadline respects player_response_timeout_seconds from config."""
        mock_exec.return_value = {"answers": ["A"]}
        state = _make_state()
        base_time = 500.0

        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            tracker = DeadlineTracker()
            ctx = _make_ctx(state, tracker)
            ctx.config = {"player_response_timeout_seconds": 120}

            handle_questions(ctx)

            # At 119s — not yet expired
            mock_time.monotonic.return_value = base_time + 119.0
            expired_early = tracker.check_expired()
            assert len(expired_early) == 0

            # At 121s — expired
            mock_time.monotonic.return_value = base_time + 121.0
            expired_late = tracker.check_expired()
            assert len(expired_late) == 1

    @patch("q21_referee._gmc.handlers.questions.execute_callback")
    def test_deadline_uses_default_timeout(self, mock_exec):
        """Without config key, default timeout of 40s applies."""
        mock_exec.return_value = {"answers": ["A"]}
        state = _make_state()
        base_time = 100.0

        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            tracker = DeadlineTracker()
            ctx = _make_ctx(state, tracker)
            ctx.config = {}  # No timeout key

            handle_questions(ctx)

            # At 41s — expired with default 40s
            mock_time.monotonic.return_value = base_time + 41.0
            expired = tracker.check_expired()

        assert len(expired) == 1
        assert expired[0]["phase"] == "guess"

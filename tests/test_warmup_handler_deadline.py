# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup handler deadline setting after sending Q21ROUNDSTART."""

from unittest.mock import MagicMock, patch

from q21_referee._gmc.handlers.warmup import handle_warmup_response
from q21_referee._gmc.state import GamePhase, GameState, PlayerState
from q21_referee._gmc.deadline_tracker import DeadlineTracker


def _make_state():
    """Build a 2-player GameState in WARMUP_SENT phase, player2 already answered."""
    state = GameState(
        game_id="0101001",
        match_id="0101001",
        season_id="S01",
        league_id="Q21G",
        phase=GamePhase.WARMUP_SENT,
        player1=PlayerState(email="p1@test.com", participant_id="P1"),
        player2=PlayerState(email="p2@test.com", participant_id="P2"),
    )
    state.player2.warmup_answer = "yes"
    state.auth_token = "tok_123"
    return state


def _make_ctx(state, deadline_tracker):
    """Build a mock HandlerContext with a real DeadlineTracker."""
    ctx = MagicMock()
    ctx.state = state
    ctx.sender_email = "p1@test.com"
    ctx.body = {"payload": {"answer": "4"}}
    ctx.config = {"player_response_timeout_seconds": 40}
    ctx.deadline_tracker = deadline_tracker
    ctx.ai.get_round_start_info.return_value = {
        "book_name": "Test",
        "book_hint": "hint",
        "association_word": "word",
    }
    ctx.builder.build_round_start.return_value = (
        {"message_id": "msg-1", "message_type": "Q21ROUNDSTART"},
        "Q21ROUNDSTART",
    )
    ctx.context_builder.build_round_start_info_ctx.return_value = {}
    return ctx


class TestWarmupHandlerSetsDeadlines:
    """Verify warmup handler sets deadlines after sending Q21ROUNDSTART."""

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_deadlines_set_for_both_players(self, mock_exec):
        """After both warmups received, deadlines set for each player."""
        mock_exec.return_value = {
            "book_name": "Test",
            "book_hint": "hint",
            "association_word": "word",
        }
        state = _make_state()
        base_time = 1000.0

        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            tracker = DeadlineTracker()
            ctx = _make_ctx(state, tracker)

            handle_warmup_response(ctx)

            # Advance time past the 40s deadline
            mock_time.monotonic.return_value = base_time + 41.0
            expired = tracker.check_expired()

        assert len(expired) == 2
        expired_emails = {e["player_email"] for e in expired}
        assert expired_emails == {"p1@test.com", "p2@test.com"}
        assert all(e["phase"] == "questions" for e in expired)

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_deadlines_use_config_timeout(self, mock_exec):
        """Deadlines respect player_response_timeout_seconds from config."""
        mock_exec.return_value = {
            "book_name": "Test",
            "book_hint": "hint",
            "association_word": "word",
        }
        state = _make_state()
        base_time = 500.0

        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            tracker = DeadlineTracker()
            ctx = _make_ctx(state, tracker)
            ctx.config = {"player_response_timeout_seconds": 120}

            handle_warmup_response(ctx)

            # At 119s — not yet expired
            mock_time.monotonic.return_value = base_time + 119.0
            expired_early = tracker.check_expired()
            assert len(expired_early) == 0

            # At 121s — expired
            mock_time.monotonic.return_value = base_time + 121.0
            expired_late = tracker.check_expired()
            assert len(expired_late) == 2

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_deadlines_use_default_timeout(self, mock_exec):
        """Without config key, default timeout of 40s applies."""
        mock_exec.return_value = {
            "book_name": "Test",
            "book_hint": "hint",
            "association_word": "word",
        }
        state = _make_state()
        base_time = 100.0

        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            tracker = DeadlineTracker()
            ctx = _make_ctx(state, tracker)
            ctx.config = {}  # No timeout key

            handle_warmup_response(ctx)

            # At 41s — expired with default 40s
            mock_time.monotonic.return_value = base_time + 41.0
            expired = tracker.check_expired()

        assert len(expired) == 2
        assert all(e["phase"] == "questions" for e in expired)

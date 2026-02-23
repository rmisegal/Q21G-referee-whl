# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup handler resilience."""

from unittest.mock import Mock, patch
from q21_referee._gmc.handlers.warmup import handle_warmup_response
from q21_referee._gmc.state import GamePhase


def make_ctx(callback_raises=None):
    """Build a mock handler context with both warmups already received."""
    ctx = Mock()
    ctx.body = {"payload": {"answer": "4"}}
    ctx.sender_email = "p1@test.com"

    player = Mock()
    player.participant_id = "P001"
    player.warmup_answer = None
    ctx.state.get_player_by_email.return_value = player
    ctx.state.both_warmups_received.return_value = True
    ctx.state.player1 = player
    ctx.state.player2 = Mock(
        participant_id="P002", email="p2@test.com",
        questions_message_id=None,
    )
    ctx.state.active_players.return_value = [
        ctx.state.player1, ctx.state.player2,
    ]

    ctx.context_builder.build_round_start_info_ctx.return_value = {}

    if callback_raises:
        ctx.ai.get_round_start_info.side_effect = callback_raises
    else:
        ctx.ai.get_round_start_info.return_value = {
            "book_name": "Test", "book_hint": "Hint",
            "association_word": "word",
        }

    ctx.builder.build_round_start.return_value = (
        {"message_id": "msg1", "message_type": "Q21ROUNDSTART"},
        "SUBJECT",
    )
    ctx.state.game_id = "0101001"
    ctx.state.match_id = "0101001"
    ctx.state.auth_token = "tok_abc"
    ctx.state.phase = GamePhase.WARMUP_SENT

    return ctx


class TestWarmupHandlerResilience:
    """Tests for warmup handler callback failure."""

    @patch(
        "q21_referee._gmc.handlers.warmup.execute_callback",
        side_effect=ValueError("AI broke"),
    )
    def test_callback_failure_returns_empty(self, mock_exec):
        """If execute_callback raises, handler returns empty list."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_successful_callback_sends_round_start(self, mock_exec):
        """Normal flow: both players get Q21ROUNDSTART."""
        mock_exec.return_value = {
            "book_name": "Test", "book_hint": "Hint",
            "association_word": "word",
        }
        ctx = make_ctx()
        outgoing = handle_warmup_response(ctx)
        assert len(outgoing) == 2

    def test_unknown_player_returns_empty(self):
        """Unknown sender returns empty list."""
        ctx = make_ctx()
        ctx.state.get_player_by_email.return_value = None
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_waiting_for_other_player(self, mock_exec):
        """Only one warmup received: returns empty, no callback."""
        ctx = make_ctx()
        ctx.state.both_warmups_received.return_value = False
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []
        mock_exec.assert_not_called()

    @patch(
        "q21_referee._gmc.handlers.warmup.execute_callback",
        side_effect=TimeoutError("deadline exceeded"),
    )
    def test_timeout_error_returns_empty(self, mock_exec):
        """Timeout in callback also returns empty list."""
        ctx = make_ctx()
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []


class TestWarmupDuplicateAndPhaseGuards:
    """Tests for duplicate protection and phase guards."""

    def test_duplicate_warmup_returns_empty(self):
        """Second warmup from same player is silently rejected."""
        ctx = make_ctx()
        player = ctx.state.get_player_by_email.return_value
        player.warmup_answer = "already answered"
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    def test_wrong_phase_returns_empty(self):
        """Warmup response in wrong phase is rejected."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.ROUND_STARTED
        outgoing = handle_warmup_response(ctx)
        assert outgoing == []

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_correct_phase_processes(self, mock_exec):
        """Warmup response in WARMUP_SENT phase is accepted."""
        mock_exec.return_value = {
            "book_name": "Test", "book_hint": "Hint",
            "association_word": "word",
        }
        ctx = make_ctx()
        ctx.state.phase = GamePhase.WARMUP_SENT
        outgoing = handle_warmup_response(ctx)
        assert len(outgoing) == 2

# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup handler in single-player mode."""

from unittest.mock import MagicMock, patch

from q21_referee._gmc.handlers.warmup import handle_warmup_response
from q21_referee._gmc.state import GamePhase, GameState, PlayerState


def _make_single_player_state():
    """Build a GameState configured for single-player mode (player2 missing)."""
    state = GameState(
        game_id="0101001",
        match_id="0101001",
        season_id="S01",
        league_id="Q21G",
        phase=GamePhase.WARMUP_SENT,
        player1=PlayerState(email="p1@test.com", participant_id="P1"),
        player2=PlayerState(email="p2@test.com", participant_id="P2"),
        single_player_mode=True,
        missing_player_role="player2",
        missing_player_email="p2@test.com",
    )
    # Pre-fill missing player fields (as GMC._setup_single_player does)
    state.player2.warmup_answer = "ABSENT_MALFUNCTION"
    state.player2.answers_sent = True
    state.player2.score_sent = True
    state.player2.league_points = 1
    state.auth_token = "tok_123"
    return state


def _make_ctx(state):
    """Build a mock HandlerContext wrapping a real GameState."""
    ctx = MagicMock()
    ctx.state = state
    ctx.sender_email = "p1@test.com"
    ctx.body = {"payload": {"answer": "4"}}
    ctx.ai.get_round_start_info.return_value = {
        "book_name": "Test Book",
        "book_hint": "A hint",
        "association_word": "word",
    }
    ctx.builder.build_round_start.return_value = (
        {"message_id": "mid_rs", "message_type": "Q21ROUNDSTART"},
        "Q21ROUNDSTART",
    )
    ctx.context_builder.build_round_start_info_ctx.return_value = {}
    return ctx


class TestWarmupHandlerSinglePlayer:
    """Warmup handler must send Q21ROUNDSTART only to active players."""

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_round_start_sent_only_to_active_player(self, mock_exec):
        """In single-player mode, Q21ROUNDSTART goes only to player1."""
        mock_exec.return_value = {
            "book_name": "Test Book",
            "book_hint": "A hint",
            "association_word": "word",
        }
        state = _make_single_player_state()
        ctx = _make_ctx(state)

        outgoing = handle_warmup_response(ctx)

        assert len(outgoing) == 1
        # The single outgoing message is addressed to player1
        _env, _subject, recipient = outgoing[0]
        assert recipient == "p1@test.com"

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_missing_player_not_sent_round_start(self, mock_exec):
        """Player2 (absent) must NOT receive Q21ROUNDSTART."""
        mock_exec.return_value = {
            "book_name": "Test Book",
            "book_hint": "A hint",
            "association_word": "word",
        }
        state = _make_single_player_state()
        ctx = _make_ctx(state)

        outgoing = handle_warmup_response(ctx)

        recipients = [r for _, _, r in outgoing]
        assert "p2@test.com" not in recipients

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_phase_advances_to_round_started(self, mock_exec):
        """Phase should advance to ROUND_STARTED after sending."""
        mock_exec.return_value = {
            "book_name": "Test Book",
            "book_hint": "A hint",
            "association_word": "word",
        }
        state = _make_single_player_state()
        ctx = _make_ctx(state)

        handle_warmup_response(ctx)

        assert state.phase == GamePhase.ROUND_STARTED

    @patch("q21_referee._gmc.handlers.warmup.execute_callback")
    def test_two_player_mode_sends_to_both(self, mock_exec):
        """In normal (2-player) mode, both players get Q21ROUNDSTART."""
        mock_exec.return_value = {
            "book_name": "Test Book",
            "book_hint": "A hint",
            "association_word": "word",
        }
        state = _make_single_player_state()
        # Switch to normal 2-player mode
        state.single_player_mode = False
        state.missing_player_role = None
        state.missing_player_email = None
        # Player2 also completed warmup normally
        state.player2.warmup_answer = "5"
        ctx = _make_ctx(state)

        outgoing = handle_warmup_response(ctx)

        assert len(outgoing) == 2
        recipients = {r for _, _, r in outgoing}
        assert recipients == {"p1@test.com", "p2@test.com"}

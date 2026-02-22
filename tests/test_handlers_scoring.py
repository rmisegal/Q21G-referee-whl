# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for scoring handler resilience."""

from unittest.mock import Mock, patch
from q21_referee._gmc.handlers.scoring import handle_guess
from q21_referee._gmc.state import GamePhase


def make_ctx(callback_raises=None):
    """Build a mock handler context."""
    ctx = Mock()
    ctx.body = {"payload": {"guess": "BookX"}, "message_id": "msg_in"}
    ctx.sender_email = "p1@test.com"

    player = Mock()
    player.participant_id = "P001"
    player.email = "p1@test.com"
    player.guess = None
    player.score_sent = False
    player.league_points = 0
    player.private_score = 0.0
    player.feedback = None
    ctx.state.get_player_by_email.return_value = player
    ctx.state.both_scores_sent.return_value = False

    ctx.context_builder.build_score_feedback_ctx.return_value = {}

    if callback_raises:
        ctx.ai.get_score_feedback.side_effect = callback_raises
    else:
        ctx.ai.get_score_feedback.return_value = {
            "league_points": 10, "private_score": 5.0,
            "breakdown": {}, "feedback": "good",
        }

    ctx.builder.build_score_feedback.return_value = (
        {"message_id": "msg_out", "message_type": "Q21SCOREFEEDBACK"},
        "SUBJ",
    )
    ctx.state.game_id = "0101001"
    ctx.state.match_id = "0101001"
    ctx.state.phase = GamePhase.ANSWERS_SENT

    return ctx


class TestScoringHandlerResilience:
    """Tests for scoring handler callback failure."""

    @patch(
        "q21_referee._gmc.handlers.scoring.execute_callback",
        side_effect=ValueError("AI broke"),
    )
    def test_callback_failure_sends_zero_score(self, mock_exec):
        """If execute_callback raises, send zero-score feedback."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        outgoing = handle_guess(ctx)

        # Should still send feedback (with zero scores)
        assert len(outgoing) == 1
        # Player should be marked as scored
        player = ctx.state.get_player_by_email.return_value
        assert player.score_sent is True
        assert player.league_points == 0
        assert player.private_score == 0.0

    @patch("q21_referee._gmc.handlers.scoring.execute_callback")
    def test_successful_callback_sends_score(self, mock_exec):
        """Normal flow: player gets score feedback."""
        mock_exec.return_value = {
            "league_points": 10, "private_score": 5.0,
            "breakdown": {}, "feedback": "good",
        }
        ctx = make_ctx()
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1

    def test_unknown_player_returns_empty(self):
        """Unknown sender returns empty list."""
        ctx = make_ctx()
        ctx.state.get_player_by_email.return_value = None
        outgoing = handle_guess(ctx)
        assert outgoing == []

    @patch(
        "q21_referee._gmc.handlers.scoring.execute_callback",
        side_effect=TimeoutError("deadline exceeded"),
    )
    def test_timeout_error_sends_zero_score(self, mock_exec):
        """Timeout in callback also sends zero-score feedback."""
        ctx = make_ctx()
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1
        player = ctx.state.get_player_by_email.return_value
        assert player.score_sent is True
        assert player.league_points == 0
        assert player.private_score == 0.0

    @patch(
        "q21_referee._gmc.handlers.scoring.execute_callback",
        side_effect=ValueError("AI broke"),
    )
    def test_callback_failure_feedback_is_none(self, mock_exec):
        """Zero-score fallback sets feedback to None."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        handle_guess(ctx)
        player = ctx.state.get_player_by_email.return_value
        assert player.feedback is None


class TestScoringDuplicateAndPhaseGuards:
    """Tests for duplicate protection and phase guards."""

    def test_duplicate_guess_returns_empty(self):
        """Second guess from same player is rejected."""
        ctx = make_ctx()
        player = ctx.state.get_player_by_email.return_value
        player.score_sent = True
        outgoing = handle_guess(ctx)
        assert outgoing == []

    def test_wrong_phase_returns_empty(self):
        """Guess in wrong phase is rejected."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.WARMUP_SENT
        outgoing = handle_guess(ctx)
        assert outgoing == []

    def test_answers_sent_phase_accepted(self):
        """Guess in ANSWERS_SENT phase is accepted."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.ANSWERS_SENT
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1

    def test_guesses_collecting_phase_accepted(self):
        """Guess in GUESSES_COLLECTING phase is accepted."""
        ctx = make_ctx()
        ctx.state.phase = GamePhase.GUESSES_COLLECTING
        outgoing = handle_guess(ctx)
        assert len(outgoing) == 1

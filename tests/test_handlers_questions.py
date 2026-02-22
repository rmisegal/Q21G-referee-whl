# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for questions handler resilience."""

from unittest.mock import Mock, patch
from q21_referee._gmc.handlers.questions import handle_questions

VALID_ANSWERS = {"answers": [{"question_number": 1, "answer": "A"}]}


def make_ctx(callback_raises=None):
    """Build a mock handler context."""
    ctx = Mock()
    ctx.body = {"payload": {"questions": ["Q1"]}, "message_id": "msg_in"}
    ctx.sender_email = "p1@test.com"

    player = Mock()
    player.participant_id = "P001"
    player.questions = None
    player.answers_sent = False
    ctx.state.get_player_by_email.return_value = player
    ctx.state.both_answers_sent.return_value = False

    ctx.context_builder.build_answers_ctx.return_value = {}

    if callback_raises:
        ctx.ai.get_answers.side_effect = callback_raises
    else:
        ctx.ai.get_answers.return_value = VALID_ANSWERS

    ctx.builder.build_answers_batch.return_value = (
        {"message_id": "msg_out", "message_type": "Q21ANSWERSBATCH"}, "SUBJ",
    )
    ctx.state.game_id = "0101001"
    ctx.state.match_id = "0101001"
    ctx.state.auth_token = "tok_abc"

    return ctx


class TestQuestionsHandlerResilience:
    """Tests for questions handler callback failure."""

    def test_callback_failure_returns_empty(self):
        """If get_answers raises, handler returns empty."""
        ctx = make_ctx(callback_raises=ValueError("AI broke"))
        outgoing = handle_questions(ctx)
        assert outgoing == []

    def test_successful_callback_sends_answers(self):
        """Normal flow: player gets Q21ANSWERSBATCH."""
        ctx = make_ctx()
        outgoing = handle_questions(ctx)
        assert len(outgoing) == 1

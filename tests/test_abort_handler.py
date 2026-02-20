# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for abort_handler — resilient scoring during game abort."""

import pytest
from q21_referee._rlgm.abort_handler import score_player_on_abort
from q21_referee._rlgm.gprm import GPRM
from q21_referee._gmc.gmc import GameManagementCycle
from q21_referee.callbacks import RefereeAI


class FailingScoreAI(RefereeAI):
    """Mock AI whose get_score_feedback always raises."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}

    def get_round_start_info(self, ctx):
        return {
            "book_name": "Test",
            "book_hint": "A test book",
            "association_word": "test",
        }

    def get_answers(self, ctx):
        return {"answers": [{"question_number": 1, "answer": "A"}]}

    def get_score_feedback(self, ctx):
        raise RuntimeError("LLM service unavailable")


def _make_config():
    return {
        "referee_id": "REF001",
        "referee_email": "ref@test.com",
        "group_id": "GROUP_A",
        "league_id": "LEAGUE001",
        "season_id": "S01",
        "league_manager_email": "lm@test.com",
    }


def _make_gprm():
    return GPRM(
        player1_email="p1@test.com",
        player1_id="P001",
        player2_email="p2@test.com",
        player2_id="P002",
        season_id="S01",
        game_id="0101001",
        match_id="0101001",
        round_id="ROUND_1",
        round_number=1,
    )


def _make_gmc_with_guess(ai, config):
    """Create a GMC where player1 has submitted a guess."""
    gprm = _make_gprm()
    gmc = GameManagementCycle(gprm, ai, config)
    gmc.state.book_name = "Test Book"
    gmc.state.book_hint = "A test hint"
    gmc.state.association_word = "test"
    gmc.state.player1.guess = {
        "opening_sentence": "It was a dark night.",
        "sentence_justification": "Seemed fitting.",
        "associative_word": "dark",
        "word_justification": "Matches the mood.",
        "confidence": 0.5,
    }
    return gmc


class TestScorePlayerOnAbortResilience:
    """Test that score_player_on_abort survives callback failures."""

    def test_callback_failure_returns_score_feedback_with_defaults(self):
        """When AI callback raises, should still return Q21SCOREFEEDBACK
        with zero defaults instead of crashing."""
        ai = FailingScoreAI()
        config = _make_config()
        gmc = _make_gmc_with_guess(ai, config)
        player = gmc.state.player1

        result = score_player_on_abort(gmc, player, ai, config)

        # Should return exactly one (envelope, subject, recipient) tuple
        assert len(result) == 1
        env, subject, recipient = result[0]
        assert env["message_type"] == "Q21SCOREFEEDBACK"
        assert recipient == "p1@test.com"
        # Payload should have zero defaults
        assert env["payload"]["league_points"] == 0
        assert env["payload"]["private_score"] == 0.0

    def test_callback_failure_sets_player_state_defaults(self):
        """When AI callback raises, player state should get zero defaults."""
        ai = FailingScoreAI()
        config = _make_config()
        gmc = _make_gmc_with_guess(ai, config)
        player = gmc.state.player1

        score_player_on_abort(gmc, player, ai, config)

        assert player.league_points == 0
        assert player.private_score == 0.0
        assert player.score_sent is True

    def test_callback_success_uses_ai_result(self):
        """When AI callback succeeds, its values should be used."""

        class SuccessAI(FailingScoreAI):
            def get_score_feedback(self, ctx):
                return {
                    "league_points": 2,
                    "private_score": 65.0,
                    "breakdown": {
                        "opening_sentence_score": 70.0,
                        "sentence_justification_score": 60.0,
                        "associative_word_score": 60.0,
                        "word_justification_score": 60.0,
                    },
                    "feedback": {
                        "opening_sentence": " ".join(["word"] * 160),
                        "associative_word": " ".join(["word"] * 160),
                    },
                }

        ai = SuccessAI()
        config = _make_config()
        gmc = _make_gmc_with_guess(ai, config)
        player = gmc.state.player1

        result = score_player_on_abort(gmc, player, ai, config)

        env, subject, recipient = result[0]
        assert env["payload"]["league_points"] == 2
        assert player.league_points == 2
        assert player.private_score == 65.0
        assert player.score_sent is True

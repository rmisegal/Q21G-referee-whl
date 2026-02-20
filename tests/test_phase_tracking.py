# Area: GMC
# PRD: docs/prd-rlgm.md
"""
Tests for accurate phase tracking in questions and scoring handlers.
"""

import pytest
from unittest.mock import Mock, patch

from q21_referee._gmc.state import GameState, GamePhase, PlayerState
from q21_referee._gmc.handlers.questions import handle_questions
from q21_referee._gmc.handlers.scoring import handle_guess


class TestBothAnswersSent:
    """Tests for the both_answers_sent helper."""

    def test_both_sent(self):
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01")
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player2 = PlayerState(email="p2@test.com", participant_id="P002")
        state.player1.answers_sent = True
        state.player2.answers_sent = True
        assert state.both_answers_sent() is True

    def test_one_sent(self):
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01")
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player2 = PlayerState(email="p2@test.com", participant_id="P002")
        state.player1.answers_sent = True
        assert state.both_answers_sent() is False

    def test_none_player(self):
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01")
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player1.answers_sent = True
        assert state.both_answers_sent() is False


EXEC_CB = "q21_referee._gmc.handlers.questions.execute_callback"


class TestPhaseAfterQuestions:
    """Tests for phase progression after question handling."""

    def _make_ctx(self, state):
        """Build a minimal ctx mock for handle_questions."""
        ctx = Mock()
        ctx.state = state
        ctx.body = {
            "message_id": "MSG001",
            "payload": {"questions": [{"q": "test"}]},
        }
        ctx.sender_email = "p1@test.com"
        ctx.context_builder = Mock()
        ctx.context_builder.build_answers_ctx.return_value = {
            "dynamic": {}, "service": {},
        }
        ctx.ai = Mock()
        ctx.ai.get_answers.return_value = {"answers": [{"question_number": 1, "answer": "A"}]}
        ctx.builder = Mock()
        ctx.builder.build_answers_batch.return_value = (
            {"message_type": "Q21ANSWERSBATCH", "message_id": "ANS001"},
            "subject",
        )
        return ctx

    @patch(EXEC_CB, return_value={"answers": [{"question_number": 1, "answer": "A"}]})
    def test_first_player_sets_questions_collecting(self, mock_exec):
        """After first player's answers sent, phase should be QUESTIONS_COLLECTING."""
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01",
                          phase=GamePhase.ROUND_STARTED)
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player2 = PlayerState(email="p2@test.com", participant_id="P002")

        ctx = self._make_ctx(state)
        handle_questions(ctx)

        assert state.phase == GamePhase.QUESTIONS_COLLECTING

    @patch(EXEC_CB, return_value={"answers": [{"question_number": 1, "answer": "A"}]})
    def test_second_player_sets_answers_sent(self, mock_exec):
        """After both players' answers sent, phase should be ANSWERS_SENT."""
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01",
                          phase=GamePhase.QUESTIONS_COLLECTING)
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player1.answers_sent = True  # first player already done
        state.player2 = PlayerState(email="p2@test.com", participant_id="P002")

        ctx = self._make_ctx(state)
        ctx.sender_email = "p2@test.com"
        handle_questions(ctx)

        assert state.phase == GamePhase.ANSWERS_SENT


EXEC_CB_SCORING = "q21_referee._gmc.handlers.scoring.execute_callback"


class TestPhaseAfterScoring:
    """Tests for phase progression after scoring."""

    def _make_ctx(self, state):
        ctx = Mock()
        ctx.state = state
        ctx.body = {
            "message_id": "MSG001",
            "payload": {
                "opening_sentence": "test",
                "sentence_justification": "test",
                "associative_word": "test",
                "word_justification": "test",
                "confidence": 0.8,
            },
        }
        ctx.sender_email = "p1@test.com"
        ctx.context_builder = Mock()
        ctx.context_builder.build_score_feedback_ctx.return_value = {
            "dynamic": {}, "service": {},
        }
        ctx.ai = Mock()
        ctx.builder = Mock()
        ctx.builder.build_score_feedback.return_value = (
            {"message_type": "Q21SCOREFEEDBACK", "message_id": "SF001"},
            "subject",
        )
        ctx.builder.build_match_result.return_value = (
            {"message_type": "MATCH_RESULT_REPORT", "message_id": "MR001"},
            "subject",
        )
        ctx.config = {"league_manager_email": "lm@test.com"}
        return ctx

    @patch(EXEC_CB_SCORING, return_value={
        "league_points": 2, "private_score": 50.0,
        "breakdown": {
            "opening_sentence_score": 20.0,
            "sentence_justification_score": 10.0,
            "associative_word_score": 15.0,
            "word_justification_score": 5.0,
        },
        "feedback": {
            "opening_sentence": " ".join(["word"] * 160),
            "associative_word": " ".join(["word"] * 160),
        },
    })
    def test_first_player_scored_sets_guesses_collecting(self, mock_exec):
        """After first player scored, phase should be GUESSES_COLLECTING."""
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01",
                          phase=GamePhase.ANSWERS_SENT)
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player2 = PlayerState(email="p2@test.com", participant_id="P002")

        ctx = self._make_ctx(state)
        handle_guess(ctx)

        assert state.phase == GamePhase.GUESSES_COLLECTING

    @patch(EXEC_CB_SCORING, return_value={
        "league_points": 2, "private_score": 50.0,
        "breakdown": {
            "opening_sentence_score": 20.0,
            "sentence_justification_score": 10.0,
            "associative_word_score": 15.0,
            "word_justification_score": 5.0,
        },
        "feedback": {
            "opening_sentence": " ".join(["word"] * 160),
            "associative_word": " ".join(["word"] * 160),
        },
    })
    def test_both_players_scored_sets_match_reported(self, mock_exec):
        """After both players scored, phase should be MATCH_REPORTED."""
        state = GameState(game_id="0101001", match_id="0101001",
                          season_id="S01", league_id="L01",
                          phase=GamePhase.GUESSES_COLLECTING)
        state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
        state.player1.score_sent = True
        state.player1.league_points = 2
        state.player2 = PlayerState(email="p2@test.com", participant_id="P002")

        ctx = self._make_ctx(state)
        ctx.sender_email = "p2@test.com"
        handle_guess(ctx)

        assert state.phase == GamePhase.MATCH_REPORTED

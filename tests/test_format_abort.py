# Area: Integration Tests
# PRD: docs/prd-rlgm.md
"""Integration tests for format validation triggering game abort."""

from unittest.mock import MagicMock

from q21_referee._rlgm.orchestrator import RLGMOrchestrator
from q21_referee._rlgm.gprm import GPRM


def _config():
    return {
        "referee_email": "ref@test.com",
        "referee_id": "ref1",
        "league_id": "Q21G",
        "league_manager_email": "lm@test.com",
        "player_response_timeout_seconds": 40,
    }


def _gprm():
    return GPRM(
        game_id="0101001",
        match_id="match-1",
        round_id="R01",
        round_number=1,
        season_id="S01",
        player1_email="p1@test.com",
        player1_id="player1",
        player2_email="p2@test.com",
        player2_id="player2",
    )


def _make_ai():
    ai = MagicMock()
    ai.get_warmup_question.return_value = {"warmup_question": "Hello?"}
    ai.get_round_start_info.return_value = {
        "book_name": "T", "book_hint": "H", "association_word": "W",
    }
    ai.get_answers.return_value = {"answers": ["A"] * 20}
    ai.get_score_feedback.return_value = {
        "league_points": 0, "private_score": 0.0, "breakdown": {},
    }
    return ai


def _start_game():
    ai = _make_ai()
    orch = RLGMOrchestrator(config=_config(), ai=ai)
    orch.start_round(_gprm())
    return orch


class TestMissingPayloadAborts:
    """Message with no payload triggers format abort."""

    def test_missing_payload_aborts(self):
        orch = _start_game()
        assert orch.current_game is not None

        bad_body = {
            "message_type": "Q21WARMUPRESPONSE",
            "sender": {"email": "p1@test.com"},
        }
        outgoing = orch.route_player_message(
            "Q21WARMUPRESPONSE", bad_body, "p1@test.com",
        )
        assert orch.current_game is None
        assert len(outgoing) > 0


class TestMissingSenderAborts:
    """Message with no sender triggers format abort."""

    def test_missing_sender_aborts(self):
        orch = _start_game()
        assert orch.current_game is not None

        bad_body = {
            "message_type": "Q21WARMUPRESPONSE",
            "payload": {"answer": "4"},
        }
        outgoing = orch.route_player_message(
            "Q21WARMUPRESPONSE", bad_body, "p1@test.com",
        )
        assert orch.current_game is None
        assert len(outgoing) > 0


class TestQuestionsNotListAborts:
    """Q21_QUESTIONS_BATCH with questions as string triggers abort."""

    def test_questions_not_list_aborts(self):
        orch = _start_game()
        assert orch.current_game is not None

        bad_body = {
            "message_type": "Q21_QUESTIONS_BATCH",
            "sender": {"email": "p1@test.com"},
            "payload": {"questions": "not a list"},
        }
        outgoing = orch.route_player_message(
            "Q21_QUESTIONS_BATCH", bad_body, "p1@test.com",
        )
        assert orch.current_game is None
        assert len(outgoing) > 0


class TestValidMessageDoesNotAbort:
    """Valid warmup response keeps the game active."""

    def test_valid_message_does_not_abort(self):
        orch = _start_game()
        assert orch.current_game is not None

        valid_body = {
            "message_type": "Q21WARMUPRESPONSE",
            "sender": {"email": "p1@test.com"},
            "payload": {"answer": "4"},
            "game_id": "0101001",
        }
        outgoing = orch.route_player_message(
            "Q21WARMUPRESPONSE", valid_body, "p1@test.com",
        )
        assert orch.current_game is not None
        assert isinstance(outgoing, list)


class TestFormatAbortProducesMatchResult:
    """Format abort outgoing must contain a MATCH_RESULT_REPORT."""

    def test_format_abort_produces_match_result(self):
        orch = _start_game()
        assert orch.current_game is not None

        bad_body = {"some_field": "value"}
        outgoing = orch.route_player_message(
            "Q21WARMUPRESPONSE", bad_body, "p1@test.com",
        )
        assert orch.current_game is None
        types = [env.get("message_type") for env, _, _ in outgoing]
        assert "MATCH_RESULT_REPORT" in types

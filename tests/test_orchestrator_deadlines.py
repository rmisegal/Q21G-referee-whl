# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for orchestrator check_deadlines() and format validation."""

import time
from unittest.mock import patch
from q21_referee._rlgm.orchestrator import RLGMOrchestrator
from q21_referee._rlgm.gprm import GPRM
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for deadline and validation tests."""
    def get_warmup_question(self, ctx):
        return {"warmup_question": "Hello?"}
    def get_round_start_info(self, ctx):
        return {"book_name": "T", "book_hint": "H", "association_word": "W"}
    def get_answers(self, ctx):
        return {"answers": ["A"] * 20}
    def get_score_feedback(self, ctx):
        return {"league_points": 10, "private_score": 5.0, "breakdown": {}}


def _config():
    return {
        "referee_id": "REF001", "referee_email": "ref@test.com",
        "league_id": "L01", "league_manager_email": "lm@test.com",
        "player_response_timeout_seconds": 40,
    }


def _gprm():
    return GPRM(
        player1_email="p1@test.com", player1_id="P001",
        player2_email="p2@test.com", player2_id="P002",
        season_id="S01", game_id="0101001",
        match_id="match-1", round_id="ROUND_1", round_number=1,
    )


class TestCheckDeadlines:
    """Tests for orchestrator.check_deadlines()."""

    def test_check_deadlines_no_game(self):
        """No current game -> returns empty list."""
        orch = RLGMOrchestrator(config=_config(), ai=MockRefereeAI())
        assert orch.check_deadlines() == []

    def test_check_deadlines_nothing_expired(self):
        """Immediately after start_round, no deadlines expired yet."""
        orch = RLGMOrchestrator(config=_config(), ai=MockRefereeAI())
        orch.start_round(_gprm())
        assert orch.current_game is not None
        result = orch.check_deadlines()
        assert result == []
        assert orch.current_game is not None

    def test_check_deadlines_expired_aborts_game(self):
        """Expired deadline causes abort; current_game becomes None."""
        orch = RLGMOrchestrator(config=_config(), ai=MockRefereeAI())
        orch.start_round(_gprm())
        assert orch.current_game is not None
        # Force all deadlines to expire by moving monotonic time far forward
        with patch("q21_referee._gmc.deadline_tracker.time.monotonic",
                   return_value=time.monotonic() + 9999999.0):
            outgoing = orch.check_deadlines()
        assert len(outgoing) > 0
        assert orch.current_game is None
        # Outgoing should contain abort report
        types = [e.get("message_type") for e, _, _ in outgoing]
        assert "MATCH_RESULT_REPORT" in types


class TestFormatValidation:
    """Tests for format validation in route_player_message()."""

    def test_format_validation_aborts_on_bad_message(self):
        """Message missing required fields -> abort, outgoing returned."""
        orch = RLGMOrchestrator(config=_config(), ai=MockRefereeAI())
        orch.start_round(_gprm())
        assert orch.current_game is not None
        # Body missing message_type, sender, payload -> format violation
        bad_body = {"some_field": "value"}
        outgoing = orch.route_player_message(
            "Q21WARMUPRESPONSE", bad_body, "p1@test.com")
        assert len(outgoing) > 0
        assert orch.current_game is None
        types = [e.get("message_type") for e, _, _ in outgoing]
        assert "MATCH_RESULT_REPORT" in types

    def test_format_validation_passes_valid_message(self):
        """Valid message passes validation; game stays active."""
        orch = RLGMOrchestrator(config=_config(), ai=MockRefereeAI())
        orch.start_round(_gprm())
        assert orch.current_game is not None
        valid_body = {
            "message_type": "Q21WARMUPRESPONSE",
            "sender": {"email": "p1@test.com"},
            "payload": {"answer": "4"},
            "game_id": "0101001",
        }
        outgoing = orch.route_player_message(
            "Q21WARMUPRESPONSE", valid_body, "p1@test.com")
        assert isinstance(outgoing, list)
        assert orch.current_game is not None

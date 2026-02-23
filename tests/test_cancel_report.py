# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for cancel_report — cancelled match report (both players missing)."""

from q21_referee._rlgm.cancel_report import build_cancel_report
from q21_referee._rlgm.gprm import GPRM


def _make_gprm():
    return GPRM(
        player1_email="p1@test.com",
        player1_id="P1",
        player2_email="p2@test.com",
        player2_id="P2",
        season_id="S01",
        game_id="0101001",
        match_id="0101001",
        round_id="S01_R1",
        round_number=1,
    )


def _make_config():
    return {
        "league_id": "Q21G",
        "referee_email": "ref@test.com",
        "referee_id": "REF001",
        "league_manager_email": "lm@test.com",
    }


class TestBuildCancelReport:
    """Tests for build_cancel_report."""

    def test_returns_one_message(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        assert len(result) == 1

    def test_sent_to_league_manager(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        _env, _subj, recipient = result[0]
        assert recipient == "lm@test.com"

    def test_status_is_cancelled_all_players_malfunction(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        env, _subj, _recipient = result[0]
        assert env["payload"]["status"] == "CANCELLED_ALL_PLAYERS_MALFUNCTION"

    def test_scores_are_empty(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        env, _subj, _recipient = result[0]
        assert env["payload"]["scores"] == []

    def test_no_winner_and_is_draw(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        env, _subj, _recipient = result[0]
        assert env["payload"]["winner_id"] is None
        assert env["payload"]["is_draw"] is True

    def test_match_id_from_gprm(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        env, _subj, _recipient = result[0]
        assert env["payload"]["match_id"] == "0101001"

    def test_game_id_in_envelope(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        env, _subj, _recipient = result[0]
        assert env["game_id"] == "0101001"

    def test_message_type_is_match_result_report(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        env, _subj, _recipient = result[0]
        assert env["message_type"] == "MATCH_RESULT_REPORT"

    def test_subject_is_string(self):
        result = build_cancel_report(_make_gprm(), _make_config())
        _env, subj, _recipient = result[0]
        assert isinstance(subj, str)
        assert len(subj) > 0

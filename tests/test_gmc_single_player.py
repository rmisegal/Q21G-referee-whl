# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for GMC single-player mode initialization."""

import pytest
from q21_referee._gmc.gmc import GameManagementCycle
from q21_referee._rlgm.gprm import GPRM
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}

    def get_round_start_info(self, ctx):
        return {"book_name": "Test", "book_hint": "A test", "association_word": "test"}

    def get_answers(self, ctx):
        return {"answers": []}

    def get_score_feedback(self, ctx):
        return {"league_points": 0, "private_score": 0.0, "breakdown": {}, "feedback": ""}


def _make_gprm():
    return GPRM(
        player1_email="p1@test.com", player1_id="P1",
        player2_email="p2@test.com", player2_id="P2",
        season_id="S01", game_id="0101001", match_id="0101001",
        round_id="S01_R1", round_number=1,
    )


def _make_config():
    return {
        "league_id": "Q21G",
        "referee_email": "ref@test.com",
        "referee_id": "REF001",
    }


class TestGMCNormalMode:
    """Normal mode: both players active, no single-player flags."""

    def test_normal_mode_both_players_active(self):
        gmc = GameManagementCycle(_make_gprm(), MockRefereeAI(), _make_config())
        assert gmc.state.single_player_mode is False
        assert gmc.state.missing_player_role is None
        assert gmc.state.missing_player_email is None

    def test_normal_mode_active_players_count(self):
        gmc = GameManagementCycle(_make_gprm(), MockRefereeAI(), _make_config())
        assert len(gmc.state.active_players()) == 2


class TestGMCSinglePlayerMissingPlayer2:
    """Single-player mode with player2 missing."""

    def test_single_player_flag_set(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player2",
        )
        assert gmc.state.single_player_mode is True
        assert gmc.state.missing_player_role == "player2"
        assert gmc.state.missing_player_email == "p2@test.com"

    def test_missing_player_state_prefilled(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player2",
        )
        p2 = gmc.state.player2
        assert p2.warmup_answer == "ABSENT_MALFUNCTION"
        assert p2.answers_sent is True
        assert p2.score_sent is True
        assert p2.league_points == 1

    def test_active_players_excludes_missing(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player2",
        )
        active = gmc.state.active_players()
        assert len(active) == 1
        assert active[0].email == "p1@test.com"

    def test_present_player_state_untouched(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player2",
        )
        p1 = gmc.state.player1
        assert p1.warmup_answer is None
        assert p1.answers_sent is False
        assert p1.score_sent is False
        assert p1.league_points == 0


class TestGMCSinglePlayerMissingPlayer1:
    """Single-player mode with player1 missing."""

    def test_single_player_flag_set(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player1",
        )
        assert gmc.state.single_player_mode is True
        assert gmc.state.missing_player_role == "player1"
        assert gmc.state.missing_player_email == "p1@test.com"

    def test_missing_player_state_prefilled(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player1",
        )
        p1 = gmc.state.player1
        assert p1.warmup_answer == "ABSENT_MALFUNCTION"
        assert p1.answers_sent is True
        assert p1.score_sent is True
        assert p1.league_points == 1

    def test_active_players_excludes_missing(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player1",
        )
        active = gmc.state.active_players()
        assert len(active) == 1
        assert active[0].email == "p2@test.com"

    def test_present_player_state_untouched(self):
        gmc = GameManagementCycle(
            _make_gprm(), MockRefereeAI(), _make_config(),
            single_player_mode=True, missing_player_role="player1",
        )
        p2 = gmc.state.player2
        assert p2.warmup_answer is None
        assert p2.answers_sent is False
        assert p2.score_sent is False
        assert p2.league_points == 0

# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup_initiator single-player mode support."""

from q21_referee._rlgm.warmup_initiator import initiate_warmup
from q21_referee._rlgm.gprm import GPRM
from q21_referee._gmc.gmc import GameManagementCycle
from q21_referee._gmc.state import GamePhase
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""
    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}
    def get_round_start_info(self, ctx):
        return {"book_name": "Test", "book_hint": "A test",
                "association_word": "test"}
    def get_answers(self, ctx):
        return {"answers": ["A"]}
    def get_score_feedback(self, ctx):
        return {"league_points": 2, "private_score": 50.0,
                "breakdown": {
                    "opening_sentence_score": 20.0,
                    "sentence_justification_score": 10.0,
                    "associative_word_score": 15.0,
                    "word_justification_score": 5.0,
                },
                "feedback": {
                    "opening_sentence": "good",
                    "associative_word": "good",
                }}


def make_config():
    return {
        "referee_id": "REF001", "referee_email": "ref@test.com",
        "group_id": "GROUP_A", "league_id": "Q21G",
        "season_id": "S01", "league_manager_email": "lm@test.com",
    }


def make_gprm():
    return GPRM(
        player1_email="p1@test.com", player1_id="P001",
        player2_email="p2@test.com", player2_id="P002",
        season_id="S01", game_id="0101001",
        match_id="0101001",
        round_id="S01_R1", round_number=1,
    )


class TestWarmupSinglePlayerMode:
    """Tests for warmup_initiator with single-player mode."""

    def test_normal_mode_sends_to_both_players(self):
        """Normal mode: warmup sent to both players."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        assert len(outgoing) == 2
        recipients = {r for _, _, r in outgoing}
        assert recipients == {"p1@test.com", "p2@test.com"}

    def test_single_player_sends_only_to_active_player(self):
        """Single-player mode (missing player2): only 1 warmup sent."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(
            gprm=gprm, ai=ai, config=config,
            single_player_mode=True,
            missing_player_role="player2",
        )

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        assert len(outgoing) == 1
        assert outgoing[0][2] == "p1@test.com"

    def test_single_player_missing_player1(self):
        """Single-player mode (missing player1): only player2 gets warmup."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(
            gprm=gprm, ai=ai, config=config,
            single_player_mode=True,
            missing_player_role="player1",
        )

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        assert len(outgoing) == 1
        assert outgoing[0][2] == "p2@test.com"

    def test_single_player_advances_phase(self):
        """Phase advances to WARMUP_SENT even in single-player mode."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(
            gprm=gprm, ai=ai, config=config,
            single_player_mode=True,
            missing_player_role="player2",
        )

        initiate_warmup(gmc, gprm, ai, config)

        assert gmc.state.phase == GamePhase.WARMUP_SENT

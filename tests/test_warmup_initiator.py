# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup_initiator: building warmup calls for players."""

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
        "group_id": "GROUP_A", "league_id": "LEAGUE001",
        "season_id": "S01", "league_manager_email": "lm@test.com",
    }


def make_gprm(round_number=1):
    return GPRM(
        player1_email="p1@test.com", player1_id="P001",
        player2_email="p2@test.com", player2_id="P002",
        season_id="S01", game_id=f"01{round_number:02d}001",
        match_id=f"01{round_number:02d}001",
        round_id=f"ROUND_{round_number}", round_number=round_number,
    )


class TestInitiateWarmup:
    """Tests for initiate_warmup function."""

    def test_warmup_sends_to_both_players(self):
        """Both players receive warmup calls."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm, ai, config)

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        assert len(outgoing) == 2
        recipients = {r for _, _, r in outgoing}
        assert recipients == {"p1@test.com", "p2@test.com"}

    def test_warmup_advances_phase(self):
        """Warmup should advance GMC to WARMUP_SENT."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm, ai, config)

        initiate_warmup(gmc, gprm, ai, config)

        assert gmc.state.phase == GamePhase.WARMUP_SENT

    def test_warmup_skips_none_player(self):
        """Warmup should skip None players without crashing."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm, ai, config)
        gmc.state.player2 = None

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        assert len(outgoing) == 1
        assert outgoing[0][2] == "p1@test.com"

    def test_warmup_skips_both_none_players(self):
        """Warmup should return empty list when both players are None."""
        config = make_config()
        gprm = make_gprm()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm, ai, config)
        gmc.state.player1 = None
        gmc.state.player2 = None

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        assert len(outgoing) == 0


class TestWarmupCallbackResilience:
    """Tests for warmup callback failure handling."""

    def test_callback_failure_uses_fallback_question(self):
        """If get_warmup_question fails, fallback question is used."""
        class FailingAI(MockRefereeAI):
            def get_warmup_question(self, ctx):
                raise ValueError("AI exploded")

        config = make_config()
        gprm = make_gprm()
        ai = FailingAI()
        gmc = GameManagementCycle(gprm, ai, config)

        outgoing = initiate_warmup(gmc, gprm, ai, config)

        # Should still send warmup calls with fallback question
        assert len(outgoing) == 2
        # Phase should still advance
        assert gmc.state.phase == GamePhase.WARMUP_SENT

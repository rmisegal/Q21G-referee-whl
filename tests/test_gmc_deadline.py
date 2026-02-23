# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for DeadlineTracker wiring inside GameManagementCycle."""

from q21_referee._gmc.gmc import GameManagementCycle
from q21_referee._gmc.deadline_tracker import DeadlineTracker
from q21_referee._rlgm.gprm import GPRM
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Minimal AI stub for GMC construction."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}

    def get_round_start_info(self, ctx):
        return {"book_name": "X", "book_hint": "Y", "association_word": "Z"}

    def get_answers(self, ctx):
        return {"answers": []}

    def get_score_feedback(self, ctx):
        return {"league_points": 0, "private_score": 0.0}


def _make_gprm():
    return GPRM(
        player1_email="p1@test.com",
        player1_id="P001",
        player2_email="p2@test.com",
        player2_id="P002",
        season_id="S01",
        game_id="0101001",
        match_id="M001",
        round_id="R01",
        round_number=1,
    )


def _make_config():
    return {
        "referee_email": "ref@test.com",
        "referee_id": "REF001",
        "league_id": "Q21G",
    }


class TestGMCDeadlineTracker:
    """DeadlineTracker should be wired into GMC."""

    def test_gmc_has_deadline_tracker(self):
        """GMC must expose a DeadlineTracker instance."""
        gmc = GameManagementCycle(_make_gprm(), MockRefereeAI(), _make_config())
        assert isinstance(gmc.deadline_tracker, DeadlineTracker)

    def test_gmc_deadline_tracker_is_fresh_per_instance(self):
        """Each GMC instance must have its own DeadlineTracker."""
        gmc1 = GameManagementCycle(_make_gprm(), MockRefereeAI(), _make_config())
        gmc2 = GameManagementCycle(_make_gprm(), MockRefereeAI(), _make_config())
        assert gmc1.deadline_tracker is not gmc2.deadline_tracker

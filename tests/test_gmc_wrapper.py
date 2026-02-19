# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for GMC Wrapper Class."""

import pytest
from unittest.mock import Mock
from q21_referee._gmc.gmc import GameManagementCycle
from q21_referee._rlgm.gprm import GPRM
from q21_referee._rlgm.game_result import GameResult
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}

    def get_round_start_info(self, ctx):
        return {"book_name": "Test Book", "book_hint": "A test", "association_word": "test"}

    def get_answers(self, ctx):
        return {"answers": ["A", "B", "C"]}

    def get_score_feedback(self, ctx):
        return {"league_points": 10, "private_score": 5.0, "breakdown": {}, "feedback": "Good"}


class TestGameManagementCycle:
    """Tests for GameManagementCycle wrapper."""

    def create_gprm(self):
        """Create sample GPRM."""
        return GPRM(
            player1_email="p1@test.com",
            player1_id="P001",
            player2_email="p2@test.com",
            player2_id="P002",
            season_id="SEASON_2026_Q1",
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            round_number=1,
        )

    def create_config(self):
        """Create sample config."""
        return {
            "referee_email": "ref@test.com",
            "referee_id": "REF001",
            "league_manager_email": "lm@test.com",
            "league_id": "LEAGUE001",
        }

    def test_gmc_accepts_gprm(self):
        """Test that GMC can be created with GPRM."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()

        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        assert gmc.gprm == gprm
        assert gmc.state.game_id == "0101001"
        assert gmc.state.player1.email == "p1@test.com"

    def test_gmc_get_result_before_complete_returns_none(self):
        """Test that get_result returns None before game completes."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()

        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        result = gmc.get_result()
        assert result is None

    def test_gmc_is_complete_false_initially(self):
        """Test that is_complete returns False initially."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()

        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        assert gmc.is_complete() is False

    def test_gmc_route_message(self):
        """Test that route_message delegates to router."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()

        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        # Send new round message
        message = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "payload": {"round_id": "ROUND_1", "round_number": 1},
        }
        outgoing = gmc.route_message("BROADCAST_NEW_LEAGUE_ROUND", message, "lm@test.com")

        # Should return warmup calls for both players
        assert len(outgoing) == 2

    def test_gmc_builds_game_result_on_complete(self):
        """Test that GMC builds GameResult when match completes."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()

        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        # Simulate full game flow would be complex, so we test the result building
        # by manually setting state and calling the internal method
        gmc.state.player1.league_points = 15
        gmc.state.player1.private_score = 7.5
        gmc.state.player2.league_points = 10
        gmc.state.player2.private_score = 5.0
        gmc.state.player1.score_sent = True
        gmc.state.player2.score_sent = True

        result = gmc._build_game_result()

        assert isinstance(result, GameResult)
        assert result.winner_id == "P001"
        assert result.is_draw is False
        assert result.player1.score == 15
        assert result.player2.score == 10

    def test_get_state_snapshot_idle(self):
        """Test snapshot at IDLE phase."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        snapshot = gmc.get_state_snapshot()

        assert snapshot["game_id"] == "0101001"
        assert snapshot["phase"] == "idle"
        assert snapshot["player1"]["email"] == "p1@test.com"
        assert snapshot["player1"]["participant_id"] == "P001"
        assert snapshot["player1"]["phase_reached"] == "idle"
        assert snapshot["player1"]["scored"] is False
        assert snapshot["player1"]["last_actor"] == "referee"
        assert snapshot["player2"]["last_actor"] == "referee"

    def test_get_state_snapshot_warmup_one_responded(self):
        """Test snapshot when one player responded to warmup."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        from q21_referee._gmc.state import GamePhase
        gmc.state.phase = GamePhase.WARMUP_SENT
        gmc.state.player1.warmup_answer = "4"

        snapshot = gmc.get_state_snapshot()

        assert snapshot["phase"] == "warmup_sent"
        assert snapshot["player1"]["phase_reached"] == "warmup_answered"
        assert snapshot["player1"]["last_actor"] == "P001"
        assert snapshot["player2"]["phase_reached"] == "warmup_sent"
        assert snapshot["player2"]["last_actor"] == "referee"

    def test_get_state_snapshot_scored(self):
        """Test snapshot when one player has been scored."""
        gprm = self.create_gprm()
        config = self.create_config()
        ai = MockRefereeAI()
        gmc = GameManagementCycle(gprm=gprm, ai=ai, config=config)

        from q21_referee._gmc.state import GamePhase
        gmc.state.phase = GamePhase.SCORING_COMPLETE
        gmc.state.player1.score_sent = True
        gmc.state.player1.league_points = 10
        gmc.state.player1.guess = {"opening_sentence": "test"}
        gmc.state.player2.guess = {"opening_sentence": "test2"}

        snapshot = gmc.get_state_snapshot()

        assert snapshot["player1"]["scored"] is True
        assert snapshot["player1"]["phase_reached"] == "scored"
        assert snapshot["player2"]["scored"] is False
        assert snapshot["player2"]["phase_reached"] == "guess_submitted"
        assert snapshot["player2"]["last_actor"] == "P002"

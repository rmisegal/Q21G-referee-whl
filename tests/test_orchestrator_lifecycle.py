# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for orchestrator round lifecycle: start_round, abort, complete."""

import pytest
import logging
from unittest.mock import Mock
from q21_referee._rlgm.orchestrator import RLGMOrchestrator
from q21_referee._rlgm.gprm import GPRM
from q21_referee._rlgm.enums import RLGMState, RLGMEvent
from q21_referee._gmc.state import GamePhase
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""
    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}
    def get_round_start_info(self, ctx):
        return {"book_name": "Test", "book_hint": "A test", "association_word": "test"}
    def get_answers(self, ctx):
        return {"answers": ["A", "B", "C"]}
    def get_score_feedback(self, ctx):
        return {"league_points": 10, "private_score": 5.0, "breakdown": {}}


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
        match_id=f"01{round_number:02d}001", round_id=f"ROUND_{round_number}",
        round_number=round_number,
    )


class TestStartRound:
    """Tests for orchestrator.start_round()."""

    def test_start_round_creates_gmc_and_warmup(self):
        """Test that start_round creates GMC and returns warmup messages."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())

        outgoing = orchestrator.start_round(make_gprm(1))

        assert orchestrator.current_game is not None
        assert orchestrator.current_round_number == 1
        assert len(outgoing) == 2  # warmup calls for 2 players
        for env, subject, recipient in outgoing:
            assert env["message_type"] == "Q21WARMUPCALL"

    def test_start_round_advances_gmc_phase(self):
        """Test that start_round sets GMC phase to WARMUP_SENT."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())

        orchestrator.start_round(make_gprm(1))

        assert orchestrator.current_game.state.phase == GamePhase.WARMUP_SENT

    def test_start_round_idempotent_same_round(self):
        """Test that starting the same round twice is idempotent."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())

        outgoing1 = orchestrator.start_round(make_gprm(1))
        first_game = orchestrator.current_game

        outgoing2 = orchestrator.start_round(make_gprm(1))

        assert orchestrator.current_game is first_game
        assert outgoing2 == []

    def test_start_round_warmup_messages_target_players(self):
        """Test that warmup messages are addressed to both players."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())

        outgoing = orchestrator.start_round(make_gprm(1))

        recipients = {recipient for _, _, recipient in outgoing}
        assert recipients == {"p1@test.com", "p2@test.com"}

    def test_start_round_overwrites_previous_game_with_warning(self, caplog):
        """Test that starting a new round when game exists logs warning."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())

        orchestrator.start_round(make_gprm(1))
        first_game = orchestrator.current_game

        with caplog.at_level(logging.WARNING):
            outgoing = orchestrator.start_round(make_gprm(2))

        assert orchestrator.current_game is not first_game
        assert orchestrator.current_round_number == 2
        assert len(outgoing) == 2
        assert any("Overwriting" in r.message for r in caplog.records)

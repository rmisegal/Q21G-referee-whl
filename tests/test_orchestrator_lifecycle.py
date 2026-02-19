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
        return {
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
        }


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

    def test_start_round_aborts_previous_game(self, caplog):
        """Test that starting a new round aborts the previous game."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())

        orchestrator.start_round(make_gprm(1))
        first_game = orchestrator.current_game

        with caplog.at_level(logging.INFO):
            outgoing = orchestrator.start_round(make_gprm(2))

        assert orchestrator.current_game is not first_game
        assert orchestrator.current_round_number == 2
        # Should have abort report + 2 warmup calls
        warmup_msgs = [
            (e, s, r) for e, s, r in outgoing
            if e.get("message_type") == "Q21WARMUPCALL"
        ]
        abort_msgs = [
            (e, s, r) for e, s, r in outgoing
            if e.get("message_type") == "MATCH_RESULT_REPORT"
        ]
        assert len(warmup_msgs) == 2
        assert len(abort_msgs) == 1
        assert any("Aborting" in r.message for r in caplog.records)


class TestAbortCurrentGame:
    """Tests for orchestrator.abort_current_game()."""

    def test_abort_no_game_returns_empty(self):
        """Test that aborting when no game is active returns empty."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        outgoing = orchestrator.abort_current_game("new_round_started")
        assert outgoing == []

    def test_abort_during_warmup_sent(self):
        """Test aborting during WARMUP_SENT phase (no player responded)."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        orchestrator.start_round(make_gprm(1))
        assert orchestrator.current_game.state.phase == GamePhase.WARMUP_SENT

        outgoing = orchestrator.abort_current_game("new_round_started")

        # Should produce MATCH_RESULT_REPORT only (no players to score)
        assert orchestrator.current_game is None
        match_reports = [
            (e, s, r) for e, s, r in outgoing
            if e.get("message_type") == "MATCH_RESULT_REPORT"
        ]
        assert len(match_reports) == 1
        env = match_reports[0][0]
        assert env["payload"]["status"] == "aborted"
        assert env["payload"]["abort_reason"] == "new_round_started"
        assert "player_states" in env["payload"]

    def test_abort_during_guesses_scores_eligible(self):
        """Test aborting when a player submitted a guess — should score."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        orchestrator.start_round(make_gprm(1))

        # Simulate: advance to guess collection, player1 submitted guess
        gmc = orchestrator.current_game
        gmc.state.phase = GamePhase.GUESSES_COLLECTING
        gmc.state.player1.guess = {"opening_sentence": "test"}
        gmc.state.player1.warmup_answer = "4"
        gmc.state.player1.questions = [{"q": "test"}]
        gmc.state.player2.warmup_answer = "4"
        gmc.state.player2.questions = [{"q": "test"}]
        gmc.state.book_name = "Test Book"

        outgoing = orchestrator.abort_current_game("new_round_started")

        # Should have Q21SCOREFEEDBACK for player1 + MATCH_RESULT_REPORT
        score_msgs = [
            (e, s, r) for e, s, r in outgoing
            if e.get("message_type") == "Q21SCOREFEEDBACK"
        ]
        assert len(score_msgs) == 1
        assert score_msgs[0][2] == "p1@test.com"

        match_reports = [
            (e, s, r) for e, s, r in outgoing
            if e.get("message_type") == "MATCH_RESULT_REPORT"
        ]
        assert len(match_reports) == 1

    def test_abort_sets_game_to_none(self):
        """Test that abort clears the current game."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        orchestrator.start_round(make_gprm(1))
        orchestrator.abort_current_game("new_round_started")
        assert orchestrator.current_game is None

    def test_abort_transitions_state_machine(self):
        """Test abort transitions state machine with GAME_ABORTED."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        # Get to IN_GAME state
        orchestrator.state_machine.transition(RLGMEvent.SEASON_START)
        orchestrator.state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        orchestrator.state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        orchestrator.state_machine.transition(RLGMEvent.ROUND_START)
        assert orchestrator.state_machine.current_state == RLGMState.IN_GAME

        # Create a game manually with proper mock attributes
        mock_game = Mock()
        mock_game.get_state_snapshot.return_value = {
            "game_id": "0101001", "phase": "warmup_sent",
            "player1": {
                "email": "p1@test.com", "participant_id": "P001",
                "phase_reached": "warmup_sent", "scored": False,
                "last_actor": "referee",
            },
            "player2": {
                "email": "p2@test.com", "participant_id": "P002",
                "phase_reached": "warmup_sent", "scored": False,
                "last_actor": "referee",
            },
        }
        mock_game.gprm = make_gprm(1)
        mock_game.state.player1.guess = None
        mock_game.state.player2.guess = None
        mock_game.state.player1.score_sent = False
        mock_game.state.player2.score_sent = False
        mock_game.state.player1.league_points = 0
        mock_game.state.player2.league_points = 0
        mock_game.state.player1.private_score = 0.0
        mock_game.state.player2.private_score = 0.0
        mock_game.state.player1.participant_id = "P001"
        mock_game.state.player1.email = "p1@test.com"
        mock_game.state.player2.participant_id = "P002"
        mock_game.state.player2.email = "p2@test.com"
        mock_game.builder = Mock()
        mock_game.builder.build_match_result.return_value = (
            {"message_type": "MATCH_RESULT_REPORT",
             "payload": {"status": "aborted"}},
            "subject",
        )
        orchestrator.current_game = mock_game
        orchestrator.current_round_number = 1

        orchestrator.abort_current_game("new_round_started")

        assert orchestrator.state_machine.current_state == RLGMState.RUNNING


class TestCompleteGame:
    """Tests for orchestrator.complete_game()."""

    def test_complete_game_clears_current_game(self):
        """Test that complete_game sets current_game to None."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        orchestrator.start_round(make_gprm(1))

        # Simulate game completion
        gmc = orchestrator.current_game
        gmc.state.player1.league_points = 15
        gmc.state.player2.league_points = 10
        gmc.state.player1.score_sent = True
        gmc.state.player2.score_sent = True
        gmc.state.phase = GamePhase.MATCH_REPORTED

        orchestrator.complete_game()

        assert orchestrator.current_game is None

    def test_complete_game_transitions_state(self):
        """Test that complete_game fires GAME_COMPLETE event."""
        orchestrator = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
        # Walk state machine to IN_GAME
        orchestrator.state_machine.transition(RLGMEvent.SEASON_START)
        orchestrator.state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        orchestrator.state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
        orchestrator.state_machine.transition(RLGMEvent.ROUND_START)

        orchestrator.current_game = Mock()
        orchestrator.current_game.get_result.return_value = Mock(
            match_id="R1M1", winner_id="P001"
        )

        orchestrator.complete_game()

        assert orchestrator.state_machine.current_state == RLGMState.RUNNING
        assert orchestrator.current_game is None

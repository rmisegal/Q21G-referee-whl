# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for orchestrator malfunction handling in handle_lm_message."""

import pytest
from unittest.mock import patch, MagicMock
from q21_referee._rlgm.orchestrator import RLGMOrchestrator
from q21_referee._rlgm.gprm import GPRM
from q21_referee._rlgm.enums import RLGMEvent
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""
    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}
    def get_round_start_info(self, ctx):
        return {"book_name": "T", "book_hint": "H", "association_word": "w"}
    def get_answers(self, ctx):
        return {"answers": ["A"]}
    def get_score_feedback(self, ctx):
        return {"league_points": 2, "private_score": 50.0, "breakdown": {}}


def make_config():
    return {
        "referee_id": "REF001", "referee_email": "ref@test.com",
        "group_id": "GROUP_A", "league_id": "LEAGUE001",
        "season_id": "S01", "league_manager_email": "lm@test.com",
    }


def make_assignment(round_number=1):
    return {
        "round_number": round_number, "game_id": f"01{round_number:02d}001",
        "player1_email": "p1@test.com", "player1_id": "P001",
        "player2_email": "p2@test.com", "player2_id": "P002",
    }


def setup_orchestrator_for_round():
    """Create orchestrator in RUNNING state with assignments."""
    orch = RLGMOrchestrator(config=make_config(), ai=MockRefereeAI())
    orch.state_machine.transition(RLGMEvent.SEASON_START)
    orch.state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
    orch.state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
    orch._assignments = [make_assignment(1)]
    orch._new_round_handler.assignments = orch._assignments
    return orch


def make_new_round_message(round_number=1, lookup_table=None):
    """Build a BROADCAST_NEW_LEAGUE_ROUND message."""
    payload = {"round_number": round_number, "round_id": f"ROUND_{round_number}"}
    if lookup_table is not None:
        payload["participant_lookup_table"] = lookup_table
    return {
        "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
        "broadcast_id": f"BC_ROUND_{round_number}",
        "payload": payload,
    }


class TestNormalMode:
    """NORMAL malfunction status: standard two-player game."""

    def test_normal_starts_game(self):
        """No malfunction -> start_round creates GMC normally."""
        orch = setup_orchestrator_for_round()
        msg = make_new_round_message(1, lookup_table=["p1@test.com", "p2@test.com"])
        orch.handle_lm_message(msg)

        assert orch.current_game is not None
        assert orch.current_game.state.single_player_mode is False

    def test_normal_sends_two_warmup_calls(self):
        """Normal mode sends warmup to both players."""
        orch = setup_orchestrator_for_round()
        msg = make_new_round_message(1, lookup_table=["p1@test.com", "p2@test.com"])
        orch.handle_lm_message(msg)
        pending = orch.get_pending_outgoing()

        warmups = [(e, s, r) for e, s, r in pending
                   if e.get("message_type") == "Q21WARMUPCALL"]
        assert len(warmups) == 2

    def test_no_lookup_table_is_normal(self):
        """When lookup table is absent, treat as NORMAL."""
        orch = setup_orchestrator_for_round()
        msg = make_new_round_message(1)  # no lookup table
        orch.handle_lm_message(msg)

        assert orch.current_game is not None
        assert orch.current_game.state.single_player_mode is False


class TestSinglePlayerMode:
    """SINGLE_PLAYER malfunction status: one player missing."""

    def test_single_player_starts_game_with_flag(self):
        """Single-player mode sets single_player_mode on GMC."""
        orch = setup_orchestrator_for_round()
        # Only p1 in lookup table -> p2 is missing
        msg = make_new_round_message(1, lookup_table=["p1@test.com"])
        orch.handle_lm_message(msg)

        assert orch.current_game is not None
        assert orch.current_game.state.single_player_mode is True
        assert orch.current_game.state.missing_player_role == "player2"

    def test_single_player_missing_player1(self):
        """When player1 is missing, missing_player_role is 'player1'."""
        orch = setup_orchestrator_for_round()
        # Only p2 in lookup table -> p1 is missing
        msg = make_new_round_message(1, lookup_table=["p2@test.com"])
        orch.handle_lm_message(msg)

        assert orch.current_game.state.single_player_mode is True
        assert orch.current_game.state.missing_player_role == "player1"

    def test_single_player_still_sends_warmup(self):
        """Single-player mode still calls start_round (warmup is sent)."""
        orch = setup_orchestrator_for_round()
        msg = make_new_round_message(1, lookup_table=["p1@test.com"])
        orch.handle_lm_message(msg)
        pending = orch.get_pending_outgoing()

        # warmup calls should still be generated
        warmups = [(e, s, r) for e, s, r in pending
                   if e.get("message_type") == "Q21WARMUPCALL"]
        assert len(warmups) >= 1  # at least the active player


class TestCancelledMode:
    """CANCELLED malfunction status: both players missing."""

    def test_cancelled_does_not_start_game(self):
        """Cancelled mode does NOT create a GMC."""
        orch = setup_orchestrator_for_round()
        # Empty lookup table -> both missing
        msg = make_new_round_message(1, lookup_table=[])
        orch.handle_lm_message(msg)

        assert orch.current_game is None

    def test_cancelled_sends_cancel_report(self):
        """Cancelled mode sends MATCH_RESULT_REPORT with cancel status."""
        orch = setup_orchestrator_for_round()
        msg = make_new_round_message(1, lookup_table=[])
        orch.handle_lm_message(msg)
        pending = orch.get_pending_outgoing()

        reports = [(e, s, r) for e, s, r in pending
                   if e.get("message_type") == "MATCH_RESULT_REPORT"]
        assert len(reports) == 1
        env, _, recipient = reports[0]
        assert env["payload"]["status"] == "CANCELLED_ALL_PLAYERS_MALFUNCTION"
        assert recipient == "lm@test.com"

    def test_cancelled_returns_none(self):
        """handle_lm_message returns None for new round (always)."""
        orch = setup_orchestrator_for_round()
        msg = make_new_round_message(1, lookup_table=[])
        result = orch.handle_lm_message(msg)

        assert result is None

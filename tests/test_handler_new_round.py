# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_NEW_LEAGUE_ROUND handler."""

import pytest
from q21_referee._rlgm.handler_new_round import BroadcastNewRoundHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent
from q21_referee._rlgm.gprm import GPRM


class TestBroadcastNewRoundHandler:
    """Tests for BroadcastNewRoundHandler."""

    def create_handler_in_running_state(self):
        """Create handler with state machine in RUNNING state."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)

        config = {
            "referee_id": "REF001",
            "group_id": "GROUP_A",
            "season_id": "SEASON_2026_Q1",
            "game_id": "0101001",
        }

        # Sample assignments
        assignments = [
            {
                "round_number": 1,
                "round_id": "ROUND_1",
                "match_id": "R1M1",
                "game_id": "0101001",
                "player1_id": "P001",
                "player1_email": "p1@test.com",
                "player2_id": "P002",
                "player2_email": "p2@test.com",
            },
            {
                "round_number": 2,
                "round_id": "ROUND_2",
                "match_id": "R2M1",
                "game_id": "0102001",
                "player1_id": "P001",
                "player1_email": "p1@test.com",
                "player2_id": "P003",
                "player2_email": "p3@test.com",
            },
        ]

        handler = BroadcastNewRoundHandler(state_machine, config, assignments)
        return handler, state_machine

    def create_round_message(self, round_number=1, round_id="ROUND_1"):
        """Create sample new round message."""
        return {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "broadcast_id": "BC003",
            "payload": {
                "round_number": round_number,
                "round_id": round_id,
                "season_id": "SEASON_2026_Q1",
            },
        }

    def test_extracts_round_info(self):
        """Test that round_number and round_id are extracted."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_round_message(round_number=2, round_id="ROUND_2")

        result = handler.handle(message)

        assert result is not None
        assert result["round_number"] == 2
        assert result["round_id"] == "ROUND_2"

    def test_queries_assignments_for_round(self):
        """Test that assignment for the round is found."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_round_message(round_number=1)

        result = handler.handle(message)

        assert result is not None
        assert result["assignment"]["match_id"] == "R1M1"

    def test_builds_gprm(self):
        """Test that GPRM is built from assignment."""
        handler, _ = self.create_handler_in_running_state()
        message = self.create_round_message(round_number=1)

        result = handler.handle(message)

        assert result is not None
        gprm = result["gprm"]
        assert isinstance(gprm, GPRM)
        assert gprm.player1_id == "P001"
        assert gprm.player2_id == "P002"
        assert gprm.round_number == 1

    def test_triggers_state_transition(self):
        """Test that handler triggers ROUND_START transition."""
        handler, state_machine = self.create_handler_in_running_state()
        assert state_machine.current_state == RLGMState.RUNNING

        handler.handle(self.create_round_message())

        assert state_machine.current_state == RLGMState.IN_GAME

    def test_no_assignment_for_round(self):
        """Test handling when no assignment exists for round."""
        handler, state_machine = self.create_handler_in_running_state()
        message = self.create_round_message(round_number=99)

        result = handler.handle(message)

        # Should return None and not transition
        assert result is None
        assert state_machine.current_state == RLGMState.RUNNING

    def test_handles_none_round_number(self):
        """Test handling when round_number is None in payload."""
        handler, state_machine = self.create_handler_in_running_state()
        message = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "broadcast_id": "BC003",
            "payload": {
                "round_number": None,  # Explicitly None
                "round_id": "ROUND_1",
            },
        }

        result = handler.handle(message)

        # Should default to round 0 and not find assignment
        assert result is None

    def test_handles_missing_round_number(self):
        """Test handling when round_number is missing from payload."""
        handler, state_machine = self.create_handler_in_running_state()
        message = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "broadcast_id": "BC003",
            "payload": {
                "round_id": "ROUND_1",
                # round_number missing
            },
        }

        result = handler.handle(message)

        # Should default to round 0 and not find assignment
        assert result is None

    def test_handle_rejects_assignment_missing_player_fields(self):
        """GPRM should not be built with missing required player fields."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)

        config = {"season_id": "S01"}
        handler = BroadcastNewRoundHandler(state_machine, config, assignments=[
            {"round_number": 1, "game_id": "0101001",
             "player1_email": "p1@test.com", "player1_id": "P001"}
            # missing player2_email and player2_id
        ])

        msg = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "broadcast_id": "BC003",
            "payload": {"round_number": 1, "round_id": "ROUND_1"},
        }
        result = handler.handle(msg)
        assert result is None  # Should reject, not silently create GPRM

    def test_handle_rejects_assignment_empty_email(self):
        """GPRM should not be built when email is empty string."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)

        config = {"season_id": "S01"}
        handler = BroadcastNewRoundHandler(state_machine, config, assignments=[
            {"round_number": 1, "game_id": "0101001",
             "player1_email": "p1@test.com", "player1_id": "P001",
             "player2_email": "", "player2_id": "P002"}
        ])

        msg = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "broadcast_id": "BC003",
            "payload": {"round_number": 1, "round_id": "ROUND_1"},
        }
        result = handler.handle(msg)
        assert result is None

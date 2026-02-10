# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_ASSIGNMENT_TABLE handler."""

import pytest
from q21_referee._rlgm.handler_assignment import BroadcastAssignmentTableHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastAssignmentTableHandler:
    """Tests for BroadcastAssignmentTableHandler."""

    def create_handler_in_waiting_state(self, group_id="GROUP_A"):
        """Create handler with state machine in WAITING_FOR_ASSIGNMENT."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        config = {"referee_id": "REF001", "group_id": group_id}
        handler = BroadcastAssignmentTableHandler(state_machine, config)
        return handler, state_machine

    def create_assignment_message(self):
        """Create sample assignment table message."""
        return {
            "message_type": "BROADCAST_ASSIGNMENT_TABLE",
            "broadcast_id": "BC002",
            "payload": {
                "season_id": "SEASON_2026_Q1",
                "assignments": [
                    {
                        "round_number": 1,
                        "round_id": "ROUND_1",
                        "group_id": "GROUP_A",
                        "match_id": "R1M1",
                        "player1_id": "P001",
                        "player1_email": "p1@test.com",
                        "player2_id": "P002",
                        "player2_email": "p2@test.com",
                    },
                    {
                        "round_number": 1,
                        "round_id": "ROUND_1",
                        "group_id": "GROUP_B",
                        "match_id": "R1M2",
                        "player1_id": "P003",
                        "player1_email": "p3@test.com",
                        "player2_id": "P004",
                        "player2_email": "p4@test.com",
                    },
                    {
                        "round_number": 2,
                        "round_id": "ROUND_2",
                        "group_id": "GROUP_A",
                        "match_id": "R2M1",
                        "player1_id": "P001",
                        "player1_email": "p1@test.com",
                        "player2_id": "P003",
                        "player2_email": "p3@test.com",
                    },
                ],
            },
        }

    def test_extracts_assignments_from_payload(self):
        """Test that assignments are extracted from payload."""
        handler, _ = self.create_handler_in_waiting_state()
        message = self.create_assignment_message()

        result = handler.handle(message)

        # Handler should have processed assignments
        assert result is not None

    def test_filters_by_group_id(self):
        """Test that only assignments for our group_id are kept."""
        handler, _ = self.create_handler_in_waiting_state(group_id="GROUP_A")
        message = self.create_assignment_message()

        handler.handle(message)

        # Should have 2 assignments for GROUP_A (rounds 1 and 2)
        assert len(handler.assignments) == 2
        for assignment in handler.assignments:
            assert assignment["group_id"] == "GROUP_A"

    def test_triggers_state_transition(self):
        """Test that handler triggers ASSIGNMENT_RECEIVED transition."""
        handler, state_machine = self.create_handler_in_waiting_state()
        assert state_machine.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

        handler.handle(self.create_assignment_message())

        assert state_machine.current_state == RLGMState.RUNNING

    def test_returns_acknowledgment(self):
        """Test that handler returns RESPONSE_GROUP_ASSIGNMENT."""
        handler, _ = self.create_handler_in_waiting_state()
        message = self.create_assignment_message()

        result = handler.handle(message)

        assert result is not None
        assert result["message_type"] == "RESPONSE_GROUP_ASSIGNMENT"
        assert result["payload"]["status"] == "acknowledged"
        assert result["payload"]["assignments_received"] == 2

    def test_no_matching_assignments(self):
        """Test handling when no assignments match our group."""
        handler, state_machine = self.create_handler_in_waiting_state(group_id="GROUP_Z")
        message = self.create_assignment_message()

        result = handler.handle(message)

        # Should still acknowledge but with 0 assignments
        assert result["payload"]["assignments_received"] == 0
        # State should not transition if no assignments
        assert state_machine.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

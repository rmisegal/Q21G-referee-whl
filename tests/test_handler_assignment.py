# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_ASSIGNMENT_TABLE handler.

Tests use the actual UNIFIED_PROTOCOL.md format:
- Each role (player1, player2, referee) is a separate entry
- game_id format: SSRRGGG (season, round, game number)
- Referee is identified by matching email
"""

import pytest
from q21_referee._rlgm.handler_assignment import BroadcastAssignmentTableHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastAssignmentTableHandler:
    """Tests for BroadcastAssignmentTableHandler."""

    def create_handler_in_waiting_state(self, referee_email="referee@test.com"):
        """Create handler with state machine in WAITING_FOR_ASSIGNMENT."""
        state_machine = RLGMStateMachine()
        state_machine.transition(RLGMEvent.SEASON_START)
        state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        config = {
            "referee_id": "REF001",
            "group_id": "G001",
            "referee_email": referee_email,
        }
        handler = BroadcastAssignmentTableHandler(state_machine, config)
        return handler, state_machine

    def create_assignment_message(self):
        """Create sample assignment table message per UNIFIED_PROTOCOL.md §5.6.

        Format: each role is a separate entry with game_id SSRRGGG.
        """
        return {
            "message_type": "BROADCAST_ASSIGNMENT_TABLE",
            "broadcast_id": "BC002",
            "league_id": "LEAGUE001",
            "payload": {
                "broadcast_id": "bc-assign-001",
                "season_id": "SEASON_2026_Q1",
                "league_id": "LEAGUE001",
                "assignments": [
                    # Game 0101001: Round 1, Game 1 - referee@test.com is referee
                    {"role": "player1", "email": "p1@test.com", "game_id": "0101001", "group_id": "G002"},
                    {"role": "player2", "email": "p2@test.com", "game_id": "0101001", "group_id": "G003"},
                    {"role": "referee", "email": "referee@test.com", "game_id": "0101001", "group_id": "G001"},
                    # Game 0101002: Round 1, Game 2 - different referee
                    {"role": "player1", "email": "p3@test.com", "game_id": "0101002", "group_id": "G004"},
                    {"role": "player2", "email": "p4@test.com", "game_id": "0101002", "group_id": "G005"},
                    {"role": "referee", "email": "other@test.com", "game_id": "0101002", "group_id": "G006"},
                    # Game 0102001: Round 2, Game 1 - referee@test.com is referee
                    {"role": "player1", "email": "p1@test.com", "game_id": "0102001", "group_id": "G002"},
                    {"role": "player2", "email": "p3@test.com", "game_id": "0102001", "group_id": "G004"},
                    {"role": "referee", "email": "referee@test.com", "game_id": "0102001", "group_id": "G001"},
                ],
                "total_count": 9,
                "message_text": "Season assignments are ready!",
            },
        }

    def test_extracts_assignments_from_payload(self):
        """Test that assignments are extracted from payload."""
        handler, _ = self.create_handler_in_waiting_state()
        message = self.create_assignment_message()

        result = handler.handle(message)

        # Handler should have processed assignments
        assert result is not None

    def test_filters_by_referee_email(self):
        """Test that only games where we are referee are kept."""
        handler, _ = self.create_handler_in_waiting_state(referee_email="referee@test.com")
        message = self.create_assignment_message()

        handler.handle(message)

        # Should have 2 games where referee@test.com is referee
        assert len(handler.assignments) == 2
        # Check game_ids
        game_ids = {a["game_id"] for a in handler.assignments}
        assert game_ids == {"0101001", "0102001"}

    def test_parses_round_from_game_id(self):
        """Test that round_number is parsed from game_id[2:4]."""
        handler, _ = self.create_handler_in_waiting_state()
        message = self.create_assignment_message()

        handler.handle(message)

        # Game 0101001 should be round 1, game 0102001 should be round 2
        rounds = {a["game_id"]: a["round_number"] for a in handler.assignments}
        assert rounds["0101001"] == 1
        assert rounds["0102001"] == 2

    def test_builds_complete_game_assignments(self):
        """Test that player info is aggregated into game assignments."""
        handler, _ = self.create_handler_in_waiting_state()
        message = self.create_assignment_message()

        handler.handle(message)

        # Find the round 1 game
        game_r1 = next(a for a in handler.assignments if a["game_id"] == "0101001")
        assert game_r1["player1_email"] == "p1@test.com"
        assert game_r1["player2_email"] == "p2@test.com"
        assert game_r1["player1_id"] == "G002"
        assert game_r1["player2_id"] == "G003"

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
        """Test handling when no assignments match our referee email."""
        handler, state_machine = self.create_handler_in_waiting_state(
            referee_email="unknown@test.com"
        )
        message = self.create_assignment_message()

        result = handler.handle(message)

        # Should still acknowledge but with 0 assignments
        assert result["payload"]["assignments_received"] == 0
        # State should not transition if no assignments
        assert state_machine.current_state == RLGMState.WAITING_FOR_ASSIGNMENT

    def test_get_assignment_for_round(self):
        """Test getting assignment for a specific round number."""
        handler, _ = self.create_handler_in_waiting_state()
        message = self.create_assignment_message()

        handler.handle(message)

        # Should find round 1 assignment
        r1 = handler.get_assignment_for_round(1)
        assert r1 is not None
        assert r1["game_id"] == "0101001"

        # Should find round 2 assignment
        r2 = handler.get_assignment_for_round(2)
        assert r2 is not None
        assert r2["game_id"] == "0102001"

        # Should return None for non-existent round
        r3 = handler.get_assignment_for_round(3)
        assert r3 is None

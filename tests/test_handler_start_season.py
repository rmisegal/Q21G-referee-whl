# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_START_SEASON handler."""

import pytest
from q21_referee._rlgm.handler_start_season import BroadcastStartSeasonHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMState, RLGMEvent


class TestBroadcastStartSeasonHandler:
    """Tests for BroadcastStartSeasonHandler."""

    def create_handler(self):
        """Create handler with fresh state machine."""
        state_machine = RLGMStateMachine()
        config = {
            "referee_id": "REF001",
            "referee_email": "referee@test.com",
            "group_id": "GROUP_A",
        }
        return BroadcastStartSeasonHandler(state_machine, config)

    def create_message(self, season_id="SEASON_2026_Q1", league_id="LEAGUE001"):
        """Create a sample BROADCAST_START_SEASON message."""
        return {
            "message_type": "BROADCAST_START_SEASON",
            "broadcast_id": "BC001",
            "payload": {
                "season_id": season_id,
                "league_id": league_id,
                "start_date": "2026-01-15",
            },
        }

    def test_extracts_season_id_from_payload(self):
        """Test that season_id is extracted from payload."""
        handler = self.create_handler()
        message = self.create_message(season_id="SEASON_2026_Q2")

        result = handler.handle(message)

        # Result should contain the season_id
        assert result is not None
        assert result["payload"]["season_id"] == "SEASON_2026_Q2"

    def test_uses_config_group_id_as_user_id(self):
        """Test that group_id from config becomes user_id per protocol."""
        handler = self.create_handler()
        message = self.create_message()

        result = handler.handle(message)

        assert result is not None
        assert result["payload"]["user_id"] == "GROUP_A"

    def test_triggers_state_transition(self):
        """Test that handler triggers SEASON_START transition."""
        state_machine = RLGMStateMachine()
        config = {"referee_id": "REF001", "referee_email": "ref@test.com", "group_id": "A"}
        handler = BroadcastStartSeasonHandler(state_machine, config)

        assert state_machine.current_state == RLGMState.INIT_START_STATE

        handler.handle(self.create_message())

        assert state_machine.current_state == RLGMState.WAITING_FOR_CONFIRMATION

    def test_returns_registration_request(self):
        """Test that handler returns SEASON_REGISTRATION_REQUEST."""
        handler = self.create_handler()
        message = self.create_message()

        result = handler.handle(message)

        assert result is not None
        assert result["message_type"] == "SEASON_REGISTRATION_REQUEST"
        # Protocol fields per UNIFIED_PROTOCOL.md §5.4
        assert "user_id" in result["payload"]
        assert "participant_id" in result["payload"]
        assert "display_name" in result["payload"]

    def test_registration_request_contains_protocol_fields(self):
        """Test registration request has protocol-compliant fields."""
        handler = self.create_handler()
        message = self.create_message()

        result = handler.handle(message)

        # group_id -> user_id, referee_id -> participant_id
        assert result["payload"]["user_id"] == "GROUP_A"
        assert result["payload"]["participant_id"] == "REF001"
        assert result["payload"]["display_name"] == "Q21 Referee"

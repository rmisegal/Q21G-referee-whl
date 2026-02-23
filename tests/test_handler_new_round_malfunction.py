# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for malfunction detection in BROADCAST_NEW_LEAGUE_ROUND handler."""

import pytest
from q21_referee._rlgm.handler_new_round import BroadcastNewRoundHandler
from q21_referee._rlgm.state_machine import RLGMStateMachine
from q21_referee._rlgm.enums import RLGMEvent
from q21_referee._rlgm.gprm import GPRM


def _make_handler():
    """Create handler with state machine in RUNNING state."""
    sm = RLGMStateMachine()
    sm.transition(RLGMEvent.SEASON_START)
    sm.transition(RLGMEvent.REGISTRATION_ACCEPTED)
    sm.transition(RLGMEvent.ASSIGNMENT_RECEIVED)
    config = {"season_id": "S01"}
    assignments = [
        {
            "round_number": 1,
            "game_id": "0101001",
            "player1_id": "P001",
            "player1_email": "p1@test.com",
            "player2_id": "P002",
            "player2_email": "p2@test.com",
        },
    ]
    return BroadcastNewRoundHandler(sm, config, assignments)


def _make_message(lookup_table=None, include_key=True):
    """Build a BROADCAST_NEW_LEAGUE_ROUND message.

    Args:
        lookup_table: Value for participant_lookup_table.
        include_key: If False, omit the key entirely from payload.
    """
    payload = {"round_number": 1, "round_id": "R1"}
    if include_key:
        payload["participant_lookup_table"] = lookup_table
    return {
        "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
        "broadcast_id": "bc-100",
        "payload": payload,
    }


class TestNewRoundMalfunctionDetection:
    """Tests for malfunction detection wired into handler_new_round."""

    def test_no_lookup_table_in_payload_returns_normal(self):
        """When participant_lookup_table is absent, status is NORMAL."""
        handler = _make_handler()
        result = handler.handle(_make_message(include_key=False))

        assert result is not None
        assert result["malfunction"]["status"] == "NORMAL"

    def test_lookup_table_none_returns_normal(self):
        """When participant_lookup_table is explicitly None, status NORMAL."""
        handler = _make_handler()
        result = handler.handle(_make_message(lookup_table=None))

        assert result is not None
        assert result["malfunction"]["status"] == "NORMAL"

    def test_both_players_in_lookup_table_returns_normal(self):
        """Both players present in lookup table -> NORMAL."""
        handler = _make_handler()
        table = ["p1@test.com", "p2@test.com", "other@test.com"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        assert result["malfunction"]["status"] == "NORMAL"
        assert result["malfunction"]["missing_players"] == []

    def test_player1_missing_returns_single_player(self):
        """Player1 not in lookup table -> SINGLE_PLAYER."""
        handler = _make_handler()
        table = ["p2@test.com", "other@test.com"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        mal = result["malfunction"]
        assert mal["status"] == "SINGLE_PLAYER"
        assert mal["missing_player_role"] == "player1"
        assert mal["missing_player_email"] == "p1@test.com"

    def test_player2_missing_returns_single_player(self):
        """Player2 not in lookup table -> SINGLE_PLAYER."""
        handler = _make_handler()
        table = ["p1@test.com", "other@test.com"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        mal = result["malfunction"]
        assert mal["status"] == "SINGLE_PLAYER"
        assert mal["missing_player_role"] == "player2"
        assert mal["missing_player_email"] == "p2@test.com"

    def test_both_players_missing_returns_cancelled(self):
        """Both players missing -> CANCELLED."""
        handler = _make_handler()
        table = ["other@test.com"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        mal = result["malfunction"]
        assert mal["status"] == "CANCELLED"
        assert "p1@test.com" in mal["missing_players"]
        assert "p2@test.com" in mal["missing_players"]

    def test_gprm_still_built_when_cancelled(self):
        """GPRM is built even when both players are missing (CANCELLED)."""
        handler = _make_handler()
        table = ["other@test.com"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        assert isinstance(result["gprm"], GPRM)
        assert result["gprm"].game_id == "0101001"

    def test_gprm_still_built_when_single_player(self):
        """GPRM is built even in SINGLE_PLAYER mode."""
        handler = _make_handler()
        table = ["p2@test.com"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        assert isinstance(result["gprm"], GPRM)

    def test_case_insensitive_lookup(self):
        """Lookup table matching should be case-insensitive."""
        handler = _make_handler()
        table = ["P1@TEST.COM", "P2@TEST.COM"]
        result = handler.handle(_make_message(lookup_table=table))

        assert result is not None
        assert result["malfunction"]["status"] == "NORMAL"

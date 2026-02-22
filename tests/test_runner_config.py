# Area: Shared Tests
# PRD: docs/prd-rlgm.md
"""Tests for _runner_config message type filtering."""

from q21_referee._runner_config import INCOMING_MESSAGE_TYPES


class TestIncomingMessageTypes:
    """Tests for INCOMING_MESSAGE_TYPES set."""

    def test_broadcast_critical_pause_accepted(self):
        assert "BROADCAST_CRITICAL_PAUSE" in INCOMING_MESSAGE_TYPES

    def test_broadcast_critical_reset_accepted(self):
        assert "BROADCAST_CRITICAL_RESET" in INCOMING_MESSAGE_TYPES

    def test_broadcast_round_results_accepted(self):
        assert "BROADCAST_ROUND_RESULTS" in INCOMING_MESSAGE_TYPES

    def test_existing_types_still_present(self):
        """Ensure we didn't break existing entries."""
        expected = {
            "BROADCAST_START_SEASON",
            "SEASON_REGISTRATION_RESPONSE",
            "BROADCAST_ASSIGNMENT_TABLE",
            "BROADCAST_NEW_LEAGUE_ROUND",
            "BROADCAST_END_LEAGUE_ROUND",
            "BROADCAST_END_SEASON",
            "BROADCAST_KEEP_ALIVE",
            "LEAGUE_COMPLETED",
        }
        assert expected.issubset(INCOMING_MESSAGE_TYPES)

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


from q21_referee._runner_config import is_lm_message, is_player_message


class TestIsLmMessage:
    """Tests for is_lm_message() routing function."""

    def test_league_completed_is_lm_message(self):
        """LEAGUE_COMPLETED must route as LM message, not be dropped."""
        assert is_lm_message("LEAGUE_COMPLETED") is True

    def test_broadcast_types_are_lm_messages(self):
        """All BROADCAST_* types should be LM messages."""
        assert is_lm_message("BROADCAST_START_SEASON") is True
        assert is_lm_message("BROADCAST_CRITICAL_PAUSE") is True
        assert is_lm_message("BROADCAST_ROUND_RESULTS") is True

    def test_season_registration_response_is_lm(self):
        assert is_lm_message("SEASON_REGISTRATION_RESPONSE") is True

    def test_player_messages_are_not_lm(self):
        assert is_lm_message("Q21WARMUPRESPONSE") is False
        assert is_lm_message("Q21QUESTIONSBATCH") is False


class TestIsPlayerMessage:
    """Tests for is_player_message() routing function."""

    def test_league_completed_is_not_player_message(self):
        assert is_player_message("LEAGUE_COMPLETED") is False

    def test_q21_types_are_player_messages(self):
        assert is_player_message("Q21WARMUPRESPONSE") is True
        assert is_player_message("Q21QUESTIONSBATCH") is True
        assert is_player_message("Q21GUESSSUBMISSION") is True

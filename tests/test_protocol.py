# Area: Shared Tests
# PRD: docs/prd-rlgm.md
"""Tests for protocol falsy field handling."""

from q21_referee._shared.protocol import build_envelope


class TestBuildEnvelopeFalsyFields:
    """Test that falsy but valid values are included in envelopes."""

    def test_empty_string_correlation_id_included(self):
        """Empty string correlation_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            correlation_id="",
        )
        assert "correlation_id" in env
        assert env["correlation_id"] == ""

    def test_empty_string_game_id_included(self):
        """Empty string game_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            game_id="",
        )
        assert "game_id" in env
        assert env["game_id"] == ""

    def test_empty_string_league_id_included(self):
        """Empty string league_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            league_id="",
        )
        assert "league_id" in env
        assert env["league_id"] == ""

    def test_empty_string_season_id_included(self):
        """Empty string season_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            season_id="",
        )
        assert "season_id" in env
        assert env["season_id"] == ""

    def test_empty_string_round_id_included(self):
        """Empty string round_id should be in envelope."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            round_id="",
        )
        assert "round_id" in env
        assert env["round_id"] == ""

    def test_none_fields_excluded(self):
        """None fields should NOT be in envelope (default behavior)."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
        )
        assert "correlation_id" not in env
        assert "game_id" not in env
        assert "league_id" not in env
        assert "season_id" not in env
        assert "round_id" not in env

    def test_non_empty_values_still_included(self):
        """Non-empty values should continue to work as before."""
        env = build_envelope(
            message_type="TEST", payload={},
            sender_email="ref@test.com", sender_role="REFEREE",
            correlation_id="abc-123",
            game_id="0102003",
            league_id="Q21",
            season_id="01",
            round_id="02",
        )
        assert env["correlation_id"] == "abc-123"
        assert env["game_id"] == "0102003"
        assert env["league_id"] == "Q21"
        assert env["season_id"] == "01"
        assert env["round_id"] == "02"

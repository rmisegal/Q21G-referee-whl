# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for malfunction detection from participant lookup table."""

import pytest
from q21_referee._rlgm.malfunction_detector import detect_malfunctions


class TestDetectMalfunctionsNormal:
    def test_both_players_present(self):
        lookup = ["p1@test.com", "p2@test.com", "ref@test.com"]
        result = detect_malfunctions(lookup, "p1@test.com", "p2@test.com")
        assert result["status"] == "NORMAL"
        assert result["missing_players"] == []

    def test_extra_participants_ignored(self):
        lookup = ["other@test.com", "p1@test.com", "p2@test.com"]
        result = detect_malfunctions(lookup, "p1@test.com", "p2@test.com")
        assert result["status"] == "NORMAL"


class TestDetectMalfunctionsSinglePlayer:
    def test_player1_missing(self):
        lookup = ["p2@test.com", "ref@test.com"]
        result = detect_malfunctions(lookup, "p1@test.com", "p2@test.com")
        assert result["status"] == "SINGLE_PLAYER"
        assert result["missing_player_role"] == "player1"
        assert result["missing_player_email"] == "p1@test.com"

    def test_player2_missing(self):
        lookup = ["p1@test.com", "ref@test.com"]
        result = detect_malfunctions(lookup, "p1@test.com", "p2@test.com")
        assert result["status"] == "SINGLE_PLAYER"
        assert result["missing_player_role"] == "player2"
        assert result["missing_player_email"] == "p2@test.com"


class TestDetectMalfunctionsCancelled:
    def test_both_players_missing(self):
        lookup = ["ref@test.com"]
        result = detect_malfunctions(lookup, "p1@test.com", "p2@test.com")
        assert result["status"] == "CANCELLED"
        assert len(result["missing_players"]) == 2

    def test_empty_lookup_table(self):
        result = detect_malfunctions([], "p1@test.com", "p2@test.com")
        assert result["status"] == "CANCELLED"


class TestDetectMalfunctionsEdgeCases:
    def test_none_lookup_table(self):
        result = detect_malfunctions(None, "p1@test.com", "p2@test.com")
        assert result["status"] == "NORMAL"

    def test_case_insensitive_emails(self):
        lookup = ["P1@TEST.COM", "p2@test.com"]
        result = detect_malfunctions(lookup, "p1@test.com", "P2@Test.Com")
        assert result["status"] == "NORMAL"

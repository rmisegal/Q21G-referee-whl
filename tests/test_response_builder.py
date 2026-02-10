# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM Response Builder."""

import pytest
from q21_referee._rlgm.response_builder import RLGMResponseBuilder
from q21_referee._rlgm.game_result import GameResult, PlayerScore


class TestRLGMResponseBuilder:
    """Tests for RLGMResponseBuilder class."""

    def create_builder(self):
        """Create builder with sample config."""
        config = {
            "referee_id": "REF001",
            "referee_email": "referee@test.com",
            "group_id": "GROUP_A",
            "league_id": "LEAGUE001",
        }
        return RLGMResponseBuilder(config)

    def test_build_registration_request_structure(self):
        """Test registration request has protocol-compliant structure per §5.4."""
        builder = self.create_builder()

        result = builder.build_registration_request(
            season_id="SEASON_2026_Q1",
            league_id="LEAGUE001",
        )

        assert result["message_type"] == "SEASON_REGISTRATION_REQUEST"
        assert "payload" in result
        # Protocol fields per UNIFIED_PROTOCOL.md §5.4
        assert result["payload"]["season_id"] == "SEASON_2026_Q1"
        assert result["payload"]["user_id"] == "GROUP_A"  # from group_id
        assert result["payload"]["participant_id"] == "REF001"  # from referee_id
        assert result["payload"]["display_name"] == "Q21 Referee"

    def test_build_group_assignment_response_structure(self):
        """Test that group assignment response has correct structure."""
        builder = self.create_builder()

        result = builder.build_group_assignment_response(
            season_id="SEASON_2026_Q1",
            assignments_received=5,
        )

        assert result["message_type"] == "RESPONSE_GROUP_ASSIGNMENT"
        assert "payload" in result
        assert result["payload"]["status"] == "acknowledged"
        assert result["payload"]["season_id"] == "SEASON_2026_Q1"
        assert result["payload"]["referee_id"] == "REF001"
        assert result["payload"]["group_id"] == "GROUP_A"
        assert result["payload"]["assignments_received"] == 5

    def test_build_match_result_report_structure(self):
        """Test that match result report has correct structure."""
        builder = self.create_builder()

        player1 = PlayerScore(
            player_id="P001",
            player_email="p1@test.com",
            score=21,
            questions_answered=10,
            correct_answers=8,
        )
        player2 = PlayerScore(
            player_id="P002",
            player_email="p2@test.com",
            score=15,
            questions_answered=10,
            correct_answers=6,
        )
        game_result = GameResult(
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            season_id="SEASON_2026_Q1",
            player1=player1,
            player2=player2,
            winner_id="P001",
            is_draw=False,
        )

        result = builder.build_match_result_report(game_result)

        assert result["message_type"] == "MATCH_RESULT_REPORT"
        assert "payload" in result
        payload = result["payload"]
        assert payload["game_id"] == "0101001"
        assert payload["match_id"] == "R1M1"
        assert payload["round_id"] == "ROUND_1"
        assert payload["winner_id"] == "P001"
        assert payload["is_draw"] is False
        assert "player1" in payload
        assert "player2" in payload
        assert payload["player1"]["score"] == 21
        assert payload["player2"]["score"] == 15

    def test_build_match_result_report_with_draw(self):
        """Test match result report for a draw."""
        builder = self.create_builder()

        player1 = PlayerScore(
            player_id="P001",
            player_email="p1@test.com",
            score=18,
            questions_answered=10,
            correct_answers=7,
        )
        player2 = PlayerScore(
            player_id="P002",
            player_email="p2@test.com",
            score=18,
            questions_answered=10,
            correct_answers=7,
        )
        game_result = GameResult(
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            season_id="SEASON_2026_Q1",
            player1=player1,
            player2=player2,
            winner_id=None,
            is_draw=True,
        )

        result = builder.build_match_result_report(game_result)

        assert result["payload"]["winner_id"] is None
        assert result["payload"]["is_draw"] is True

    def test_build_keep_alive_response(self):
        """Test that keep-alive response has correct structure."""
        builder = self.create_builder()

        result = builder.build_keep_alive_response()

        assert result["message_type"] == "RESPONSE_KEEP_ALIVE"
        assert result["payload"]["referee_id"] == "REF001"
        assert result["payload"]["status"] == "alive"

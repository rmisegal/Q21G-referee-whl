# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for GameResult and PlayerScore dataclasses."""

import pytest
from q21_referee._rlgm.game_result import GameResult, PlayerScore


class TestPlayerScore:
    """Tests for PlayerScore dataclass."""

    def test_player_score_creation(self):
        """Test that PlayerScore can be created with all fields."""
        score = PlayerScore(
            player_id="P001",
            player_email="player1@test.com",
            score=21,
            questions_answered=10,
            correct_answers=8,
        )
        assert score.player_id == "P001"
        assert score.player_email == "player1@test.com"
        assert score.score == 21
        assert score.questions_answered == 10
        assert score.correct_answers == 8


class TestGameResult:
    """Tests for GameResult dataclass."""

    def test_game_result_creation(self):
        """Test that GameResult can be created with winner."""
        player1_score = PlayerScore(
            player_id="P001",
            player_email="player1@test.com",
            score=21,
            questions_answered=10,
            correct_answers=8,
        )
        player2_score = PlayerScore(
            player_id="P002",
            player_email="player2@test.com",
            score=15,
            questions_answered=10,
            correct_answers=6,
        )
        result = GameResult(
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            season_id="SEASON_2026_Q1",
            player1=player1_score,
            player2=player2_score,
            winner_id="P001",
            is_draw=False,
        )
        assert result.game_id == "0101001"
        assert result.match_id == "R1M1"
        assert result.round_id == "ROUND_1"
        assert result.season_id == "SEASON_2026_Q1"
        assert result.player1.player_id == "P001"
        assert result.player2.player_id == "P002"
        assert result.winner_id == "P001"
        assert result.is_draw is False

    def test_game_result_with_draw(self):
        """Test that GameResult can represent a draw."""
        player1_score = PlayerScore(
            player_id="P001",
            player_email="player1@test.com",
            score=18,
            questions_answered=10,
            correct_answers=7,
        )
        player2_score = PlayerScore(
            player_id="P002",
            player_email="player2@test.com",
            score=18,
            questions_answered=10,
            correct_answers=7,
        )
        result = GameResult(
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            season_id="SEASON_2026_Q1",
            player1=player1_score,
            player2=player2_score,
            winner_id=None,
            is_draw=True,
        )
        assert result.winner_id is None
        assert result.is_draw is True
        assert result.player1.score == result.player2.score

    def test_game_result_defaults_to_completed(self):
        """Test that GameResult defaults to status='completed'."""
        player1_score = PlayerScore(
            player_id="P001", player_email="p1@test.com",
            score=21, questions_answered=10, correct_answers=8,
        )
        player2_score = PlayerScore(
            player_id="P002", player_email="p2@test.com",
            score=15, questions_answered=10, correct_answers=6,
        )
        result = GameResult(
            game_id="0101001", match_id="R1M1",
            round_id="ROUND_1", season_id="S01",
            player1=player1_score, player2=player2_score,
            winner_id="P001", is_draw=False,
        )
        assert result.status == "completed"
        assert result.abort_reason is None
        assert result.player_states is None

    def test_game_result_aborted(self):
        """Test that GameResult can represent an aborted game."""
        player1_score = PlayerScore(
            player_id="P001", player_email="p1@test.com",
            score=0, questions_answered=0, correct_answers=0,
        )
        player2_score = PlayerScore(
            player_id="P002", player_email="p2@test.com",
            score=0, questions_answered=0, correct_answers=0,
        )
        player_states = {
            "player1": {
                "phase_reached": "warmup_answered",
                "scored": False,
                "last_actor": "player1",
            },
            "player2": {
                "phase_reached": "idle",
                "scored": False,
                "last_actor": "referee",
            },
        }
        result = GameResult(
            game_id="0101001", match_id="R1M1",
            round_id="ROUND_1", season_id="S01",
            player1=player1_score, player2=player2_score,
            winner_id=None, is_draw=True,
            status="aborted",
            abort_reason="new_round_started",
            player_states=player_states,
        )
        assert result.status == "aborted"
        assert result.abort_reason == "new_round_started"
        assert result.player_states["player1"]["last_actor"] == "player1"
        assert result.player_states["player2"]["phase_reached"] == "idle"

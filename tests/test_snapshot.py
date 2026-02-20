# Area: GMC
# PRD: docs/prd-rlgm.md
"""Tests for q21_referee._gmc.snapshot — state snapshot builder."""

from q21_referee._gmc.snapshot import build_state_snapshot
from q21_referee._gmc.state import GameState, PlayerState, GamePhase


def test_snapshot_with_both_players():
    """Snapshot should include both players when both are present."""
    state = GameState(
        game_id="0101001", match_id="0101001",
        season_id="S01", league_id="L01",
    )
    state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
    state.player2 = PlayerState(email="p2@test.com", participant_id="P002")

    result = build_state_snapshot("0101001", state)

    assert result["game_id"] == "0101001"
    assert result["player1"]["email"] == "p1@test.com"
    assert result["player2"]["email"] == "p2@test.com"


def test_snapshot_with_none_player():
    """Snapshot should handle None player gracefully."""
    state = GameState(
        game_id="0101001", match_id="0101001",
        season_id="S01", league_id="L01",
    )
    state.player1 = PlayerState(email="p1@test.com", participant_id="P001")
    state.player2 = None

    result = build_state_snapshot("0101001", state)

    assert result["player1"]["email"] == "p1@test.com"
    assert result["player2"]["phase_reached"] == "not_initialized"
    assert result["player2"]["scored"] is False


def test_snapshot_with_both_players_none():
    """Snapshot should handle both players being None."""
    state = GameState(
        game_id="0101001", match_id="0101001",
        season_id="S01", league_id="L01",
    )
    state.player1 = None
    state.player2 = None

    result = build_state_snapshot("0101001", state)

    assert result["player1"]["phase_reached"] == "not_initialized"
    assert result["player1"]["scored"] is False
    assert result["player2"]["phase_reached"] == "not_initialized"
    assert result["player2"]["scored"] is False

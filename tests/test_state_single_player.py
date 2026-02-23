# Area: GMC
# PRD: docs/prd-rlgm.md
"""
Tests for single-player mode fields and active_players() on GameState.
"""

import pytest

from q21_referee._gmc.state import GameState, GamePhase, PlayerState


def _make_state(**kwargs):
    """Create a GameState with sensible defaults."""
    defaults = dict(
        game_id="0101001", match_id="0101001",
        season_id="S01", league_id="L01",
    )
    defaults.update(kwargs)
    return GameState(**defaults)


def _player1():
    return PlayerState(email="p1@test.com", participant_id="P001")


def _player2():
    return PlayerState(email="p2@test.com", participant_id="P002")


class TestActivePlayersNormalMode:
    """active_players() when single_player_mode is False (default)."""

    def test_both_players_returned(self):
        state = _make_state()
        state.player1 = _player1()
        state.player2 = _player2()
        active = state.active_players()
        assert len(active) == 2
        assert state.player1 in active
        assert state.player2 in active

    def test_none_player_excluded(self):
        state = _make_state()
        state.player1 = _player1()
        state.player2 = None
        active = state.active_players()
        assert len(active) == 1
        assert state.player1 in active

    def test_no_players_returns_empty(self):
        state = _make_state()
        assert state.active_players() == []


class TestActivePlayersSinglePlayerMode:
    """active_players() when single_player_mode is True."""

    def test_missing_player1_excludes_player1(self):
        state = _make_state(
            single_player_mode=True,
            missing_player_role="player1",
            missing_player_email="ghost@test.com",
        )
        state.player1 = _player1()
        state.player2 = _player2()
        active = state.active_players()
        assert len(active) == 1
        assert state.player2 in active
        assert state.player1 not in active

    def test_missing_player2_excludes_player2(self):
        state = _make_state(
            single_player_mode=True,
            missing_player_role="player2",
            missing_player_email="ghost@test.com",
        )
        state.player1 = _player1()
        state.player2 = _player2()
        active = state.active_players()
        assert len(active) == 1
        assert state.player1 in active
        assert state.player2 not in active

    def test_missing_player1_when_player2_none(self):
        """Edge case: missing player1, and player2 is also None."""
        state = _make_state(
            single_player_mode=True,
            missing_player_role="player1",
        )
        state.player1 = _player1()
        state.player2 = None
        assert state.active_players() == []

    def test_returns_list_not_generator(self):
        state = _make_state(
            single_player_mode=True,
            missing_player_role="player1",
        )
        state.player1 = _player1()
        state.player2 = _player2()
        result = state.active_players()
        assert isinstance(result, list)


class TestBothChecksSinglePlayer:
    """both_*() helpers work correctly in single-player mode."""

    def _single_player_state(self):
        state = _make_state(
            single_player_mode=True,
            missing_player_role="player1",
        )
        state.player1 = _player1()
        state.player2 = _player2()
        return state

    def test_warmups_received_with_one_player(self):
        state = self._single_player_state()
        assert state.both_warmups_received() is False
        state.player2.warmup_answer = "hello"
        assert state.both_warmups_received() is True

    def test_answers_sent_with_one_player(self):
        state = self._single_player_state()
        assert state.both_answers_sent() is False
        state.player2.answers_sent = True
        assert state.both_answers_sent() is True

    def test_scores_sent_with_one_player(self):
        state = self._single_player_state()
        assert state.both_scores_sent() is False
        state.player2.score_sent = True
        assert state.both_scores_sent() is True

    def test_no_active_players_returns_false(self):
        """Edge: single-player mode but no active players left."""
        state = _make_state(
            single_player_mode=True,
            missing_player_role="player1",
        )
        state.player1 = _player1()
        state.player2 = None
        assert state.both_warmups_received() is False
        assert state.both_answers_sent() is False
        assert state.both_scores_sent() is False

# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.snapshot — Game state snapshot builder
=======================================================

Builds serializable per-player state snapshots for abort reporting.
"""

from .state import GameState, GamePhase, PlayerState


def build_state_snapshot(game_id: str, state: GameState) -> dict:
    """Build serializable per-player state snapshot."""
    return {
        "game_id": game_id,
        "phase": state.phase.value,
        "player1": _player_snapshot(state, state.player1) if state.player1 else _empty_snapshot(),
        "player2": _player_snapshot(state, state.player2) if state.player2 else _empty_snapshot(),
    }


def _empty_snapshot() -> dict:
    """Return a placeholder snapshot for a player that is not yet initialized."""
    return {
        "email": "", "participant_id": "",
        "phase_reached": "not_initialized", "scored": False,
        "last_actor": "none",
    }


def _player_snapshot(state: GameState, player: PlayerState) -> dict:
    """Build snapshot for one player."""
    phase_reached = _determine_phase_reached(state, player)
    last_actor = _determine_last_actor(player, phase_reached)
    return {
        "email": player.email,
        "participant_id": player.participant_id,
        "phase_reached": phase_reached,
        "scored": player.score_sent,
        "last_actor": last_actor,
    }


def _determine_phase_reached(state: GameState, player: PlayerState) -> str:
    """Determine the furthest phase a player has reached."""
    if player.score_sent:
        return "scored"
    if player.guess is not None:
        return "guess_submitted"
    if player.answers_sent:
        return "answers_received"
    if player.questions is not None:
        return "questions_submitted"
    if player.warmup_answer is not None:
        return "warmup_answered"
    phase = state.phase
    if phase in (GamePhase.WARMUP_SENT, GamePhase.WARMUP_COMPLETE):
        return "warmup_sent"
    if phase in (GamePhase.ROUND_STARTED, GamePhase.QUESTIONS_COLLECTING):
        return "round_started"
    return "idle"


def _determine_last_actor(player: PlayerState, phase_reached: str) -> str:
    """Determine who acted last for this player.

    Returns 'referee' if referee was last to send to this player,
    or the player's participant_id if the player last acted.
    """
    player_acted_phases = {
        "warmup_answered", "questions_submitted", "guess_submitted",
    }
    if phase_reached in player_acted_phases:
        return player.participant_id
    return "referee"

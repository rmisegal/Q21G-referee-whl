# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
runner_protocol_context — Protocol logger context management
=============================================================

Pure functions extracted from RLGMRunner to manage protocol logger
game_id and role context before/after message routing.
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import RLGMOrchestrator
    from .._shared.protocol_logger import ProtocolLogger

logger = logging.getLogger("q21_referee")

# Season-level message types (use 0199999, empty role)
SEASON_LEVEL_MESSAGES = {
    "BROADCAST_START_SEASON",
    "SEASON_REGISTRATION_RESPONSE",
    "BROADCAST_ASSIGNMENT_TABLE",
    "LEAGUE_COMPLETED",
    "MATCH_RESULT_REPORT",
}


def find_assignment_for_round(
    orchestrator: RLGMOrchestrator, round_number: int
) -> dict:
    """Find assignment for the given round number."""
    for assignment in orchestrator.get_assignments():
        if assignment.get("round_number") == round_number:
            return assignment
    return {}


def update_context_before_routing(
    orchestrator: RLGMOrchestrator,
    message_type: str,
    body: dict,
    protocol_logger: ProtocolLogger,
) -> None:
    """Update protocol logger context BEFORE routing (for RECEIVED log).

    Game ID format: SSRRGGG (SS=season always "01", RR=round, GGG=game)
    - Season-level messages: 0199999 (RR=99 -> empty role)
    - Round-level (START-ROUND): 01RR999 (ACTIVE/INACTIVE based on assignment)
    - Game-level (active game): 01RRGGG (ACTIVE)
    """
    # If we have an active game, use its context (game-level)
    if orchestrator.current_game:
        gprm = orchestrator.current_game.gprm
        if gprm and gprm.game_id:
            protocol_logger.set_game_id(gprm.game_id)
            protocol_logger.set_role_active(True)
            return

    # Season-level messages: 0199999, role will be empty (RR=99)
    if message_type in SEASON_LEVEL_MESSAGES:
        protocol_logger.set_game_id("0199999")
        protocol_logger.set_role_active(False)
        return

    # Round-level: BROADCAST_NEW_LEAGUE_ROUND
    if message_type == "BROADCAST_NEW_LEAGUE_ROUND":
        payload = body.get("payload") or {}
        round_number = payload.get("round_number")
        if not isinstance(round_number, int):
            logger.warning(
                f"Invalid round_number in payload: {round_number}, "
                "defaulting to 0"
            )
            round_number = 0

        assignment = find_assignment_for_round(orchestrator, round_number)
        if assignment:
            game_id = assignment.get("game_id", "")
            if game_id:
                protocol_logger.set_game_id(game_id)
                protocol_logger.set_role_active(True)
                return

        # Not assigned - build placeholder game_id: 01RR999 (no game)
        game_id = f"01{round_number:02d}999"
        protocol_logger.set_game_id(game_id)
        protocol_logger.set_role_active(False)
        return

    # Default fallback for unknown message types
    protocol_logger.set_game_id("0199999")
    protocol_logger.set_role_active(False)


def update_context_after_routing(
    orchestrator: RLGMOrchestrator,
    protocol_logger: ProtocolLogger,
) -> None:
    """Update protocol logger context AFTER routing (for SENT logs)."""
    if orchestrator.current_game:
        gprm = orchestrator.current_game.gprm
        if gprm and gprm.game_id:
            protocol_logger.set_game_id(gprm.game_id)
            protocol_logger.set_role_active(True)

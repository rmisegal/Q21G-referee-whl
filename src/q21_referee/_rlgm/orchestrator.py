# Area: RLGM
# PRD: docs/prd-rlgm.md
"""Orchestrator — coordinates handlers, state machine, and GMC."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from .state_machine import RLGMStateMachine
from .broadcast_router import BroadcastRouter
from .response_builder import RLGMResponseBuilder
from .handler_start_season import BroadcastStartSeasonHandler
from .handler_registration_response import SeasonRegistrationResponseHandler
from .handler_assignment import BroadcastAssignmentTableHandler
from .handler_new_round import BroadcastNewRoundHandler
from .handler_end_round import BroadcastEndRoundHandler
from .handler_end_season import BroadcastEndSeasonHandler
from .handler_keep_alive import BroadcastKeepAliveHandler
from .handler_critical_pause import BroadcastCriticalPauseHandler
from .handler_critical_reset import BroadcastCriticalResetHandler
from .handler_round_results import BroadcastRoundResultsHandler
from .gprm import GPRM
from .enums import RLGMEvent
from .warmup_initiator import initiate_warmup
from .abort_handler import build_abort_report
from .cancel_report import build_cancel_report
from .._gmc.gmc import GameManagementCycle
from .._gmc.incoming_validator import validate_player_message
from ..callbacks import RefereeAI

logger = logging.getLogger("q21_referee.rlgm.orchestrator")
Msgs = List[Tuple[dict, str, str]]

class RLGMOrchestrator:
    def __init__(self, config: Dict[str, Any], ai: RefereeAI):
        self.config, self.ai = config, ai
        self.state_machine = RLGMStateMachine()
        self.response_builder = RLGMResponseBuilder(config)
        self.router = BroadcastRouter()
        self.current_game: Optional[GameManagementCycle] = None
        self.current_round_number: Optional[int] = None
        self._assignments: List[Dict[str, Any]] = []
        self._pending_outgoing: Msgs = []
        self._processed_broadcasts: set = set()
        self._register_handlers()
    def _register_handlers(self) -> None:
        reg = self.router.register_handler
        reg("BROADCAST_START_SEASON", BroadcastStartSeasonHandler(self.state_machine, self.config))
        reg("SEASON_REGISTRATION_RESPONSE", SeasonRegistrationResponseHandler(self.state_machine))
        self._assignment_handler = BroadcastAssignmentTableHandler(self.state_machine, self.config)
        reg("BROADCAST_ASSIGNMENT_TABLE", self._assignment_handler)
        self._new_round_handler = BroadcastNewRoundHandler(self.state_machine, self.config, self._assignments)
        reg("BROADCAST_NEW_LEAGUE_ROUND", self._new_round_handler)
        self._end_round_handler = BroadcastEndRoundHandler(self.state_machine)
        reg("BROADCAST_END_LEAGUE_ROUND", self._end_round_handler)
        reg("BROADCAST_END_SEASON", BroadcastEndSeasonHandler(self.state_machine))
        reg("LEAGUE_COMPLETED", BroadcastEndSeasonHandler(self.state_machine))
        reg("BROADCAST_KEEP_ALIVE", BroadcastKeepAliveHandler(self.config, self.response_builder))
        reg("BROADCAST_CRITICAL_PAUSE", BroadcastCriticalPauseHandler(self.state_machine))
        reg("BROADCAST_CRITICAL_RESET", BroadcastCriticalResetHandler(self.state_machine))
        reg("BROADCAST_ROUND_RESULTS", BroadcastRoundResultsHandler())
    def handle_lm_message(self, message: Dict[str, Any]) -> Optional[Dict]:
        msg_type, bid = message.get("message_type", ""), message.get("broadcast_id")
        if bid and bid in self._processed_broadcasts:
            return None
        logger.info("LM message: %s", msg_type)
        result = self.router.route(message)
        if msg_type == "BROADCAST_ASSIGNMENT_TABLE":
            self._assignments = self._assignment_handler.assignments
            self._new_round_handler.assignments = self._assignments
        if msg_type == "BROADCAST_NEW_LEAGUE_ROUND" and result:
            self._pending_outgoing.extend(self._handle_new_round(result))
            return None
        if msg_type == "BROADCAST_END_LEAGUE_ROUND" and result:
            if result.get("abort_signal"):
                self._pending_outgoing.extend(self.abort_current_game("end_round_received"))
            return None
        if msg_type == "LEAGUE_COMPLETED":
            self._pending_outgoing.extend(self.abort_current_game("league_completed"))
        if bid:
            self._processed_broadcasts.add(bid)
        return result
    def get_pending_outgoing(self) -> Msgs:
        msgs, self._pending_outgoing = self._pending_outgoing, []
        return msgs
    def _handle_new_round(self, result: dict) -> Msgs:
        gprm = result.get("gprm")
        if not gprm:
            return []
        malf = result.get("malfunction", {})
        if malf.get("status") == "CANCELLED":
            return build_cancel_report(gprm, self.config)
        sp = malf.get("status") == "SINGLE_PLAYER"
        mr = malf.get("missing_player_role") if sp else None
        return self.start_round(gprm, single_player_mode=sp, missing_player_role=mr)
    def start_round(self, gprm: GPRM, single_player_mode: bool = False,
                    missing_player_role: str = None) -> Msgs:
        if self.current_round_number == gprm.round_number:
            logger.info("Round %d already active, skipping", gprm.round_number)
            return []
        outgoing: Msgs = []
        if self.current_game is not None:
            logger.info("Aborting round %s for round %s", self.current_round_number, gprm.round_number)
            outgoing.extend(self.abort_current_game("new_round_started"))
        self.current_round_number = self._end_round_handler.current_round_number = gprm.round_number
        self.current_game = GameManagementCycle(
            gprm=gprm, ai=self.ai, config=self.config,
            single_player_mode=single_player_mode,
            missing_player_role=missing_player_role)
        outgoing.extend(initiate_warmup(self.current_game, gprm, self.ai, self.config))
        return outgoing
    def abort_current_game(self, reason: str) -> Msgs:
        if not self.current_game:
            return []
        outgoing = build_abort_report(self.current_game, reason, self.ai, self.config)
        self.current_game = None
        if self.state_machine.can_transition(RLGMEvent.GAME_ABORTED):
            self.state_machine.transition(RLGMEvent.GAME_ABORTED)
        return outgoing
    def check_deadlines(self) -> Msgs:
        """Check for expired player response deadlines; abort game if found."""
        if not self.current_game:
            return []
        expired = self.current_game.deadline_tracker.check_expired()
        if expired:
            player = expired[0]["player_email"]
            logger.warning("Player timeout: %s", player)
            return self.abort_current_game(f"player_timeout:{player}")
        return []
    def route_player_message(self, message_type: str, body: dict,
                             sender_email: str) -> Msgs:
        if not self.current_game:
            logger.warning("No active game for player message")
            return []
        errors = validate_player_message(body)
        if errors:
            logger.warning("Format violation from %s: %s", sender_email, errors)
            return self.abort_current_game(f"format_violation:{sender_email}")
        incoming_game_id = body.get("game_id")
        if incoming_game_id and incoming_game_id != self.current_game.gprm.game_id:
            logger.warning("game_id mismatch: got %s, expected %s", incoming_game_id, self.current_game.gprm.game_id)
            return []
        outgoing = self.current_game.route_message(message_type, body, sender_email)
        if self.current_game.is_complete():
            self.complete_game()
        return outgoing
    def complete_game(self) -> None:
        if not self.current_game:
            return
        if self.current_game.get_result():
            self.state_machine.transition(RLGMEvent.GAME_COMPLETE, force=True)
        self.current_game = None
    def get_assignments(self) -> List[Dict[str, Any]]: return self._assignments

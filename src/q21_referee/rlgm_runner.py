# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee.rlgm_runner — RLGM-aware Runner
============================================

Runner that uses RLGM orchestrator for multi-game season management.
"""

from __future__ import annotations
import time
import logging
import signal
from typing import Dict, Any, List, Tuple

from .callbacks import RefereeAI
from ._shared import (
    EmailClient,
    setup_logging,
    build_subject,
    enable_protocol_mode,
    get_protocol_logger,
)
from ._rlgm.orchestrator import RLGMOrchestrator
from ._runner_config import (
    INCOMING_MESSAGE_TYPES,
    validate_config,
    is_lm_message,
    is_player_message,
)

logger = logging.getLogger("q21_referee")


class RLGMRunner:
    """
    RLGM-aware runner for season management.

    Routes League Manager messages to RLGM orchestrator and
    player messages to the current active game.
    """

    def __init__(self, config: Dict[str, Any], ai: RefereeAI):
        self.config = config
        self.ai = ai
        self._running = False

        # Setup logging
        log_file = config.get("log_file", "q21_referee.log")
        setup_logging(log_file_path=log_file)

        # Validate config
        validate_config(config)

        # Build email client (OAuth-based)
        self.email_client = EmailClient(
            credentials_path=config.get("credentials_path", ""),
            token_path=config.get("token_path", ""),
        )

        # Build RLGM orchestrator
        self.orchestrator = RLGMOrchestrator(config=config, ai=ai)

        self.poll_interval = config.get("poll_interval_seconds", 5)

        # Enable protocol logging mode (suppresses standard logs on terminal)
        enable_protocol_mode()
        self._protocol_logger = get_protocol_logger()

    def run(self) -> None:
        """Start the RLGM event loop. Blocks until interrupted."""
        self._running = True
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, "_running", False))

        self._log_startup()
        self.email_client.connect_imap()

        # Update config with actual email address from Gmail API
        if self.email_client.address:
            self.config["referee_email"] = self.email_client.address

        while self._running:
            try:
                self._poll_and_process()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                time.sleep(self.poll_interval)

        self.email_client.disconnect_imap()
        logger.info("RLGM Runner stopped.")

    def _log_startup(self) -> None:
        """Log startup information."""
        logger.info("=" * 60)
        logger.info("  Q21 RLGM Runner — Starting")
        logger.info(f"  Email: {self.email_client.address or 'connecting...'}")
        logger.info(f"  Group: {self.config.get('group_id', 'N/A')}")
        logger.info(f"  Poll:  every {self.poll_interval}s")
        logger.info("=" * 60)

    def _poll_and_process(self) -> None:
        """Single poll iteration: get emails → route → send."""
        for msg in self.email_client.poll():
            subject = msg.get("subject", "")
            from_addr = msg.get("from", "")
            body = msg.get("body_json")

            if not body:
                logger.debug(f"Skipped (no JSON): {subject} from {from_addr}")
                continue

            message_type = body.get("message_type") or ""
            sender_dict = body.get("sender") or {}
            sender = sender_dict.get("email") or from_addr or "unknown"

            if message_type not in INCOMING_MESSAGE_TYPES:
                logger.debug(f"Skipped (unknown type '{message_type}'): {subject}")
                continue

            logger.debug(f"── Received: {message_type} from {sender}")

            try:
                # Update context BEFORE routing so RECEIVED log has correct context
                self._update_protocol_logger_context(message_type, body)

                # Log the received message with current context
                self._protocol_logger.log_received(email=sender, message_type=message_type)

                # Route the message (may create a game, updating context)
                outgoing = self._route_message(message_type, body, sender)

                # Update context again after routing (game may have been created)
                self._update_protocol_logger_context_after_routing()

                self._send_messages(outgoing)
            except Exception as e:
                logger.error(f"Router error: {e}", exc_info=True)
                self._protocol_logger.log_error(str(e))

    def _route_message(
        self, message_type: str, body: dict, sender: str
    ) -> List[Tuple[dict, str, str]]:
        """Route message to appropriate handler."""
        outgoing = []

        if is_lm_message(message_type):
            result = self.orchestrator.handle_lm_message(body)
            if result:
                lm_email = self.config.get("league_manager_email", "")
                # Build protocol-compliant subject
                response_type = result.get("message_type", "RESPONSE")
                referee_email = self.email_client.address or ""
                # Use message_id if present, otherwise generate new tx_id
                tx_id = result.get("message_id") or None
                subject = build_subject(
                    role="REFEREE",
                    email=referee_email,
                    message_type=response_type,
                    tx_id=tx_id,
                )
                outgoing.append((result, subject, lm_email))

            # Check for pending player messages (e.g., warmup calls after new round)
            outgoing.extend(self.orchestrator.get_pending_outgoing())

        elif is_player_message(message_type):
            outgoing = self.orchestrator.route_player_message(message_type, body, sender)

        return outgoing

    # Season-level message types (use 0199999, empty role)
    SEASON_LEVEL_MESSAGES = {
        "BROADCAST_START_SEASON",
        "SEASON_REGISTRATION_RESPONSE",
        "BROADCAST_ASSIGNMENT_TABLE",
        "LEAGUE_COMPLETED",
        "MATCH_RESULT_REPORT",
    }

    def _update_protocol_logger_context(
        self, message_type: str, body: dict
    ) -> None:
        """Update protocol logger context BEFORE routing (for RECEIVED log).

        Game ID format: SSRRGGG (SS=season always "01", RR=round, GGG=game)
        - Season-level messages: 0199999 (RR=99 → empty role)
        - Round-level (START-ROUND): 01RR999 (ACTIVE/INACTIVE based on assignment)
        - Game-level (active game): 01RRGGG (ACTIVE)
        """
        # If we have an active game, use its context (game-level)
        if self.orchestrator.current_game:
            gprm = self.orchestrator.current_game.gprm
            if gprm and gprm.game_id:
                self._protocol_logger.set_game_id(gprm.game_id)
                self._protocol_logger.set_role_active(True)
                return

        # Season-level messages: 0199999, role will be empty (RR=99)
        if message_type in self.SEASON_LEVEL_MESSAGES:
            self._protocol_logger.set_game_id("0199999")
            self._protocol_logger.set_role_active(False)
            return

        # Round-level: BROADCAST_NEW_LEAGUE_ROUND
        if message_type == "BROADCAST_NEW_LEAGUE_ROUND":
            payload = body.get("payload") or {}
            round_number = payload.get("round_number")
            if not isinstance(round_number, int):
                logger.warning(f"Invalid round_number in payload: {round_number}, defaulting to 0")
                round_number = 0

            # Check if we have an assignment for this round
            assignment = self._find_assignment_for_round(round_number)
            if assignment:
                # We're assigned - use game_id from assignment
                game_id = assignment.get("game_id", "")
                if game_id:
                    self._protocol_logger.set_game_id(game_id)
                    self._protocol_logger.set_role_active(True)
                    return

            # Not assigned - build placeholder game_id: 01RR999 (no game)
            game_id = f"01{round_number:02d}999"
            self._protocol_logger.set_game_id(game_id)
            self._protocol_logger.set_role_active(False)
            return

        # Default fallback for unknown message types
        self._protocol_logger.set_game_id("0199999")
        self._protocol_logger.set_role_active(False)

    def _find_assignment_for_round(self, round_number: int) -> dict:
        """Find assignment for the given round number."""
        for assignment in self.orchestrator.get_assignments():
            if assignment.get("round_number") == round_number:
                return assignment
        return {}

    def _update_protocol_logger_context_after_routing(self) -> None:
        """Update protocol logger context AFTER routing (for SENT logs)."""
        # If a game was created during routing, use its context
        if self.orchestrator.current_game:
            gprm = self.orchestrator.current_game.gprm
            if gprm and gprm.game_id:
                self._protocol_logger.set_game_id(gprm.game_id)
                self._protocol_logger.set_role_active(True)

    def _send_messages(self, outgoing: List[Tuple[dict, str, str]]) -> None:
        """Send outgoing messages."""
        for envelope, subject, recipient in outgoing:
            self.email_client.send(recipient, subject, envelope)

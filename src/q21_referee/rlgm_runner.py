# Area: RLGM
# PRD: docs/prd-rlgm.md
"""RLGM-aware Runner for multi-game season management."""
from __future__ import annotations
import time, logging, signal
from typing import Dict, Any, List, Tuple
from .callbacks import RefereeAI
from ._shared import (
    EmailClient, setup_logging, build_subject,
    enable_protocol_mode, get_protocol_logger,
)
from ._rlgm.orchestrator import RLGMOrchestrator
from ._rlgm.runner_protocol_context import (
    update_context_before_routing, update_context_after_routing,
)
from ._runner_config import (
    INCOMING_MESSAGE_TYPES, validate_config, is_lm_message, is_player_message,
)

logger = logging.getLogger("q21_referee")


class RLGMRunner:
    """Routes LM messages to RLGM orchestrator, player messages to active game."""

    def __init__(self, config: Dict[str, Any], ai: RefereeAI):
        self.config, self.ai = config, ai
        self._running = False
        setup_logging(log_file_path=config.get("log_file", "q21_referee.log"))
        validate_config(config)
        self.email_client = EmailClient(
            credentials_path=config.get("credentials_path", ""),
            token_path=config.get("token_path", ""),
        )
        self.orchestrator = RLGMOrchestrator(config=config, ai=ai)
        self.poll_interval = config.get("poll_interval_seconds", 5)
        enable_protocol_mode()
        self._protocol_logger = get_protocol_logger()

    def run(self) -> None:
        """Start the RLGM event loop. Blocks until interrupted."""
        self._running = True
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, "_running", False))
        self._log_startup()
        self.email_client.connect_imap()
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
        """Single poll iteration: get emails, route, send."""
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
                update_context_before_routing(
                    self.orchestrator, message_type, body, self._protocol_logger)
                self._protocol_logger.log_received(
                    email=sender, message_type=message_type)
                outgoing = self._route_message(message_type, body, sender)
                update_context_after_routing(
                    self.orchestrator, self._protocol_logger)
                self._send_messages(outgoing)
            except Exception as e:
                logger.error(f"Router error: {e}", exc_info=True)
                self._protocol_logger.log_error(str(e))

    def _route_message(
        self, message_type: str, body: dict, sender: str
    ) -> List[Tuple[dict, str, str]]:
        """Route message to appropriate handler."""
        outgoing: List[Tuple[dict, str, str]] = []
        if is_lm_message(message_type):
            result = self.orchestrator.handle_lm_message(body)
            if result:
                lm_email = self.config.get("league_manager_email", "")
                response_type = result.get("message_type", "RESPONSE")
                referee_email = self.email_client.address or ""
                tx_id = result.get("message_id") or None
                subject = build_subject(
                    role="REFEREE", email=referee_email,
                    message_type=response_type, tx_id=tx_id,
                )
                outgoing.append((result, subject, lm_email))
            outgoing.extend(self.orchestrator.get_pending_outgoing())
        elif is_player_message(message_type):
            outgoing = self.orchestrator.route_player_message(
                message_type, body, sender)
        return outgoing

    def _send_messages(self, outgoing: List[Tuple[dict, str, str]]) -> None:
        """Send outgoing messages."""
        for envelope, subject, recipient in outgoing:
            self.email_client.send(recipient, subject, envelope)

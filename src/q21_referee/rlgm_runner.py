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
from ._shared import EmailClient, setup_logging
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

    def run(self) -> None:
        """Start the RLGM event loop. Blocks until interrupted."""
        self._running = True
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, "_running", False))

        self._log_startup()
        self.email_client.connect_imap()

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
            body = msg.get("body_json")
            if not body:
                continue

            message_type = body.get("message_type", "")
            sender = body.get("sender", {}).get("email", msg.get("from", ""))

            if message_type not in INCOMING_MESSAGE_TYPES:
                continue

            logger.info(f"── Received: {message_type} from {sender}")

            try:
                outgoing = self._route_message(message_type, body, sender)
                self._send_messages(outgoing)
            except Exception as e:
                logger.error(f"Router error: {e}", exc_info=True)

    def _route_message(
        self, message_type: str, body: dict, sender: str
    ) -> List[Tuple[dict, str, str]]:
        """Route message to appropriate handler."""
        if is_lm_message(message_type):
            result = self.orchestrator.handle_lm_message(body)
            if result:
                lm_email = self.config.get("league_manager_email", "")
                return [(result, f"RE: {message_type}", lm_email)]
            return []
        elif is_player_message(message_type):
            return self.orchestrator.route_player_message(message_type, body, sender)
        return []

    def _send_messages(self, outgoing: List[Tuple[dict, str, str]]) -> None:
        """Send outgoing messages."""
        for envelope, subject, recipient in outgoing:
            self.email_client.send(recipient, subject, envelope)

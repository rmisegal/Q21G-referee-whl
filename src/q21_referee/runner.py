# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee.runner — Main event loop
======================================

The RefereeRunner is what students instantiate and call .run() on.
"""

from __future__ import annotations
import time
import logging
import signal
from typing import Dict, Any, List, Tuple

from .callbacks import RefereeAI
from ._shared import EmailClient, setup_logging
from ._gmc import GameState, GamePhase, PlayerState, EnvelopeBuilder, MessageRouter
from ._runner_config import (
    INCOMING_MESSAGE_TYPES,
    validate_config,
    is_lm_message,
    is_player_message,
)

logger = logging.getLogger("q21_referee")


class RefereeRunner:
    """
    Main entry point for students.

    Usage:
        runner = RefereeRunner(config=config, ai=MyRefereeAI())
        runner.run()
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

        # Build GMC components (for backwards compatibility)
        self._init_gmc_components()

        self.poll_interval = config.get("poll_interval_seconds", 5)

    def _init_gmc_components(self) -> None:
        """Initialize GMC components for single-game mode."""
        c = self.config
        if "game_id" not in c:
            return  # RLGM mode, no direct GMC

        self.state = GameState(
            game_id=c["game_id"],
            match_id=c.get("match_id", ""),
            season_id=c["season_id"],
            league_id=c["league_id"],
            player1=PlayerState(email=c["player1_email"], participant_id=c["player1_id"]),
            player2=PlayerState(email=c["player2_email"], participant_id=c["player2_id"]),
        )
        self.builder = EnvelopeBuilder(
            referee_email=c["referee_email"],
            referee_id=c["referee_id"],
            league_id=c["league_id"],
            season_id=c["season_id"],
        )
        self.router = MessageRouter(
            ai=self.ai, state=self.state, builder=self.builder, config=c
        )

    def run(self) -> None:
        """Start the referee event loop. Blocks until interrupted."""
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
        logger.info("Runner stopped.")

    def _log_startup(self) -> None:
        """Log startup information."""
        logger.info("=" * 60)
        logger.info("  Q21 Referee Runner — Starting")
        logger.info(f"  Email: {self.email_client.address or 'connecting...'}")
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
                outgoing = self.router.route(message_type, body, sender)
                for envelope, subject, recipient in outgoing:
                    self.email_client.send(recipient, subject, envelope)
            except Exception as e:
                logger.error(f"Router error: {e}", exc_info=True)

    def simulate_incoming(self, message: dict) -> List[Tuple[dict, str, str]]:
        """For testing: simulate receiving a message without email."""
        message_type = message.get("message_type", "")
        sender = message.get("sender", {}).get("email", "")
        return self.router.route(message_type, message, sender)

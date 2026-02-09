"""
q21_referee.runner — Main event loop
======================================

The RefereeRunner is what students instantiate and call .run() on.
It orchestrates email polling, message validation, state management,
callback invocation, and response sending in a single blocking loop.
"""

from __future__ import annotations
import json
import time
import logging
import signal
import sys
from typing import Dict, Any, Optional

from .callbacks import RefereeAI
from ._email_client import EmailClient
from ._state import GameState, GamePhase, PlayerState
from ._envelope_builder import EnvelopeBuilder
from ._message_router import MessageRouter
from ._logging_config import setup_logging

logger = logging.getLogger("q21_referee")


# Message types the referee cares about
INCOMING_MESSAGE_TYPES = {
    "BROADCAST_START_SEASON",
    "SEASON_REGISTRATION_RESPONSE",
    "BROADCAST_ASSIGNMENT_TABLE",
    "BROADCAST_NEW_LEAGUE_ROUND",
    "Q21WARMUPRESPONSE",
    "Q21QUESTIONSBATCH",
    "Q21GUESSSUBMISSION",
    "LEAGUE_COMPLETED",
}


class RefereeRunner:
    """
    Main entry point for students.

    Usage
    -----
        from q21_referee import RefereeRunner
        from my_ai import MyRefereeAI

        config = {
            "referee_email": "my-referee@gmail.com",
            "referee_password": "app-password-here",
            "referee_id": "R001",
            "league_manager_email": "server@example.com",
            "league_id": "LEAGUE001",
            "season_id": "SEASON_2026_Q1",
            "game_id": "0101001",
            "match_id": "R1M1",
            "player1_email": "player1@example.com",
            "player1_id": "P001",
            "player2_email": "player2@example.com",
            "player2_id": "P002",
            "poll_interval_seconds": 5,
            "imap_server": "imap.gmail.com",
            "smtp_server": "smtp.gmail.com",
        }

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

        # Validate required config keys
        required = ["referee_email", "referee_password", "referee_id",
                     "league_manager_email", "league_id", "season_id",
                     "game_id", "match_id",
                     "player1_email", "player1_id",
                     "player2_email", "player2_id"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

        # Build internal components
        self.email_client = EmailClient(
            address=config["referee_email"],
            password=config["referee_password"],
            imap_server=config.get("imap_server", "imap.gmail.com"),
            smtp_server=config.get("smtp_server", "smtp.gmail.com"),
        )

        self.state = GameState(
            game_id=config["game_id"],
            match_id=config["match_id"],
            season_id=config["season_id"],
            league_id=config["league_id"],
            player1=PlayerState(
                email=config["player1_email"],
                participant_id=config["player1_id"],
            ),
            player2=PlayerState(
                email=config["player2_email"],
                participant_id=config["player2_id"],
            ),
        )

        self.builder = EnvelopeBuilder(
            referee_email=config["referee_email"],
            referee_id=config["referee_id"],
            league_id=config["league_id"],
            season_id=config["season_id"],
        )

        self.router = MessageRouter(
            ai=ai,
            state=self.state,
            builder=self.builder,
            config=config,
        )

        self.poll_interval = config.get("poll_interval_seconds", 5)

    # ── Main loop ─────────────────────────────────────────────

    def run(self):
        """
        Start the referee event loop. Blocks until interrupted (Ctrl+C).
        """
        self._running = True

        # Graceful shutdown on Ctrl+C
        def _signal_handler(sig, frame):
            logger.info("\nShutting down gracefully...")
            self._running = False
        signal.signal(signal.SIGINT, _signal_handler)

        logger.info("=" * 60)
        logger.info("  Q21 Referee Runner — Starting")
        logger.info(f"  Email:    {self.config['referee_email']}")
        logger.info(f"  Game:     {self.config['game_id']}")
        logger.info(f"  Player 1: {self.config['player1_email']}")
        logger.info(f"  Player 2: {self.config['player2_email']}")
        logger.info(f"  Poll:     every {self.poll_interval}s")
        logger.info("=" * 60)

        # Connect to email
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

        # Cleanup
        self.email_client.disconnect_imap()
        logger.info("Runner stopped.")

    def _poll_and_process(self):
        """Single poll iteration: get emails → validate → route → send."""
        messages = self.email_client.poll()

        for msg in messages:
            body = msg.get("body_json")
            if not body:
                continue

            message_type = body.get("message_type", "")
            sender_email = body.get("sender", {}).get("email", msg.get("from", ""))

            # Only process messages we care about
            if message_type not in INCOMING_MESSAGE_TYPES:
                logger.debug(f"Ignoring message_type={message_type}")
                continue

            logger.info(f"── Received: {message_type} from {sender_email}")

            # Route the message → may trigger callbacks → returns outgoing
            try:
                outgoing = self.router.route(message_type, body, sender_email)
            except Exception as e:
                logger.error(f"Router error for {message_type}: {e}",
                             exc_info=True)
                continue

            # Send all outgoing messages
            for envelope, subject, recipient in outgoing:
                self.email_client.send(recipient, subject, envelope)

    # ── Manual trigger for testing without email ──────────────

    def simulate_incoming(self, message: dict) -> list:
        """
        For testing: simulate receiving a message without email.
        Returns list of outgoing (envelope, subject, recipient) tuples.
        """
        message_type = message.get("message_type", "")
        sender_email = message.get("sender", {}).get("email", "")
        return self.router.route(message_type, message, sender_email)

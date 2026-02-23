# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.router — Message Router (Slim)
================================================

Routes incoming messages to appropriate handlers.
This is the refactored version of message_router.py, under 150 lines.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, List, Tuple

from .state import GameState
from ..callbacks import RefereeAI
from .envelope_builder import EnvelopeBuilder
from .context_builder import ContextBuilder
from .deadline_tracker import DeadlineTracker
from .handlers import (
    handle_warmup_response,
    handle_questions,
    handle_guess,
)

logger = logging.getLogger("q21_referee.router")


@dataclass
class HandlerContext:
    """Context passed to handler functions."""

    ai: RefereeAI
    state: GameState
    builder: EnvelopeBuilder
    context_builder: ContextBuilder
    config: dict
    body: dict
    sender_email: str
    deadline_tracker: DeadlineTracker


class MessageRouter:
    """
    Stateful message router for one game.

    Routes validated incoming messages to handlers that:
    1. Update GameState
    2. Call student callbacks
    3. Build outgoing messages
    """

    def __init__(
        self,
        ai: RefereeAI,
        state: GameState,
        builder: EnvelopeBuilder,
        config: dict,
        deadline_tracker: DeadlineTracker,
    ):
        self.ai = ai
        self.state = state
        self.builder = builder
        self.config = config
        self.deadline_tracker = deadline_tracker
        self.context_builder = ContextBuilder(config, state)

    def route(
        self, message_type: str, body: dict, sender_email: str
    ) -> List[Tuple[dict, str, str]]:
        """
        Route an incoming message.

        Returns list of (envelope, subject, recipient_email) tuples.
        """
        self.deadline_tracker.cancel(sender_email)

        ctx = HandlerContext(
            ai=self.ai,
            state=self.state,
            builder=self.builder,
            context_builder=self.context_builder,
            config=self.config,
            body=body,
            sender_email=sender_email,
            deadline_tracker=self.deadline_tracker,
        )

        if message_type in ("Q21WARMUPRESPONSE", "Q21_WARMUP_RESPONSE"):
            return handle_warmup_response(ctx)

        elif message_type in ("Q21QUESTIONSBATCH", "Q21_QUESTIONS_BATCH"):
            return handle_questions(ctx)

        elif message_type in ("Q21GUESSSUBMISSION", "Q21_GUESS_SUBMISSION"):
            return handle_guess(ctx)

        else:
            logger.debug(f"No handler for message_type={message_type}")
            return []

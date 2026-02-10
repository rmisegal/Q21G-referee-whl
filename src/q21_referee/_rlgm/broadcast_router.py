# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.broadcast_router — Broadcast Message Router
=============================================================

Routes incoming broadcast messages from the League Manager to
their appropriate handlers based on message type.
"""

import logging
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger("q21_referee.rlgm.router")


class BroadcastHandler(Protocol):
    """Protocol for broadcast message handlers."""

    def handle(self, message: Dict[str, Any]) -> Optional[Any]:
        """Handle a broadcast message and optionally return a response."""
        ...


class BroadcastRouter:
    """
    Routes League Manager broadcast messages to handlers.

    Maintains a registry of handlers for each message type and
    dispatches incoming messages to the appropriate handler.

    Usage:
        router = BroadcastRouter()
        router.register_handler("BROADCAST_START_SEASON", start_handler)
        result = router.route(message)
    """

    def __init__(self):
        """Initialize router with empty handler registry."""
        self._handlers: Dict[str, BroadcastHandler] = {}

    def register_handler(
        self, message_type: str, handler: BroadcastHandler
    ) -> None:
        """
        Register a handler for a message type.

        Args:
            message_type: The message type to handle
            handler: The handler instance
        """
        self._handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type}")

    def get_handler(self, message_type: str) -> Optional[BroadcastHandler]:
        """
        Get the handler for a message type.

        Args:
            message_type: The message type to look up

        Returns:
            The handler if registered, None otherwise
        """
        return self._handlers.get(message_type)

    def route(self, message: Dict[str, Any]) -> Optional[Any]:
        """
        Route a message to its handler.

        Args:
            message: The message to route (must have 'message_type' key)

        Returns:
            The handler's result, or None if no handler found
        """
        message_type = message.get("message_type", "")
        handler = self._handlers.get(message_type)

        if handler is None:
            logger.warning(f"No handler for message type: {message_type}")
            return None

        logger.info(f"Routing {message_type} to handler")
        return handler.handle(message)

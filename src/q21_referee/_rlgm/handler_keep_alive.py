# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_keep_alive — Keep-Alive Handler
==========================================================

Handles BROADCAST_KEEP_ALIVE messages from the League Manager.
Responds to confirm the referee is still active.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .handler_base import BaseBroadcastHandler
from .response_builder import RLGMResponseBuilder

logger = logging.getLogger("q21_referee.rlgm.handler.keep_alive")


class BroadcastKeepAliveHandler(BaseBroadcastHandler):
    """
    Handler for BROADCAST_KEEP_ALIVE messages.

    When the League Manager sends keep-alive:
    1. Update last-seen timestamp
    2. Return RESPONSE_KEEP_ALIVE
    """

    def __init__(self, config: Dict[str, Any], response_builder: RLGMResponseBuilder):
        """
        Initialize handler.

        Args:
            config: Configuration dict
            response_builder: Response builder for creating messages
        """
        self.config = config
        self.response_builder = response_builder
        self.last_keep_alive: Optional[datetime] = None

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle BROADCAST_KEEP_ALIVE message.

        Args:
            message: The broadcast message

        Returns:
            RESPONSE_KEEP_ALIVE message
        """
        broadcast_id = self.extract_broadcast_id(message)

        logger.debug(f"Keep-alive received (broadcast_id={broadcast_id})")

        # Update timestamp
        self.last_keep_alive = datetime.now()

        # Return response
        return self.response_builder.build_keep_alive_response()

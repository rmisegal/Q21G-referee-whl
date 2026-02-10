# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.handler_base — Base Broadcast Handler
=======================================================

Abstract base class for all broadcast message handlers.
Provides common utility methods for message parsing and
idempotency checking.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger("q21_referee.rlgm.handler")


class BaseBroadcastHandler(ABC):
    """
    Abstract base class for broadcast message handlers.

    All handlers for League Manager broadcast messages should
    extend this class and implement the handle() method.

    Provides helper methods for:
    - Extracting common message fields
    - Idempotency checking (is_already_processed)
    - Saving processed broadcasts
    """

    @abstractmethod
    def handle(self, message: Dict[str, Any]) -> Optional[Any]:
        """
        Handle a broadcast message.

        Args:
            message: The broadcast message to handle

        Returns:
            Optional response to send back, or None
        """
        pass

    def extract_broadcast_id(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract broadcast_id from message.

        Args:
            message: The message to extract from

        Returns:
            The broadcast_id if present, None otherwise
        """
        return message.get("broadcast_id")

    def extract_message_type(self, message: Dict[str, Any]) -> str:
        """
        Extract message_type from message.

        Args:
            message: The message to extract from

        Returns:
            The message_type, or empty string if missing
        """
        return message.get("message_type", "")

    def extract_payload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract payload from message.

        Args:
            message: The message to extract from

        Returns:
            The payload dict, or empty dict if missing
        """
        return message.get("payload", {})

    def log_handling(self, message_type: str, broadcast_id: Optional[str]) -> None:
        """
        Log that a message is being handled.

        Args:
            message_type: The type of message
            broadcast_id: The broadcast ID if available
        """
        if broadcast_id:
            logger.info(f"Handling {message_type} (broadcast_id={broadcast_id})")
        else:
            logger.info(f"Handling {message_type}")

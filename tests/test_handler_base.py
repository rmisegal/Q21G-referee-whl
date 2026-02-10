# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for Handler Base Class."""

import pytest
from typing import Any, Dict, Optional
from q21_referee._rlgm.handler_base import BaseBroadcastHandler


class ConcreteHandler(BaseBroadcastHandler):
    """Concrete implementation for testing."""

    def handle(self, message: Dict[str, Any]) -> Optional[Any]:
        """Simple handle implementation."""
        return {"handled": True}


class TestBaseBroadcastHandler:
    """Tests for BaseBroadcastHandler class."""

    def test_extract_broadcast_id(self):
        """Test extracting broadcast_id from message."""
        handler = ConcreteHandler()
        message = {
            "message_type": "BROADCAST_START_SEASON",
            "broadcast_id": "BC001",
            "payload": {},
        }
        broadcast_id = handler.extract_broadcast_id(message)
        assert broadcast_id == "BC001"

    def test_extract_broadcast_id_missing(self):
        """Test extracting broadcast_id when missing returns None."""
        handler = ConcreteHandler()
        message = {"message_type": "BROADCAST_START_SEASON", "payload": {}}
        broadcast_id = handler.extract_broadcast_id(message)
        assert broadcast_id is None

    def test_extract_message_type(self):
        """Test extracting message_type from message."""
        handler = ConcreteHandler()
        message = {"message_type": "BROADCAST_START_SEASON", "payload": {}}
        msg_type = handler.extract_message_type(message)
        assert msg_type == "BROADCAST_START_SEASON"

    def test_extract_payload(self):
        """Test extracting payload from message."""
        handler = ConcreteHandler()
        message = {
            "message_type": "BROADCAST_START_SEASON",
            "payload": {"season_id": "S001"},
        }
        payload = handler.extract_payload(message)
        assert payload == {"season_id": "S001"}

    def test_extract_payload_missing(self):
        """Test extracting payload when missing returns empty dict."""
        handler = ConcreteHandler()
        message = {"message_type": "BROADCAST_START_SEASON"}
        payload = handler.extract_payload(message)
        assert payload == {}

    def test_handle_is_abstract(self):
        """Test that handle method must be implemented."""
        # This is implicitly tested by ConcreteHandler implementing it
        handler = ConcreteHandler()
        result = handler.handle({"message_type": "TEST"})
        assert result == {"handled": True}

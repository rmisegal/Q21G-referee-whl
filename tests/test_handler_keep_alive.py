# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for BROADCAST_KEEP_ALIVE handler."""

import pytest
from unittest.mock import patch
from q21_referee._rlgm.handler_keep_alive import BroadcastKeepAliveHandler
from q21_referee._rlgm.response_builder import RLGMResponseBuilder


class TestBroadcastKeepAliveHandler:
    """Tests for BroadcastKeepAliveHandler."""

    def create_handler(self):
        """Create handler with sample config."""
        config = {
            "referee_id": "REF001",
            "referee_email": "ref@test.com",
            "group_id": "GROUP_A",
        }
        response_builder = RLGMResponseBuilder(config)
        return BroadcastKeepAliveHandler(config, response_builder)

    def create_keep_alive_message(self):
        """Create sample keep-alive message."""
        return {
            "message_type": "BROADCAST_KEEP_ALIVE",
            "broadcast_id": "KA001",
            "payload": {
                "timestamp": "2026-01-15T10:00:00Z",
            },
        }

    def test_responds_to_keep_alive(self):
        """Test that handler returns RESPONSE_KEEP_ALIVE."""
        handler = self.create_handler()
        message = self.create_keep_alive_message()

        result = handler.handle(message)

        assert result is not None
        assert result["message_type"] == "RESPONSE_KEEP_ALIVE"
        assert result["payload"]["status"] == "alive"
        assert result["payload"]["referee_id"] == "REF001"

    def test_updates_last_seen_timestamp(self):
        """Test that handler updates last seen timestamp."""
        handler = self.create_handler()
        message = self.create_keep_alive_message()

        assert handler.last_keep_alive is None

        handler.handle(message)

        assert handler.last_keep_alive is not None

    def test_logs_keep_alive(self):
        """Test that keep-alive is logged."""
        handler = self.create_handler()
        message = self.create_keep_alive_message()

        with patch("q21_referee._rlgm.handler_keep_alive.logger") as mock_logger:
            handler.handle(message)
            mock_logger.debug.assert_called()

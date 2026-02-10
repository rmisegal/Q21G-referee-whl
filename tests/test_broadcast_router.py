# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for Broadcast Router."""

import pytest
from unittest.mock import Mock, patch
from q21_referee._rlgm.broadcast_router import BroadcastRouter


class TestBroadcastRouter:
    """Tests for BroadcastRouter class."""

    def test_routes_to_correct_handler(self):
        """Test that messages are routed to registered handlers."""
        router = BroadcastRouter()

        # Create mock handler
        mock_handler = Mock()
        mock_handler.handle.return_value = {"response": "ok"}

        # Register handler
        router.register_handler("BROADCAST_START_SEASON", mock_handler)

        # Route message
        message = {"message_type": "BROADCAST_START_SEASON", "payload": {}}
        result = router.route(message)

        # Verify handler was called
        mock_handler.handle.assert_called_once_with(message)
        assert result == {"response": "ok"}

    def test_returns_none_for_unknown_type(self):
        """Test that unknown message types return None."""
        router = BroadcastRouter()
        message = {"message_type": "UNKNOWN_TYPE", "payload": {}}
        result = router.route(message)
        assert result is None

    def test_logs_routed_message(self):
        """Test that routed messages are logged."""
        router = BroadcastRouter()
        mock_handler = Mock()
        mock_handler.handle.return_value = None
        router.register_handler("BROADCAST_START_SEASON", mock_handler)

        message = {"message_type": "BROADCAST_START_SEASON", "payload": {}}

        with patch("q21_referee._rlgm.broadcast_router.logger") as mock_logger:
            router.route(message)
            mock_logger.info.assert_called()

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers for different message types."""
        router = BroadcastRouter()

        handler1 = Mock()
        handler1.handle.return_value = "result1"
        handler2 = Mock()
        handler2.handle.return_value = "result2"

        router.register_handler("TYPE_A", handler1)
        router.register_handler("TYPE_B", handler2)

        msg_a = {"message_type": "TYPE_A"}
        msg_b = {"message_type": "TYPE_B"}

        assert router.route(msg_a) == "result1"
        assert router.route(msg_b) == "result2"

        handler1.handle.assert_called_once_with(msg_a)
        handler2.handle.assert_called_once_with(msg_b)

    def test_get_handler_returns_handler(self):
        """Test that get_handler returns the registered handler."""
        router = BroadcastRouter()
        mock_handler = Mock()
        router.register_handler("TEST_TYPE", mock_handler)

        assert router.get_handler("TEST_TYPE") is mock_handler
        assert router.get_handler("UNKNOWN") is None

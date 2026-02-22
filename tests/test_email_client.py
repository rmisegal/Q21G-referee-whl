# Area: Shared Tests
# PRD: docs/prd-rlgm.md
"""Tests for email client resilience."""

from unittest.mock import MagicMock

from q21_referee._shared.email_client import EmailClient


class TestPollResilience:
    """Tests for poll() error recovery."""

    def test_poll_error_resets_service(self):
        """After a poll error, _service should be None to force reconnect."""
        client = EmailClient.__new__(EmailClient)
        client.credentials_path = "creds.json"
        client.token_path = "token.json"
        client.address = "test@test.com"
        client._credentials = MagicMock()

        # Create a mock service that fails on list()
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = (
            Exception("API error")
        )
        client._service = mock_service

        # Poll should not crash
        result = client.poll()

        assert result == []
        # Service should be reset so next call reconnects
        assert client._service is None

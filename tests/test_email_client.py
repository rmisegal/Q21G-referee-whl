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


class TestNestedAttachmentParsing:
    """Tests for nested attachment handling."""

    def test_nested_parts_passes_message_id(self):
        """Recursive call should pass original message id for API fetch."""
        client = EmailClient.__new__(EmailClient)
        client.credentials_path = "creds.json"
        client.token_path = "token.json"
        client.address = "test@test.com"
        client._credentials = MagicMock()
        client._service = MagicMock()

        msg = {
            "id": "msg123",
            "payload": {
                "parts": [
                    {
                        "mimeType": "multipart/mixed",
                        "parts": [
                            {
                                "filename": "data.json",
                                "mimeType": "application/json",
                                "body": {"attachmentId": "att1"},
                            }
                        ],
                    }
                ],
            },
        }

        mock_att_get = MagicMock()
        mock_att_get.execute.return_value = {"data": "e30="}
        mock_get_fn = client._service.users.return_value \
            .messages.return_value.attachments.return_value.get
        mock_get_fn.return_value = mock_att_get

        client._get_json_from_attachments(msg)

        # Verify nested attachment fetch used original message id
        mock_get_fn.assert_called_with(
            userId="me", messageId="msg123", id="att1"
        )

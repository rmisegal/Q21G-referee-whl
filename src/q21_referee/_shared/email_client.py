# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee._shared.email_client — Gmail API wrapper with OAuth
================================================================

Handles all email I/O using Gmail API with OAuth2 authentication.
The runner calls poll() to get new messages and send() to deliver outgoing.
Students never use this directly.

Setup:
    1. Create OAuth credentials at https://console.cloud.google.com/
    2. Download as client_secret.json
    3. Set GMAIL_CREDENTIALS_PATH and GMAIL_TOKEN_PATH in .env
       (use full paths including filename!)
    4. On first run, browser opens for OAuth consent
"""

from __future__ import annotations

import base64
import json
import logging
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .email_auth import get_credentials
from .email_reader import parse_message, get_json_from_attachments
from .protocol_logger import get_protocol_logger

logger = logging.getLogger("q21_referee.email")


class EmailClient:
    """Gmail API client with OAuth2 authentication."""

    def __init__(
        self,
        credentials_path: str = "",
        token_path: str = "",
        address: str = "",
        **kwargs,  # Accept legacy params for backwards compat
    ):
        """Initialize Gmail client.

        Args:
            credentials_path: Full path to OAuth client_secret.json
            token_path: Full path to store/load token.json
            address: Gmail address (for logging, auto-detected from API)
        """
        self.credentials_path = credentials_path or os.environ.get(
            "GMAIL_CREDENTIALS_PATH", "client_secret.json"
        )
        self.token_path = token_path or os.environ.get(
            "GMAIL_TOKEN_PATH", "token.json"
        )
        self.address = address
        self._service = None
        self._credentials: Optional[Credentials] = None

    def connect_imap(self) -> None:
        """Establish connection to Gmail API (named for backwards compat)."""
        self._connect()

    def _connect(self) -> bool:
        """Establish connection to Gmail API."""
        try:
            self._credentials = get_credentials(
                self.credentials_path, self.token_path
            )
            self._service = build(
                "gmail", "v1", credentials=self._credentials
            )

            # Get user's email address
            profile = (
                self._service.users().getProfile(userId="me").execute()
            )
            self.address = profile.get("emailAddress", self.address)

            logger.info(f"Gmail API connected: {self.address}")
            return True
        except Exception as e:
            logger.error(f"Gmail connection failed: {e}")
            raise

    def disconnect_imap(self) -> None:
        """Close connection (named for backwards compat)."""
        self._service = None
        self._credentials = None

    def poll(self, **kwargs) -> List[Dict[str, Any]]:
        """Poll inbox for new unread messages (oldest first)."""
        if not self._service:
            self._connect()

        messages = []
        try:
            results = self._service.users().messages().list(
                userId="me", q="is:unread", maxResults=50
            ).execute()

            msg_refs = results.get("messages", [])
            msg_refs = list(reversed(msg_refs))

            for ref in msg_refs:
                try:
                    msg = self._service.users().messages().get(
                        userId="me", id=ref["id"], format="full"
                    ).execute()

                    parsed = parse_message(msg, self._service)
                    if parsed:
                        messages.append(parsed)

                    self._service.users().messages().modify(
                        userId="me",
                        id=ref["id"],
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()

                except Exception as e:
                    logger.warning(
                        f"Failed to process message {ref['id']}: {e}"
                    )

        except Exception as e:
            logger.error(f"Poll error: {e}")
            self._service = None

        return messages

    def _get_json_from_attachments(
        self, msg: dict
    ) -> Optional[Dict[str, Any]]:
        """Delegate to standalone function (backwards compat)."""
        return get_json_from_attachments(msg, self._service)

    def send(
        self,
        to_email: str,
        subject: str,
        body_dict: dict,
        attachment_filename: str = "payload.json",
    ) -> bool:
        """Send a protocol message as email with JSON attachment."""
        if not self._service:
            self._connect()

        try:
            msg = MIMEMultipart()
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText("", "plain", "utf-8"))

            json_content = json.dumps(body_dict, indent=2)
            attachment = MIMEBase("application", "json")
            attachment.set_payload(json_content.encode("utf-8"))
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={attachment_filename}",
            )
            msg.attach(attachment)

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self._service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            short_subj = (
                subject.split("::")[-1] if "::" in subject else subject
            )
            logger.debug(f"Sent [{short_subj}] -> {to_email}")

            protocol_logger = get_protocol_logger()
            message_type = body_dict.get("message_type") or ""
            game_id = (
                (body_dict.get("payload") or {}).get("game_id") or ""
            )
            if not game_id:
                game_id = body_dict.get("game_id", "")
            protocol_logger.log_sent(
                email=to_email,
                message_type=message_type,
                game_id=game_id if game_id else None,
            )
            return True

        except Exception as e:
            logger.error(f"Send failed to {to_email}: {e}")
            return False

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
    2. Download as credentials.json
    3. Set GMAIL_CREDENTIALS_PATH and GMAIL_TOKEN_PATH in .env
    4. On first run, browser opens for OAuth consent
"""

from __future__ import annotations
import base64
import json
import logging
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger("q21_referee.email")

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


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
            credentials_path: Path to OAuth credentials.json
            token_path: Path to store/load token.json
            address: Gmail address (for logging, auto-detected from API)
        """
        self.credentials_path = credentials_path or os.environ.get(
            "GMAIL_CREDENTIALS_PATH", "credentials.json"
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
            self._credentials = self._get_credentials()
            self._service = build("gmail", "v1", credentials=self._credentials)

            # Get user's email address
            profile = self._service.users().getProfile(userId="me").execute()
            self.address = profile.get("emailAddress", self.address)

            logger.info(f"Gmail API connected: {self.address}")
            return True
        except Exception as e:
            logger.error(f"Gmail connection failed: {e}")
            raise

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth2 credentials."""
        creds_path = Path(self.credentials_path)
        token_path = Path(self.token_path)

        if not creds_path.exists():
            raise FileNotFoundError(
                f"Gmail credentials not found at {creds_path}. "
                "Download from Google Cloud Console."
            )

        creds = None

        # Load existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(token_path), GMAIL_SCOPES
                )
            except Exception:
                pass

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds

    def disconnect_imap(self) -> None:
        """Close connection (named for backwards compat)."""
        self._service = None
        self._credentials = None

    def poll(self, **kwargs) -> List[Dict[str, Any]]:
        """Poll inbox for new unread messages."""
        if not self._service:
            self._connect()

        messages = []
        try:
            # Get unread messages
            results = self._service.users().messages().list(
                userId="me", q="is:unread", maxResults=50
            ).execute()

            msg_refs = results.get("messages", [])

            for ref in msg_refs:
                try:
                    msg = self._service.users().messages().get(
                        userId="me", id=ref["id"], format="full"
                    ).execute()

                    parsed = self._parse_message(msg)
                    if parsed:
                        messages.append(parsed)

                    # Mark as read
                    self._service.users().messages().modify(
                        userId="me",
                        id=ref["id"],
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()

                except Exception as e:
                    logger.warning(f"Failed to process message {ref['id']}: {e}")

        except Exception as e:
            logger.error(f"Poll error: {e}")

        return messages

    def _parse_message(self, msg: dict) -> Optional[Dict[str, Any]]:
        """Parse Gmail API message into standard format."""
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

        subject = headers.get("Subject", "")
        from_addr = headers.get("From", "")

        # Extract body
        body = self._get_body(msg["payload"])

        # Try to parse as JSON
        body_json = None
        if body:
            try:
                body_json = json.loads(body.strip())
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "uid": msg["id"],
            "subject": subject,
            "from": from_addr,
            "body_json": body_json,
            "raw_body": body,
        }

    def _get_body(self, payload: dict) -> str:
        """Extract text body from message payload."""
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")
            elif part.get("parts"):
                result = self._get_body(part)
                if result:
                    return result
        return ""

    def send(self, to_email: str, subject: str, body_dict: dict) -> bool:
        """Send a protocol message as email."""
        if not self._service:
            self._connect()

        try:
            body_json = json.dumps(body_dict, indent=2)

            msg = MIMEText(body_json, "plain", "utf-8")
            msg["To"] = to_email
            msg["Subject"] = subject

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self._service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            short_subj = subject.split("::")[-1] if "::" in subject else subject
            logger.info(f"Sent [{short_subj}] → {to_email}")
            return True

        except Exception as e:
            logger.error(f"Send failed to {to_email}: {e}")
            return False

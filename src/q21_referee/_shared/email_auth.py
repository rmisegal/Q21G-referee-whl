# Area: Shared
# PRD: docs/prd-rlgm.md
"""OAuth2 credential management for Gmail API."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger("q21_referee.email")

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials(credentials_path: str, token_path: str) -> Credentials:
    """Get or refresh OAuth2 credentials.

    Args:
        credentials_path: Full path to OAuth client_secret.json
        token_path: Full path to store/load token.json

    Returns:
        Valid OAuth2 Credentials object.
    """
    creds_path = Path(credentials_path)
    tok_path = Path(token_path)

    if not creds_path.exists():
        raise FileNotFoundError(
            f"Gmail credentials not found at {creds_path}. "
            "Download from Google Cloud Console."
        )

    creds = None

    # Load existing token
    if tok_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(tok_path), GMAIL_SCOPES
            )
        except Exception:
            pass

    # Refresh or get new credentials
    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                refreshed = True
            except Exception:
                logger.warning("Token refresh failed, re-authenticating...")

        if not refreshed:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials
        tok_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tok_path, "w") as token:
            token.write(creds.to_json())

    return creds

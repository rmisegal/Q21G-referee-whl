#!/usr/bin/env python3
# Area: Shared
# PRD: docs/prd-rlgm.md
"""
Q21 Referee SDK - Google OAuth Authentication Script
=====================================================

Run this script to authenticate with Gmail API via OAuth.
A browser will open for you to grant permission.

Usage:
    python authenticate.py

The script reads credentials path from (in order):
    1. config.json (if exists)
    2. .env file (if exists)
    3. Environment variables
    4. Default: client_secret.json

After running:
    - token.json will be created
    - You can run the referee without browser prompts
"""

import json
import os
import sys
from pathlib import Path

# Load .env file if exists
from dotenv import load_dotenv
load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def authenticate(credentials_path: str = "client_secret.json",
                 token_path: str = "token.json") -> bool:
    """
    Authenticate with Gmail API and save token.

    Args:
        credentials_path: Path to OAuth client_secret.json
        token_path: Path to save token.json

    Returns:
        True if authentication successful
    """
    creds_path = Path(credentials_path)
    tok_path = Path(token_path)

    # Check for credentials file
    if not creds_path.exists():
        print(f"Error: client_secret.json not found at {creds_path.absolute()}")
        print()
        print("To get client_secret.json:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a project (or select existing)")
        print("  3. Enable the Gmail API:")
        print("     - Go to 'APIs & Services' → 'Library'")
        print("     - Search for 'Gmail API' and enable it")
        print("  4. Create OAuth credentials:")
        print("     - Go to 'APIs & Services' → 'Credentials'")
        print("     - Click 'Create Credentials' → 'OAuth client ID'")
        print("     - Select 'Desktop app'")
        print("     - Download and save as 'client_secret.json'")
        print()
        print("NOTE: Make sure to specify the FULL path including the filename!")
        print("  Example: /Users/yourname/projects/q21/client_secret.json")
        return False

    creds = None

    # Check for existing token
    if tok_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(tok_path), GMAIL_SCOPES)
            if creds and creds.valid:
                print(f"Already authenticated! Token exists at {tok_path}")
                return verify_connection(creds)
            elif creds and creds.expired and creds.refresh_token:
                print("Token expired, refreshing...")
                creds.refresh(Request())
                save_token(creds, tok_path)
                return verify_connection(creds)
        except Exception as e:
            print(f"Existing token invalid: {e}")
            creds = None

    # Run OAuth flow
    print("Opening browser for Google OAuth consent...")
    print()
    print("Please:")
    print("  1. Select your Gmail account")
    print("  2. Click 'Continue' on the 'Google hasn't verified this app' screen")
    print("  3. Grant the requested permissions")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), GMAIL_SCOPES)
        creds = flow.run_local_server(port=0)
        save_token(creds, tok_path)
        return verify_connection(creds)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return False


def save_token(creds: Credentials, token_path: Path) -> None:
    """Save credentials to token file."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {token_path}")


def verify_connection(creds: Credentials) -> bool:
    """Verify the connection works by getting user profile."""
    try:
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "unknown")
        print()
        print("=" * 50)
        print("  Authentication Successful!")
        print("=" * 50)
        print(f"  Connected as: {email}")
        print()
        print("  You can now run:")
        print("    python -m q21_referee --demo --config config.json")
        print()
        return True
    except Exception as e:
        print(f"Connection verification failed: {e}")
        return False


def load_paths_from_config() -> tuple:
    """Load credentials and token paths from config.json if exists."""
    config_file = Path("config.json")
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            return (
                config.get("credentials_path"),
                config.get("token_path"),
            )
        except Exception:
            pass
    return None, None


def main():
    """Main entry point."""
    print()
    print("=" * 50)
    print("  Q21 Referee SDK - OAuth Authentication")
    print("=" * 50)
    print()

    # Try config.json first, then env vars, then defaults
    config_creds, config_token = load_paths_from_config()

    creds_path = (
        config_creds
        or os.environ.get("GMAIL_CREDENTIALS_PATH")
        or "client_secret.json"
    )
    token_path = (
        config_token
        or os.environ.get("GMAIL_TOKEN_PATH")
        or "token.json"
    )

    print(f"Credentials: {creds_path}")
    print(f"Token: {token_path}")
    print()

    success = authenticate(creds_path, token_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

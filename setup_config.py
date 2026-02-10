#!/usr/bin/env python3
# Area: Shared
# PRD: docs/prd-rlgm.md
"""
Q21 Referee SDK - Configuration Setup Script
=============================================

Interactive script to generate config.json and .env files.

Usage:
    python setup_config.py
"""

import json
import os
from pathlib import Path


def prompt(question: str, default: str = "", required: bool = True) -> str:
    """Prompt user for input with optional default value."""
    if default:
        display = f"{question} [{default}]: "
    else:
        display = f"{question}: "

    while True:
        value = input(display).strip()
        if not value and default:
            return default
        if value:
            return value
        if not required:
            return ""
        print("  This field is required. Please enter a value.")


def print_header():
    """Print welcome header."""
    print()
    print("=" * 60)
    print("  Q21 Referee SDK - Configuration Setup")
    print("=" * 60)
    print()
    print("This script will help you create config.json and .env files.")
    print("Press Enter to accept default values shown in [brackets].")
    print()


def print_section(title: str):
    """Print section header."""
    print()
    print(f"--- {title} ---")
    print()


def get_config_values() -> dict:
    """Interactively collect configuration values."""
    config = {}

    print_section("OAuth Credentials")
    print("You need OAuth credentials from Google Cloud Console.")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a project and enable Gmail API")
    print("3. Create OAuth 2.0 credentials (Desktop app)")
    print("4. Download the credentials JSON file (client_secret.json)")
    print()
    print("WARNING: Enter the FULL path including the filename!")
    print("  Example: /Users/yourname/projects/q21/client_secret.json")
    print()

    config["credentials_path"] = prompt(
        "Full path to client_secret.json", default="client_secret.json"
    )
    config["token_path"] = prompt(
        "Full path to store token.json", default="token.json"
    )

    print_section("Referee Identity")
    config["referee_id"] = prompt("Referee ID", default="REF001")
    config["group_id"] = prompt("Group ID", default="GROUP_01")
    config["display_name"] = prompt(
        "Display name", default="Q21 Referee", required=False
    )

    print_section("League Manager")
    config["league_manager_email"] = prompt("League Manager email address")

    print_section("Optional Settings")
    poll_interval = prompt(
        "Poll interval in seconds", default="5", required=False
    )
    if poll_interval:
        config["poll_interval_seconds"] = int(poll_interval)

    return config


def write_config_json(config: dict, path: Path) -> None:
    """Write config.json file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    print(f"  Created: {path}")


def write_env_file(config: dict, path: Path) -> None:
    """Write .env file."""
    env_mapping = {
        "credentials_path": "GMAIL_CREDENTIALS_PATH",
        "token_path": "GMAIL_TOKEN_PATH",
        "referee_id": "REFEREE_ID",
        "group_id": "GROUP_ID",
        "display_name": "DISPLAY_NAME",
        "league_manager_email": "LEAGUE_MANAGER_EMAIL",
        "poll_interval_seconds": "POLL_INTERVAL_SECONDS",
    }

    lines = []
    for config_key, env_key in env_mapping.items():
        if config_key in config and config[config_key]:
            lines.append(f"{env_key}={config[config_key]}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Created: {path}")


def main():
    """Main entry point."""
    print_header()

    try:
        config = get_config_values()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        return 1

    print_section("Generating Files")

    base_path = Path.cwd()
    write_config_json(config, base_path / "config.json")
    write_env_file(config, base_path / ".env")

    print()
    print("=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print()
    print("  1. Make sure client_secret.json is at the path you specified")
    print()
    print("  2. Authenticate with Google:")
    print("     python authenticate.py")
    print()
    print("  3. Run in demo mode to test your setup:")
    print("     python -m q21_referee --demo --config config.json")
    print()
    print("  4. Once working, implement your own RefereeAI class")
    print()
    return 0


if __name__ == "__main__":
    exit(main())

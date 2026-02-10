# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee.cli — Command-line interface
=========================================

Provides CLI entry point for running the referee.

Usage:
    python -m q21_referee --demo                    # Run in demo mode
    python -m q21_referee --config config.json      # Run with config file

Demo mode can be enabled via:
    1. CLI flag: --demo
    2. Config key: demo_mode: True
    3. Environment variable: DEMO_MODE=true
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .demo_ai import DemoAI
from .callbacks import RefereeAI


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Q21 Referee SDK - Run your referee AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m q21_referee --demo
  python -m q21_referee --config config.json
  python -m q21_referee --demo --config config.json
  DEMO_MODE=true python -m q21_referee --config config.json
        """,
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode using DemoAI (no AI implementation needed)",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON config file",
    )

    parser.add_argument(
        "--single-game",
        action="store_true",
        help="Run single game mode (RefereeRunner) instead of season mode (RLGMRunner)",
    )

    parser.add_argument(
        "--demo-path",
        type=str,
        help="Custom path to demo data files (default: demo_data/)",
    )

    return parser.parse_args()


def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load config from file or environment."""
    config: Dict[str, Any] = {}

    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                config = json.load(f)

    # Override with environment variables
    env_mappings = {
        "GMAIL_ACCOUNT": "referee_email",
        "GMAIL_APP_PASSWORD": "referee_password",
        "REFEREE_ID": "referee_id",
        "GROUP_ID": "group_id",
        "LEAGUE_MANAGER_EMAIL": "league_manager_email",
        "DISPLAY_NAME": "display_name",
        "POLL_INTERVAL_SECONDS": "poll_interval_seconds",
    }

    for env_key, config_key in env_mappings.items():
        if env_key in os.environ:
            value = os.environ[env_key]
            if config_key == "poll_interval_seconds":
                value = int(value)
            config[config_key] = value

    return config


def is_demo_mode(args: argparse.Namespace, config: Dict[str, Any]) -> bool:
    """Check if demo mode is enabled via CLI, config, or environment."""
    if args.demo:
        return True
    if config.get("demo_mode"):
        return True
    if os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes"):
        return True
    return False


def get_ai(args: argparse.Namespace, config: Dict[str, Any]) -> RefereeAI:
    """Get the appropriate AI instance based on mode."""
    if is_demo_mode(args, config):
        demo_path = args.demo_path or config.get("demo_path")
        return DemoAI(demo_path=demo_path)

    # In non-demo mode, users must provide their own AI via Python code
    # CLI can only use DemoAI
    print("Error: Non-demo mode requires running from Python code.", file=sys.stderr)
    print("Use --demo flag or implement your own RefereeAI.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    """Main CLI entry point."""
    args = parse_args()
    config = load_config(args.config)

    # Validate required config
    required = ["referee_email", "referee_password"]
    missing = [k for k in required if k not in config]
    if missing:
        print(f"Error: Missing required config: {', '.join(missing)}", file=sys.stderr)
        print("Set via config file or environment variables.", file=sys.stderr)
        return 1

    ai = get_ai(args, config)

    # Import runners here to avoid circular imports
    if args.single_game:
        from .runner import RefereeRunner
        runner = RefereeRunner(config=config, ai=ai)
    else:
        from .rlgm_runner import RLGMRunner
        runner = RLGMRunner(config=config, ai=ai)

    runner.run()
    return 0

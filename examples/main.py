"""
main.py — Run your Q21 Referee
================================

This is the entry point. Just configure your credentials,
point to your AI implementation, and run.

    python main.py

The runner will:
  1. Connect to your email inbox
  2. Poll for incoming protocol messages
  3. Call YOUR AI functions when triggered
  4. Send responses automatically

Press Ctrl+C to stop.
"""

import logging
from q21_referee import RefereeRunner
from my_ai import MyRefereeAI

# ── Setup logging (so you can see what's happening) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ── Configuration ──
config = {
    # Your referee email credentials (use Gmail app password)
    "referee_email": "your-referee@gmail.com",
    "referee_password": "your-app-password",
    "referee_id": "R001",

    # League Manager
    "league_manager_email": "league-manager@example.com",

    # League / Season / Game IDs (from BROADCAST_ASSIGNMENT_TABLE)
    "league_id": "LEAGUE001",
    "season_id": "SEASON_2026_Q1",
    "game_id": "0101001",          # 7-digit SSRRGGG format
    "match_id": "R1M1",

    # Your two players (from assignment table)
    "player1_email": "player1@example.com",
    "player1_id": "P001",
    "player2_email": "player2@example.com",
    "player2_id": "P002",

    # How often to check email (seconds)
    "poll_interval_seconds": 5,

    # Email server settings (Gmail defaults)
    "imap_server": "imap.gmail.com",
    "smtp_server": "smtp.gmail.com",
}

# ── Create your AI and run ──
my_ai = MyRefereeAI()
runner = RefereeRunner(config=config, ai=my_ai)
runner.run()

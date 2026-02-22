# Area: GMC
# PRD: docs/prd-rlgm.md
"""Helper functions for envelope construction."""

from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f+00:00"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(_TIME_FMT)


def deadline_iso(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime(_TIME_FMT)


def msg_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def email_subject(protocol: str, role: str, email: str,
                  tx_id: str, message_type: str) -> str:
    return f"{protocol}::{role}::{email}::{tx_id}::{message_type}"


def sender_block(email: str, logical_id: str) -> dict:
    return {"email": email, "role": "REFEREE", "logical_id": logical_id}


def base_q21_envelope(message_type: str, mid: str, recipient_id: str,
                      game_id: str, email: str, logical_id: str,
                      correlation_id: Optional[str] = None) -> dict:
    env = {
        "protocol": "Q21G.v1",
        "message_type": message_type,
        "message_id": mid,
        "timestamp": now_iso(),
        "sender": sender_block(email, logical_id),
        "recipient_id": recipient_id,
        "game_id": game_id,
    }
    if correlation_id is not None:
        env["correlation_id"] = correlation_id
    return env


def base_league_envelope(message_type: str, mid: str, recipient_id: str,
                         email: str, logical_id: str,
                         league_id: str, season_id: str,
                         round_id: str = None, game_id: str = None,
                         correlation_id: str = None) -> dict:
    env = {
        "protocol": "league.v2",
        "message_type": message_type,
        "message_id": mid,
        "timestamp": now_iso(),
        "sender": sender_block(email, logical_id),
        "recipient_id": recipient_id,
        "league_id": league_id,
        "season_id": season_id,
    }
    if round_id is not None:
        env["round_id"] = round_id
    if game_id is not None:
        env["game_id"] = game_id
    if correlation_id is not None:
        env["correlation_id"] = correlation_id
    return env

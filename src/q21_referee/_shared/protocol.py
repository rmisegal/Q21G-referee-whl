# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee._shared.protocol — Protocol helpers for message formatting
======================================================================

Implements the UNIFIED_PROTOCOL.md specification for message envelopes
and email subject formatting.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Protocol versions
LEAGUE_PROTOCOL = "league.v2"
Q21_PROTOCOL = "Q21G.v1"


def generate_tx_id(prefix: str = "tx") -> str:
    """Generate unique transaction ID.

    Format: prefix-YYYYMMDD-XXXXXX
    """
    date_part = datetime.now().strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:6]
    return f"{prefix}-{date_part}-{unique_part}"


def generate_message_id() -> str:
    """Generate unique message ID."""
    return str(uuid.uuid4())


def current_timestamp() -> str:
    """Generate ISO 8601 timestamp with timezone."""
    return datetime.now(timezone.utc).isoformat()


def build_subject(
    role: str,
    email: str,
    message_type: str,
    tx_id: Optional[str] = None,
    protocol: str = LEAGUE_PROTOCOL,
) -> str:
    """Build protocol-compliant subject line.

    Format: protocol::ROLE::email::tx-id::MESSAGETYPE

    Args:
        role: Sender role (REFEREE, PLAYER, LEAGUEMANAGER)
        email: Sender's email address
        message_type: Message type (underscores removed for subject)
        tx_id: Transaction ID (auto-generated if not provided)
        protocol: Protocol version (league.v2 or Q21G.v1)

    Returns:
        Formatted subject line
    """
    if tx_id is None:
        tx_id = generate_tx_id()

    # Remove underscores from message type per protocol spec
    msg_type_formatted = message_type.replace("_", "")

    return f"{protocol}::{role}::{email}::{tx_id}::{msg_type_formatted}"


def build_envelope(
    message_type: str,
    payload: Dict[str, Any],
    sender_email: str,
    sender_role: str,
    sender_logical_id: Optional[str] = None,
    recipient_id: str = "LEAGUEMANAGER",
    correlation_id: Optional[str] = None,
    league_id: Optional[str] = None,
    season_id: Optional[str] = None,
    round_id: Optional[str] = None,
    game_id: Optional[str] = None,
    message_id: Optional[str] = None,
    protocol: str = LEAGUE_PROTOCOL,
) -> Dict[str, Any]:
    """Build protocol-compliant message envelope.

    Args:
        message_type: Message type (e.g., SEASON_REGISTRATION_REQUEST)
        payload: Message-specific payload data
        sender_email: Sender's email
        sender_role: Sender role (REFEREE, PLAYER)
        sender_logical_id: Logical ID (referee_id, player_id)
        recipient_id: Recipient identifier
        correlation_id: Links to original request (for responses)
        league_id: League context
        season_id: Season context
        round_id: Round context
        game_id: Game/match context
        message_id: Message ID (auto-generated if not provided)
        protocol: Protocol version

    Returns:
        Complete envelope dict
    """
    if message_id is None:
        message_id = generate_message_id()

    envelope = {
        "protocol": protocol,
        "message_type": message_type,
        "message_id": message_id,
        "timestamp": current_timestamp(),
        "sender": {
            "email": sender_email,
            "role": sender_role,
            "logical_id": sender_logical_id,
        },
        "recipient_id": recipient_id,
        "payload": payload,
    }

    # Add optional context fields (use `is not None` to preserve falsy values)
    if correlation_id is not None:
        envelope["correlation_id"] = correlation_id
    if league_id is not None:
        envelope["league_id"] = league_id
    if season_id is not None:
        envelope["season_id"] = season_id
    if round_id is not None:
        envelope["round_id"] = round_id
    if game_id is not None:
        envelope["game_id"] = game_id

    return envelope

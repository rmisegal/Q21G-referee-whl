"""
Q21 League Protocol SDK
=======================
Unified Protocol v2 — league.v2 + Q21G.v1

Usage
-----
    from sdk import process_message, list_supported_messages

    # From a dict (the full envelope + payload):
    result = process_message({
        "protocol": "Q21G.v1",
        "message_type": "Q21WARMUPCALL",
        "message_id": "warmup-r1m1-p001",
        "timestamp": "2026-01-25T10:00:00.000000+00:00",
        "sender": {"email": "ref@ex.com", "role": "REFEREE", "logical_id": "R001"},
        "recipient_id": "P001",
        "game_id": "0101001",
        "payload": {
            "match_id": "R1M1",
            "warmup_question": "What is 2+2?",
            "deadline": "2026-01-25T10:02:00.000000+00:00"
        }
    })

    # From a JSON string or file path:
    result = process_message("incoming.json")
"""

import json

from .core import (
    MessageDispatcher, MessageRegistry, SDKError, ValidationResult,
    Protocol, EmailSubject, ErrorResponseBuilder,
)

# ── Import all message modules to trigger @register_message ──
from . import messages_league   # league.v2: §5.3–5.6, §6.1, §7.9, §7.10
from . import messages_q21      # Q21G.v1:   §7.2–7.8


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def process_message(input_data) -> dict:
    """
    Validate and process a protocol message.

    Parameters
    ----------
    input_data : dict | str
        Full envelope+payload dict, a JSON string, or a .json file path.

    Returns
    -------
    dict
        On success:  {"status": "success", "protocol": "...", "message_type": "...", ...}
        On error:    {"status": "error", ...}
    """
    try:
        return MessageDispatcher.dispatch(input_data)
    except SDKError as e:
        return json.loads(e.to_json())


def list_supported_messages() -> list[str]:
    """All registered message_type strings."""
    return MessageRegistry.list_types()


def list_league_messages() -> list[str]:
    """message_type strings for league.v2 only."""
    return MessageRegistry.list_by_protocol(Protocol.LEAGUE)


def list_q21_messages() -> list[str]:
    """message_type strings for Q21G.v1 only."""
    return MessageRegistry.list_by_protocol(Protocol.Q21G)


def get_message_info() -> list[dict]:
    """Metadata about every registered handler."""
    info = []
    for mt in MessageRegistry.list_types():
        cls = MessageRegistry.get_handler(mt)
        info.append({
            "message_type": mt,
            "class_name": cls.__name__,
            "protocol": cls.PROTOCOL.value,
            "direction": cls.DIRECTION.value,
            "required_context": cls.REQUIRED_CONTEXT_FIELDS,
        })
    return info


def build_error_response(error_code: str, error_message: str,
                         original_message_type: str, recoverable: bool,
                         sender_email: str, recipient_id: str,
                         correlation_id: str = None) -> dict:
    """Build a spec-compliant ERROR_RESPONSE message (§8)."""
    return ErrorResponseBuilder.build(
        error_code, error_message, original_message_type,
        recoverable, sender_email, recipient_id, correlation_id,
    )


def parse_email_subject(subject: str) -> dict | None:
    """Parse a protocol email subject line (§3)."""
    return EmailSubject.parse(subject)


def generate_email_subject(message: dict) -> str:
    """Generate the email subject line for a message (§3)."""
    return EmailSubject.from_message(message)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sdk.py <message.json | JSON_STRING>")
        print(f"\n── league.v2 messages ({len(list_league_messages())}) ──")
        for mt in list_league_messages():
            cls = MessageRegistry.get_handler(mt)
            print(f"  {mt:<40s} {cls.DIRECTION.value}")
        print(f"\n── Q21G.v1 messages ({len(list_q21_messages())}) ──")
        for mt in list_q21_messages():
            cls = MessageRegistry.get_handler(mt)
            print(f"  {mt:<40s} {cls.DIRECTION.value}")
        sys.exit(0)

    result = process_message(sys.argv[1])
    print(json.dumps(result, indent=2))

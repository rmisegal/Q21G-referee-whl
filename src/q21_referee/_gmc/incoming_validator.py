# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.incoming_validator — Player message format validation
=====================================================================

Validates the structure of incoming player messages before routing.
Returns a list of error strings (empty list = valid message).
Unknown message types pass through without payload validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# PAYLOAD RULE DEFINITIONS
# ══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PayloadRule:
    """Defines validation rules for a specific message type's payload."""

    required_fields: List[str] = field(default_factory=list)
    list_fields: List[str] = field(default_factory=list)
    min_keys: Optional[int] = None


_PAYLOAD_RULES: Dict[str, PayloadRule] = {
    "Q21_WARMUP_RESPONSE": PayloadRule(required_fields=["answer"]),
    "Q21WARMUPRESPONSE": PayloadRule(required_fields=["answer"]),
    "Q21_QUESTIONS_BATCH": PayloadRule(
        required_fields=["questions"], list_fields=["questions"],
    ),
    "Q21QUESTIONSBATCH": PayloadRule(
        required_fields=["questions"], list_fields=["questions"],
    ),
    "Q21_GUESS_SUBMISSION": PayloadRule(min_keys=1),
    "Q21GUESSSUBMISSION": PayloadRule(min_keys=1),
}


# ══════════════════════════════════════════════════════════════
# TOP-LEVEL VALIDATION
# ══════════════════════════════════════════════════════════════


def _check_top_level(body: dict) -> List[str]:
    """Validate top-level required fields: message_type, sender, payload."""
    errors: List[str] = []

    if "message_type" not in body:
        errors.append("Missing required field: message_type")

    if "sender" not in body:
        errors.append("Missing required field: sender")
    elif not isinstance(body["sender"], dict):
        errors.append("'sender' must be a dict")
    elif "email" not in body["sender"]:
        errors.append("'sender' missing required field: email")

    if "payload" not in body:
        errors.append("Missing required field: payload")
    elif not isinstance(body["payload"], dict):
        errors.append("'payload' must be a dict")

    return errors


# ══════════════════════════════════════════════════════════════
# PAYLOAD VALIDATION
# ══════════════════════════════════════════════════════════════


def _check_payload(message_type: str, payload: dict) -> List[str]:
    """Validate payload against rules for the given message type."""
    rule = _PAYLOAD_RULES.get(message_type)
    if rule is None:
        return []

    errors: List[str] = []

    for fld in rule.required_fields:
        if fld not in payload:
            errors.append(f"Payload missing required field: {fld}")

    for fld in rule.list_fields:
        if fld in payload and not isinstance(payload[fld], list):
            errors.append(f"Payload field '{fld}' must be a list")

    if rule.min_keys is not None and len(payload) < rule.min_keys:
        errors.append(
            f"Payload must have at least {rule.min_keys} key(s), "
            f"got {len(payload)}"
        )

    return errors


# ══════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════


def validate_player_message(body: dict) -> List[str]:
    """
    Validate an incoming player message body.

    Parameters
    ----------
    body : dict
        The parsed JSON body of the incoming message.

    Returns
    -------
    List[str]
        List of validation error strings. Empty if the message is valid.
    """
    errors = _check_top_level(body)

    # Only check payload if top-level is clean enough
    if "message_type" in body and isinstance(body.get("payload"), dict):
        errors.extend(_check_payload(body["message_type"], body["payload"]))

    return errors

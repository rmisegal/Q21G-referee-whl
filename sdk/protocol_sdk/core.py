"""
Q21 League Protocol SDK — Core Framework
=========================================
Matches UNIFIED_PROTOCOL v2 specification.

Two protocols:
  - league.v2   : League Manager ↔ Participants
  - Q21G.v1     : Referee ↔ Player (Q21 game messages)

Every message uses the canonical JSON envelope (§2) with a nested payload.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# 1. ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════

class Protocol(Enum):
    LEAGUE = "league.v2"
    Q21G   = "Q21G.v1"


class Role(Enum):
    PLAYER        = "PLAYER"
    REFEREE       = "REFEREE"
    LEAGUEMANAGER = "LEAGUEMANAGER"


class MessageDirection(Enum):
    LM_TO_ALL         = "LM→All"
    LM_TO_PR          = "LM→Player/Referee"
    PR_TO_LM          = "Player/Referee→LM"
    REFEREE_TO_LM     = "Referee→LM"
    REFEREE_TO_PLAYER = "Referee→Player"
    PLAYER_TO_REFEREE = "Player→Referee"
    ANY               = "Any"


# Standard error codes (§8.2)
STANDARD_ERROR_CODES = [
    "INVALID_MESSAGE",
    "UNAUTHORIZED",
    "NOT_REGISTERED",
    "DEADLINE_PASSED",
    "INVALID_STATE",
    "INTERNAL_ERROR",
]


# ═══════════════════════════════════════════════════════════════════
# 2. ERROR / VALIDATION TYPES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FieldError:
    """Single field-level validation failure."""
    field_name: str
    error_type: str        # missing | invalid_type | invalid_value | out_of_range
    expected: Optional[str] = None
    received: Optional[Any] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"field": self.field_name, "error_type": self.error_type}
        if self.expected:
            d["expected"] = self.expected
        if self.received is not None:
            d["received"] = str(self.received)
        if self.message:
            d["message"] = self.message
        return d


@dataclass
class ValidationResult:
    """Aggregated validation result across all fields."""
    is_valid: bool = True
    errors: List[FieldError] = field(default_factory=list)

    def add_error(self, err: FieldError):
        self.is_valid = False
        self.errors.append(err)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
        }


class SDKError(Exception):
    """Raised when message validation fails."""
    def __init__(self, message_type: str, validation: ValidationResult):
        self.message_type = message_type
        self.validation = validation
        super().__init__(
            f"[{message_type}] Validation failed with {len(validation.errors)} error(s)"
        )

    def to_json(self) -> str:
        return json.dumps({
            "status": "error",
            "message_type": self.message_type,
            "validation": self.validation.to_dict(),
        }, indent=2)


# ═══════════════════════════════════════════════════════════════════
# 3. FIELD VALIDATORS — reusable building blocks
# ═══════════════════════════════════════════════════════════════════

class FieldValidator:
    """Static, composable field-check methods that accumulate errors."""

    @staticmethod
    def required(data: dict, field_name: str, result: ValidationResult,
                 prefix: str = "") -> Any:
        full = f"{prefix}{field_name}" if prefix else field_name
        if field_name not in data or data[field_name] is None:
            result.add_error(FieldError(full, "missing",
                                        message=f"'{full}' is required"))
            return None
        return data[field_name]

    @staticmethod
    def expected_type(value: Any, field_name: str, expected: type,
                      result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if not isinstance(value, expected):
            result.add_error(FieldError(full, "invalid_type",
                                        expected=expected.__name__,
                                        received=type(value).__name__))
            return False
        return True

    @staticmethod
    def one_of(value: Any, field_name: str, choices: list,
               result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if value not in choices:
            result.add_error(FieldError(full, "invalid_value",
                                        expected=f"one of {choices}",
                                        received=value))
            return False
        return True

    @staticmethod
    def non_empty_string(value: Any, field_name: str,
                         result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if not isinstance(value, str) or len(value.strip()) == 0:
            result.add_error(FieldError(full, "invalid_value",
                                        expected="non-empty string",
                                        received=value))
            return False
        return True

    @staticmethod
    def positive_int(value: Any, field_name: str,
                     result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if not isinstance(value, int) or value <= 0:
            result.add_error(FieldError(full, "out_of_range",
                                        expected="positive integer",
                                        received=value))
            return False
        return True

    @staticmethod
    def non_negative_int(value: Any, field_name: str,
                         result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if not isinstance(value, int) or value < 0:
            result.add_error(FieldError(full, "out_of_range",
                                        expected="non-negative integer",
                                        received=value))
            return False
        return True

    @staticmethod
    def number_in_range(value: Any, field_name: str,
                        min_val: float, max_val: float,
                        result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if not isinstance(value, (int, float)):
            result.add_error(FieldError(full, "invalid_type",
                                        expected="number",
                                        received=type(value).__name__))
            return False
        if value < min_val or value > max_val:
            result.add_error(FieldError(full, "out_of_range",
                                        expected=f"{min_val}–{max_val}",
                                        received=value))
            return False
        return True

    @staticmethod
    def iso_datetime(value: Any, field_name: str,
                     result: ValidationResult, prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        try:
            datetime.fromisoformat(str(value))
            return True
        except (ValueError, TypeError):
            result.add_error(FieldError(full, "invalid_value",
                                        expected="ISO-8601 datetime with timezone",
                                        received=value))
            return False

    @staticmethod
    def is_list(value: Any, field_name: str, result: ValidationResult,
                prefix: str = "", min_length: int = 0) -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None:
            return False
        if not isinstance(value, list):
            result.add_error(FieldError(full, "invalid_type",
                                        expected="array",
                                        received=type(value).__name__))
            return False
        if len(value) < min_length:
            result.add_error(FieldError(full, "out_of_range",
                                        expected=f"min length {min_length}",
                                        received=len(value)))
            return False
        return True

    @staticmethod
    def word_count_range(value: Any, field_name: str, min_words: int,
                         max_words: int, result: ValidationResult,
                         prefix: str = "") -> bool:
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None or not isinstance(value, str):
            return False
        wc = len(value.split())
        if wc < min_words or wc > max_words:
            result.add_error(FieldError(full, "out_of_range",
                                        expected=f"{min_words}–{max_words} words",
                                        received=f"{wc} words"))
            return False
        return True

    @staticmethod
    def game_id_format(value: Any, field_name: str,
                       result: ValidationResult, prefix: str = "") -> bool:
        """Validate 7-digit SSRRGGG game ID format (§5.6)."""
        full = f"{prefix}{field_name}" if prefix else field_name
        if value is None or not isinstance(value, str):
            return False
        import re
        if not re.match(r'^\d{7}$', value):
            result.add_error(FieldError(full, "invalid_value",
                                        expected="7-digit SSRRGGG format",
                                        received=value))
            return False
        return True


# ═══════════════════════════════════════════════════════════════════
# 4. EMAIL SUBJECT PARSING / GENERATION (§3)
# ═══════════════════════════════════════════════════════════════════

class EmailSubject:
    """Parse and generate email subject lines per §3."""

    @staticmethod
    def generate(protocol: str, role: str, email: str,
                 transaction_id: str, message_type: str) -> str:
        return f"{protocol}::{role}::{email}::{transaction_id}::{message_type}"

    @staticmethod
    def parse(subject: str) -> Optional[dict]:
        parts = subject.split("::")
        if len(parts) != 5:
            return None
        return {
            "protocol": parts[0],
            "role": parts[1],
            "email": parts[2],
            "transaction_id": parts[3],
            "message_type": parts[4],
        }

    @staticmethod
    def from_message(data: dict) -> str:
        protocol = data.get("protocol", "league.v2")
        sender = data.get("sender", {})
        role = sender.get("role", "UNKNOWN")
        email = sender.get("email", "unknown@example.com")
        tx_id = data.get("message_id", str(uuid.uuid4())[:12])
        msg_type = data.get("message_type", "UNKNOWN")
        return EmailSubject.generate(protocol, role, email, tx_id, msg_type)


# ═══════════════════════════════════════════════════════════════════
# 5. BASE MESSAGE CLASS
# ═══════════════════════════════════════════════════════════════════

class BaseMessage(ABC):
    """
    Abstract base for every protocol message.

    Each subclass MUST define:
      MESSAGE_TYPE            : str
      PROTOCOL                : Protocol (league.v2 or Q21G.v1)
      DIRECTION               : MessageDirection
      REQUIRED_CONTEXT_FIELDS : list of envelope context field names
      validate_payload()      : field checks on self.payload → appends to ValidationResult
      process_payload()       : business logic → dict
    """

    MESSAGE_TYPE: str = ""
    PROTOCOL: Protocol = Protocol.LEAGUE
    DIRECTION: MessageDirection = MessageDirection.LM_TO_ALL
    REQUIRED_CONTEXT_FIELDS: List[str] = []

    def __init__(self, raw: dict):
        self.raw = raw
        self.payload: dict = raw.get("payload", {})
        self.fv = FieldValidator()

    # ── Public entry point ────────────────────────────────────────
    def handle(self) -> dict:
        result = ValidationResult()
        self._validate_envelope(result)
        self.validate_payload(result)
        if not result.is_valid:
            raise SDKError(self.MESSAGE_TYPE, result)
        return self._build_output()

    # ── Envelope validation (§2) ──────────────────────────────────
    def _validate_envelope(self, r: ValidationResult):
        # protocol
        proto = self.fv.required(self.raw, "protocol", r)
        if proto is not None:
            self.fv.one_of(proto, "protocol", [self.PROTOCOL.value], r)

        # message_type
        mt = self.fv.required(self.raw, "message_type", r)
        if mt is not None:
            self.fv.one_of(mt, "message_type", [self.MESSAGE_TYPE], r)

        # message_id
        self.fv.required(self.raw, "message_id", r)
        self.fv.non_empty_string(self.raw.get("message_id"), "message_id", r)

        # timestamp — ISO 8601 with timezone
        self.fv.required(self.raw, "timestamp", r)
        self.fv.iso_datetime(self.raw.get("timestamp"), "timestamp", r)

        # sender object (§2.2)
        sender = self.fv.required(self.raw, "sender", r)
        if sender is not None:
            self.fv.expected_type(sender, "sender", dict, r)
            if isinstance(sender, dict):
                self.fv.required(sender, "email", r, prefix="sender.")
                self.fv.non_empty_string(sender.get("email"), "email", r,
                                         prefix="sender.")
                role_val = self.fv.required(sender, "role", r, prefix="sender.")
                if role_val is not None:
                    self.fv.one_of(role_val, "role",
                                   ["PLAYER", "REFEREE", "LEAGUEMANAGER"],
                                   r, prefix="sender.")
                # logical_id is optional (null for LEAGUEMANAGER)

        # recipient_id
        self.fv.required(self.raw, "recipient_id", r)
        self.fv.non_empty_string(self.raw.get("recipient_id"), "recipient_id", r)

        # payload must be a dict
        payload = self.fv.required(self.raw, "payload", r)
        if payload is not None:
            self.fv.expected_type(payload, "payload", dict, r)

        # Required context fields for this message type
        for ctx in self.REQUIRED_CONTEXT_FIELDS:
            val = self.fv.required(self.raw, ctx, r)
            if val is not None:
                self.fv.non_empty_string(val, ctx, r)

    # ── Subclass hooks ────────────────────────────────────────────
    @abstractmethod
    def validate_payload(self, result: ValidationResult) -> None:
        ...

    @abstractmethod
    def process_payload(self) -> dict:
        ...

    # ── Build output ──────────────────────────────────────────────
    def _build_output(self) -> dict:
        return {
            "status": "success",
            "protocol": self.PROTOCOL.value,
            "message_type": self.MESSAGE_TYPE,
            "direction": self.DIRECTION.value,
            "message_id": self.raw.get("message_id"),
            "email_subject": EmailSubject.from_message(self.raw),
            "processed_payload": self.process_payload(),
        }


# ═══════════════════════════════════════════════════════════════════
# 6. ERROR RESPONSE BUILDER (§8)
# ═══════════════════════════════════════════════════════════════════

class ErrorResponseBuilder:
    """Build a spec-compliant ERROR_RESPONSE message (§8.1)."""

    @staticmethod
    def build(error_code: str, error_message: str,
              original_message_type: str, recoverable: bool,
              sender_email: str, recipient_id: str,
              correlation_id: Optional[str] = None) -> dict:
        msg_id = f"error-{uuid.uuid4().hex[:8]}"
        return {
            "protocol": "league.v2",
            "message_type": "ERROR_RESPONSE",
            "message_id": msg_id,
            "timestamp": datetime.utcnow().isoformat() + "+00:00",
            "sender": {
                "email": sender_email,
                "role": "LEAGUEMANAGER",
                "logical_id": None,
            },
            "recipient_id": recipient_id,
            "correlation_id": correlation_id,
            "payload": {
                "error_code": error_code,
                "error_message": error_message,
                "original_message_type": original_message_type,
                "recoverable": recoverable,
            },
        }


# ═══════════════════════════════════════════════════════════════════
# 7. MESSAGE REGISTRY & DISPATCHER
# ═══════════════════════════════════════════════════════════════════

class MessageRegistry:
    """Maps message_type strings → handler classes."""
    _handlers: Dict[str, Type[BaseMessage]] = {}

    @classmethod
    def register(cls, message_cls: Type[BaseMessage]) -> Type[BaseMessage]:
        cls._handlers[message_cls.MESSAGE_TYPE] = message_cls
        return message_cls

    @classmethod
    def get_handler(cls, message_type: str) -> Optional[Type[BaseMessage]]:
        return cls._handlers.get(message_type)

    @classmethod
    def list_types(cls) -> List[str]:
        return sorted(cls._handlers.keys())

    @classmethod
    def list_by_protocol(cls, protocol: Protocol) -> List[str]:
        return sorted(
            mt for mt, h in cls._handlers.items()
            if h.PROTOCOL == protocol
        )


def register_message(cls: Type[BaseMessage]) -> Type[BaseMessage]:
    MessageRegistry.register(cls)
    return cls


class MessageDispatcher:
    """
    Main entry point: raw JSON → resolve handler → validate → process.
    Accepts dict, JSON string, or .json file path.
    """

    @staticmethod
    def dispatch(input_data: Union[str, dict]) -> dict:
        # ── Parse input ──────────────────────────────────────────
        if isinstance(input_data, str):
            if input_data.strip().endswith(".json"):
                try:
                    with open(input_data, "r") as f:
                        data = json.load(f)
                except FileNotFoundError:
                    return {"status": "error", "error_code": "INVALID_MESSAGE",
                            "message": f"File not found: {input_data}"}
                except json.JSONDecodeError as e:
                    return {"status": "error", "error_code": "INVALID_MESSAGE",
                            "message": f"Invalid JSON in file: {e}"}
            else:
                try:
                    data = json.loads(input_data)
                except json.JSONDecodeError as e:
                    return {"status": "error", "error_code": "INVALID_MESSAGE",
                            "message": f"Invalid JSON string: {e}"}
        elif isinstance(input_data, dict):
            data = input_data
        else:
            return {"status": "error", "error_code": "INVALID_MESSAGE",
                    "message": f"Unsupported input type: {type(input_data).__name__}"}

        # ── Resolve handler ──────────────────────────────────────
        msg_type = data.get("message_type")
        if not msg_type:
            return {
                "status": "error",
                "error_code": "INVALID_MESSAGE",
                "message": "Missing 'message_type' in envelope",
                "supported_types": MessageRegistry.list_types(),
            }

        handler_cls = MessageRegistry.get_handler(msg_type)
        if handler_cls is None:
            return {
                "status": "error",
                "error_code": "INVALID_MESSAGE",
                "message": f"Unknown message_type: '{msg_type}'",
                "supported_types": MessageRegistry.list_types(),
            }

        # ── Validate & process ───────────────────────────────────
        handler = handler_cls(data)
        return handler.handle()

"""
q21_referee.errors — Custom exception classes
==============================================

Defines the exception hierarchy for callback errors.
Each exception stores full context for structured logging.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json


class Q21RefereeError(Exception):
    """Base exception for all Q21 Referee package errors."""
    pass


class CallbackTimeoutError(Q21RefereeError):
    """Raised when a callback exceeds its deadline."""

    def __init__(
        self,
        callback_name: str,
        deadline_seconds: int,
        input_payload: Dict[str, Any],
    ):
        self.callback_name = callback_name
        self.deadline_seconds = deadline_seconds
        self.input_payload = input_payload
        super().__init__(
            f"Callback '{callback_name}' timed out after {deadline_seconds} seconds"
        )

    def format_error_log(self) -> str:
        return _format_error_block(
            error_type="CALLBACK_TIMEOUT",
            callback_name=self.callback_name,
            deadline_seconds=self.deadline_seconds,
            input_payload=self.input_payload,
            output_payload=None,
            validation_errors=None,
        )


class InvalidJSONResponseError(Q21RefereeError):
    """Raised when a callback returns a non-dict value."""

    def __init__(
        self,
        callback_name: str,
        input_payload: Dict[str, Any],
        raw_output: Any,
    ):
        self.callback_name = callback_name
        self.input_payload = input_payload
        self.raw_output = raw_output
        self.raw_output_type = type(raw_output).__name__
        super().__init__(
            f"Callback '{callback_name}' returned {self.raw_output_type} instead of dict"
        )

    def format_error_log(self) -> str:
        return _format_error_block(
            error_type="INVALID_JSON_RESPONSE",
            callback_name=self.callback_name,
            deadline_seconds=None,
            input_payload=self.input_payload,
            output_payload={"raw_output": repr(self.raw_output), "type": self.raw_output_type},
            validation_errors=[f"Expected dict, got {self.raw_output_type}"],
        )


class SchemaValidationError(Q21RefereeError):
    """Raised when a callback's output fails schema validation."""

    def __init__(
        self,
        callback_name: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        validation_errors: List[str],
    ):
        self.callback_name = callback_name
        self.input_payload = input_payload
        self.output_payload = output_payload
        self.validation_errors = validation_errors
        super().__init__(
            f"Callback '{callback_name}' output failed validation: {validation_errors}"
        )

    def format_error_log(self) -> str:
        return _format_error_block(
            error_type="SCHEMA_VALIDATION_FAILURE",
            callback_name=self.callback_name,
            deadline_seconds=None,
            input_payload=self.input_payload,
            output_payload=self.output_payload,
            validation_errors=self.validation_errors,
        )


def _format_error_block(
    error_type: str,
    callback_name: str,
    deadline_seconds: Optional[int],
    input_payload: Dict[str, Any],
    output_payload: Optional[Dict[str, Any]],
    validation_errors: Optional[List[str]],
) -> str:
    """Format a structured error block per PRD specification."""
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    lines = [
        "",
        "=" * 64,
        " CALLBACK ERROR — PROCESS TERMINATED",
        "=" * 64,
        f" Timestamp:    {timestamp}",
        f" Error Type:   {error_type}",
        f" Callback:     {callback_name}",
    ]

    if deadline_seconds is not None:
        lines.append(f" Deadline:     {deadline_seconds} seconds")

    lines.append("")
    lines.append(" ── INPUT PAYLOAD " + "─" * 46)
    lines.append(_indent_json(input_payload))

    if output_payload is not None:
        lines.append("")
        lines.append(" ── OUTPUT PAYLOAD (from callback) " + "─" * 29)
        lines.append(_indent_json(output_payload))

    if validation_errors:
        lines.append("")
        lines.append(" ── VALIDATION ERRORS " + "─" * 42)
        for error in validation_errors:
            lines.append(f" • {error}")

    lines.append("")
    lines.append("=" * 64)
    lines.append("")

    return "\n".join(lines)


def _indent_json(data: Dict[str, Any], indent: int = 2) -> str:
    """Format JSON with indentation for error logs."""
    try:
        formatted = json.dumps(data, indent=indent, default=str)
        # Add leading space to each line
        return "\n".join(" " + line for line in formatted.split("\n"))
    except Exception:
        return f" {repr(data)}"

# Area: Shared
# PRD: docs/prd-rlgm.md
"""Error formatting for structured callback error logs."""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional


def format_error_block(
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
    lines.append(indent_json(input_payload))

    if output_payload is not None:
        lines.append("")
        lines.append(" ── OUTPUT PAYLOAD (from callback) " + "─" * 29)
        lines.append(indent_json(output_payload))

    if validation_errors:
        lines.append("")
        lines.append(" ── VALIDATION ERRORS " + "─" * 42)
        for error in validation_errors:
            lines.append(f" • {error}")

    lines.append("")
    lines.append("=" * 64)
    lines.append("")

    return "\n".join(lines)


def indent_json(data: Dict[str, Any], indent: int = 2) -> str:
    """Format JSON with indentation for error logs."""
    try:
        formatted = json.dumps(data, indent=indent, default=str)
        return "\n".join(" " + line for line in formatted.split("\n"))
    except Exception:
        return f" {repr(data)}"

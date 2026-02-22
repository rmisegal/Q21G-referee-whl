# Area: Shared
# PRD: docs/prd-rlgm.md
"""Gmail message parsing utilities."""

from __future__ import annotations

import base64
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("q21_referee.email")


def parse_message(msg: dict, service) -> Optional[Dict[str, Any]]:
    """Parse Gmail API message into standard format."""
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "")
    from_addr = headers.get("From", "")

    logger.info(f"Processing email: {subject} from {from_addr}")

    body = get_body(msg["payload"])

    # Try to parse body as JSON first
    body_json = None
    if body:
        try:
            body_json = json.loads(body.strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # If no JSON in body, check attachments
    if not body_json:
        body_json = get_json_from_attachments(msg, service)

    if body_json:
        logger.debug(
            f"Parsed JSON with message_type: "
            f"{body_json.get('message_type', 'N/A')}"
        )
    else:
        logger.debug("No JSON found in body, checking attachments...")

    return {
        "uid": msg["id"],
        "subject": subject,
        "from": from_addr,
        "body_json": body_json,
        "raw_body": body,
    }


def get_json_from_attachments(msg: dict, service) -> Optional[Dict[str, Any]]:
    """Extract JSON from email attachments."""
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    logger.info(f"Checking {len(parts)} parts for JSON attachments")

    for part in parts:
        filename = part.get("filename", "")
        mime_type = part.get("mimeType", "")
        logger.info(f"  Part: filename='{filename}', mimeType='{mime_type}'")

        # Check nested parts (multipart emails)
        if part.get("parts"):
            nested = get_json_from_attachments(
                {"payload": part, "id": msg.get("id", "")}, service
            )
            if nested:
                return nested

        # Look for JSON attachments
        if filename.endswith(".json") or mime_type == "application/json":
            result = _decode_json_part(part, msg, service)
            if result:
                return result

    return None


def _decode_json_part(part: dict, msg: dict, service) -> Optional[Dict[str, Any]]:
    """Decode a JSON attachment part (fetched or inline)."""
    body_data = part.get("body", {})
    attachment_id = body_data.get("attachmentId")
    filename = part.get("filename", "")

    if attachment_id:
        try:
            att = service.users().messages().attachments().get(
                userId="me", messageId=msg["id"], id=attachment_id,
            ).execute()
            data = att.get("data", "")
            if data:
                content = base64.urlsafe_b64decode(data).decode("utf-8")
                return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to get attachment {filename}: {e}")
    elif body_data.get("data"):
        try:
            content = base64.urlsafe_b64decode(body_data["data"]).decode("utf-8")
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to parse inline attachment: {e}")

    return None


def get_body(payload: dict) -> str:
    """Extract text body from message payload."""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8")
        elif part.get("parts"):
            result = get_body(part)
            if result:
                return result
    return ""

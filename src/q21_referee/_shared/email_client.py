# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee._shared.email_client — IMAP/SMTP email wrapper
==========================================================

Handles all email I/O. The runner calls poll() to get new messages
and send() to deliver outgoing messages. Students never use this directly.
"""

from __future__ import annotations
import imaplib
import smtplib
import email
import json
import time
import logging
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Any

logger = logging.getLogger("q21_referee.email")


class EmailClient:
    """
    Wraps IMAP (receive) and SMTP (send) for protocol messages.
    """

    def __init__(self, address: str, password: str,
                 imap_server: str = "imap.gmail.com",
                 smtp_server: str = "smtp.gmail.com",
                 imap_port: int = 993,
                 smtp_port: int = 587):
        self.address = address
        self.password = password
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.imap_port = imap_port
        self.smtp_port = smtp_port
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    # ── Connection management ─────────────────────────────────

    def connect_imap(self):
        """Establish IMAP connection."""
        try:
            self._imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self._imap.login(self.address, self.password)
            self._imap.select("INBOX")
            logger.info(f"IMAP connected: {self.address}")
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise

    def disconnect_imap(self):
        """Close IMAP connection."""
        if self._imap:
            try:
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

    # ── Polling ───────────────────────────────────────────────

    def poll(self, since_uid: int = 0,
             subject_filter: str = None) -> List[Dict[str, Any]]:
        """
        Poll inbox for new protocol messages.

        Returns list of dicts:
            [{"uid": int, "subject": str, "from": str,
              "body_json": dict | None, "raw_body": str}]
        """
        if not self._imap:
            self.connect_imap()

        messages = []
        try:
            # Search for unseen messages (or all since UID)
            search_criteria = "(UNSEEN)"
            if subject_filter:
                search_criteria = f'(UNSEEN SUBJECT "{subject_filter}")'

            status, data = self._imap.search(None, search_criteria)
            if status != "OK" or not data[0]:
                return []

            msg_nums = data[0].split()
            for num in msg_nums:
                try:
                    status, msg_data = self._imap.fetch(num, "(RFC822)")
                    if status != "OK":
                        continue

                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)

                    subject = msg.get("Subject", "")
                    from_addr = msg.get("From", "")

                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(
                                    "utf-8", errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(
                            "utf-8", errors="replace")

                    # Try to parse body as JSON
                    body_json = None
                    try:
                        body_json = json.loads(body.strip())
                    except (json.JSONDecodeError, ValueError):
                        pass

                    messages.append({
                        "uid": int(num),
                        "subject": subject,
                        "from": from_addr,
                        "body_json": body_json,
                        "raw_body": body,
                    })

                    # Mark as seen
                    self._imap.store(num, "+FLAGS", "\\Seen")

                except Exception as e:
                    logger.warning(f"Failed to process message {num}: {e}")
                    continue

        except imaplib.IMAP4.abort:
            logger.warning("IMAP connection lost, reconnecting...")
            self.connect_imap()
        except Exception as e:
            logger.error(f"Poll error: {e}")

        return messages

    # ── Sending ───────────────────────────────────────────────

    def send(self, to_email: str, subject: str,
             body_dict: dict) -> bool:
        """
        Send a protocol message as email.

        Parameters
        ----------
        to_email : str      Recipient email address
        subject  : str      Protocol-formatted subject line
        body_dict : dict    The full envelope (will be JSON-serialized)

        Returns
        -------
        bool    True if sent successfully
        """
        try:
            body_json = json.dumps(body_dict, indent=2)

            msg = MIMEText(body_json, "plain", "utf-8")
            msg["From"] = self.address
            msg["To"] = to_email
            msg["Subject"] = subject

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.address, self.password)
                server.send_message(msg)

            logger.info(f"Sent [{subject.split('::')[-1] if '::' in subject else subject}] → {to_email}")
            return True

        except Exception as e:
            logger.error(f"Send failed to {to_email}: {e}")
            return False

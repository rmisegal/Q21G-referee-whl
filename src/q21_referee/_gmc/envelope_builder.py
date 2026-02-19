# Area: GMC
# PRD: docs/prd-rlgm.md
# NOTE: This file is 212 lines - may need splitting in Part 22
"""
q21_referee._gmc.envelope_builder — Constructs outgoing protocol messages
=========================================================================

Takes the clean dicts returned by student callbacks and wraps them
in spec-compliant envelopes (§2) with proper email subjects (§3).
Students never call this directly.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def _msg_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _email_subject(protocol: str, role: str, email: str,
                   tx_id: str, message_type: str) -> str:
    return f"{protocol}::{role}::{email}::{tx_id}::{message_type}"


class EnvelopeBuilder:
    """
    Builds all outgoing messages the referee needs to send.
    Each method returns (envelope_dict, email_subject_str).
    """

    def __init__(self, referee_email: str, referee_id: str,
                 league_id: str, season_id: str):
        self.referee_email = referee_email
        self.referee_id = referee_id
        self.league_id = league_id
        self.season_id = season_id

    def _base_q21_envelope(self, message_type: str, recipient_id: str,
                           game_id: str, msg_id: str,
                           correlation_id: Optional[str] = None) -> dict:
        env = {
            "protocol": "Q21G.v1",
            "message_type": message_type,
            "message_id": msg_id,
            "timestamp": _now_iso(),
            "sender": {
                "email": self.referee_email,
                "role": "REFEREE",
                "logical_id": self.referee_id,
            },
            "recipient_id": recipient_id,
            "game_id": game_id,
        }
        if correlation_id:
            env["correlation_id"] = correlation_id
        return env

    def _base_league_envelope(self, message_type: str, recipient_id: str,
                              msg_id: str, round_id: str = None,
                              game_id: str = None,
                              correlation_id: str = None) -> dict:
        env = {
            "protocol": "league.v2",
            "message_type": message_type,
            "message_id": msg_id,
            "timestamp": _now_iso(),
            "sender": {
                "email": self.referee_email,
                "role": "REFEREE",
                "logical_id": self.referee_id,
            },
            "recipient_id": recipient_id,
            "league_id": self.league_id,
            "season_id": self.season_id,
        }
        if round_id:
            env["round_id"] = round_id
        if game_id:
            env["game_id"] = game_id
        if correlation_id:
            env["correlation_id"] = correlation_id
        return env

    # ── Q21WARMUPCALL (§7.2) ──────────────────────────────────

    def build_warmup_call(self, player_id: str, game_id: str,
                          match_id: str, warmup_question: str,
                          auth_token: str,
                          deadline_minutes: int = 2) -> tuple[dict, str]:
        msg_id = _msg_id(f"warmup-{match_id}-{player_id}")
        deadline = datetime.now(timezone.utc)
        # Add deadline_minutes
        from datetime import timedelta
        deadline = (deadline + timedelta(minutes=deadline_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f+00:00")

        env = self._base_q21_envelope("Q21WARMUPCALL", player_id,
                                       game_id, msg_id)
        env["payload"] = {
            "match_id": match_id,
            "warmup_question": warmup_question,
            "deadline": deadline,
            "auth_token": auth_token,
        }
        subject = _email_subject("Q21G.v1", "REFEREE", self.referee_email,
                                  msg_id, "Q21WARMUPCALL")
        return env, subject

    # ── Q21ROUNDSTART (§7.4) ──────────────────────────────────

    def build_round_start(self, player_id: str, game_id: str,
                          match_id: str, book_name: str,
                          book_hint: str, association_word: str,
                          auth_token: str,
                          questions_required: int = 20,
                          deadline_minutes: int = 5) -> tuple[dict, str]:
        msg_id = _msg_id(f"round-start-{match_id}-{player_id}")
        from datetime import timedelta
        deadline = (datetime.now(timezone.utc) + timedelta(minutes=deadline_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f+00:00")

        env = self._base_q21_envelope("Q21ROUNDSTART", player_id,
                                       game_id, msg_id)
        env["payload"] = {
            "match_id": match_id,
            "book_name": book_name,
            "book_hint": book_hint,
            "association_word": association_word,
            "questions_required": questions_required,
            "deadline": deadline,
            "auth_token": auth_token,
        }
        subject = _email_subject("Q21G.v1", "REFEREE", self.referee_email,
                                  msg_id, "Q21ROUNDSTART")
        return env, subject

    # ── Q21ANSWERSBATCH (§7.6) ────────────────────────────────

    def build_answers_batch(self, player_id: str, game_id: str,
                            match_id: str, answers: list,
                            auth_token: str,
                            correlation_id: str = None,
                            deadline_minutes: int = 5) -> tuple[dict, str]:
        msg_id = _msg_id(f"answers-{match_id}-{player_id}")
        from datetime import timedelta
        deadline = (datetime.now(timezone.utc) + timedelta(minutes=deadline_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f+00:00")

        env = self._base_q21_envelope("Q21ANSWERSBATCH", player_id,
                                       game_id, msg_id,
                                       correlation_id=correlation_id)
        env["payload"] = {
            "match_id": match_id,
            "answers": answers,
            "deadline": deadline,
            "auth_token": auth_token,
        }
        subject = _email_subject("Q21G.v1", "REFEREE", self.referee_email,
                                  msg_id, "Q21ANSWERSBATCH")
        return env, subject

    # ── Q21SCOREFEEDBACK (§7.8) ───────────────────────────────

    def build_score_feedback(self, player_id: str, game_id: str,
                             match_id: str, league_points: int,
                             private_score: float, breakdown: dict,
                             feedback: dict = None,
                             correlation_id: str = None) -> tuple[dict, str]:
        msg_id = _msg_id(f"score-{match_id}-{player_id}")

        env = self._base_q21_envelope("Q21SCOREFEEDBACK", player_id,
                                       game_id, msg_id,
                                       correlation_id=correlation_id)
        env["payload"] = {
            "match_id": match_id,
            "league_points": league_points,
            "private_score": private_score,
            "breakdown": breakdown,
        }
        if feedback:
            env["payload"]["feedback"] = feedback
        subject = _email_subject("Q21G.v1", "REFEREE", self.referee_email,
                                  msg_id, "Q21SCOREFEEDBACK")
        return env, subject

    # ── MATCH_RESULT_REPORT (§7.9) ────────────────────────────

    def build_match_result(self, game_id: str, match_id: str,
                           round_id: str, winner_id: str,
                           is_draw: bool, scores: list,
                           correlation_id: str = None,
                           status: str = "completed",
                           abort_reason: str = None,
                           player_states: dict = None) -> tuple[dict, str]:
        msg_id = _msg_id(f"result-{match_id}")

        env = self._base_league_envelope(
            "MATCH_RESULT_REPORT", "LEAGUEMANAGER", msg_id,
            round_id=round_id, game_id=game_id,
            correlation_id=correlation_id)
        env["payload"] = {
            "match_id": match_id,
            "status": status,
            "winner_id": winner_id,
            "is_draw": is_draw,
            "scores": scores,
        }
        if abort_reason:
            env["payload"]["abort_reason"] = abort_reason
        if player_states:
            env["payload"]["player_states"] = player_states
        subject = _email_subject("league.v2", "REFEREE", self.referee_email,
                                  msg_id, "MATCH_RESULT_REPORT")
        return env, subject

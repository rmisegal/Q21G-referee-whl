# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.envelope_builder — Constructs outgoing protocol messages
=========================================================================

Takes the clean dicts returned by student callbacks and wraps them
in spec-compliant envelopes (§2) with proper email subjects (§3).
Students never call this directly.
"""

from __future__ import annotations

from .envelope_helpers import (
    base_league_envelope, base_q21_envelope, deadline_iso,
    email_subject, msg_id,
)


class EnvelopeBuilder:
    """Builds all outgoing messages the referee needs to send.
    Each method returns (envelope_dict, email_subject_str)."""

    def __init__(self, referee_email: str, referee_id: str,
                 league_id: str, season_id: str):
        self.referee_email = referee_email
        self.referee_id = referee_id
        self.league_id = league_id
        self.season_id = season_id

    def _base_q21_envelope(self, mtype: str, player_id: str, game_id: str,
                           mid: str, correlation_id: str = None) -> dict:
        return base_q21_envelope(mtype, mid, player_id, game_id,
                                 self.referee_email, self.referee_id,
                                 correlation_id=correlation_id)

    def _base_league_envelope(self, mtype: str, recipient_id: str, mid: str,
                              round_id: str = None, game_id: str = None,
                              correlation_id: str = None) -> dict:
        return base_league_envelope(mtype, mid, recipient_id,
                                    self.referee_email, self.referee_id,
                                    self.league_id, self.season_id,
                                    round_id=round_id, game_id=game_id,
                                    correlation_id=correlation_id)

    def _email_subject(self, protocol: str, mid: str, mtype: str) -> str:
        return email_subject(protocol, "REFEREE", self.referee_email,
                             mid, mtype)

    def build_warmup_call(self, player_id: str, game_id: str,
                          match_id: str, warmup_question: str,
                          auth_token: str,
                          deadline_minutes: int = 2) -> tuple[dict, str]:
        mid = msg_id(f"warmup-{match_id}-{player_id}")
        env = self._base_q21_envelope("Q21WARMUPCALL", player_id, game_id, mid)
        env["payload"] = {
            "match_id": match_id,
            "warmup_question": warmup_question,
            "deadline": deadline_iso(deadline_minutes),
            "auth_token": auth_token,
        }
        return env, self._email_subject("Q21G.v1", mid, "Q21WARMUPCALL")

    def build_round_start(self, player_id: str, game_id: str,
                          match_id: str, book_name: str,
                          book_hint: str, association_word: str,
                          auth_token: str,
                          questions_required: int = 20,
                          deadline_minutes: int = 5) -> tuple[dict, str]:
        mid = msg_id(f"round-start-{match_id}-{player_id}")
        env = self._base_q21_envelope("Q21ROUNDSTART", player_id, game_id, mid)
        env["payload"] = {
            "match_id": match_id,
            "book_name": book_name,
            "book_hint": book_hint,
            "association_word": association_word,
            "questions_required": questions_required,
            "deadline": deadline_iso(deadline_minutes),
            "auth_token": auth_token,
        }
        return env, self._email_subject("Q21G.v1", mid, "Q21ROUNDSTART")

    def build_answers_batch(self, player_id: str, game_id: str,
                            match_id: str, answers: list,
                            auth_token: str,
                            correlation_id: str = None,
                            deadline_minutes: int = 5) -> tuple[dict, str]:
        mid = msg_id(f"answers-{match_id}-{player_id}")
        env = self._base_q21_envelope("Q21ANSWERSBATCH", player_id, game_id, mid,
                         correlation_id=correlation_id)
        env["payload"] = {
            "match_id": match_id,
            "answers": answers,
            "deadline": deadline_iso(deadline_minutes),
            "auth_token": auth_token,
        }
        return env, self._email_subject("Q21G.v1", mid, "Q21ANSWERSBATCH")

    def build_score_feedback(self, player_id: str, game_id: str,
                             match_id: str, league_points: int,
                             private_score: float, breakdown: dict,
                             feedback: dict = None,
                             correlation_id: str = None) -> tuple[dict, str]:
        mid = msg_id(f"score-{match_id}-{player_id}")
        env = self._base_q21_envelope("Q21SCOREFEEDBACK", player_id, game_id, mid,
                         correlation_id=correlation_id)
        env["payload"] = {
            "match_id": match_id,
            "league_points": league_points,
            "private_score": private_score,
            "breakdown": breakdown,
        }
        if feedback is not None:
            env["payload"]["feedback"] = feedback
        return env, self._email_subject("Q21G.v1", mid, "Q21SCOREFEEDBACK")

    def build_match_result(self, game_id: str, match_id: str,
                           round_id: str, winner_id: str,
                           is_draw: bool, scores: list,
                           correlation_id: str = None,
                           status: str = "completed",
                           abort_reason: str = None,
                           player_states: dict = None) -> tuple[dict, str]:
        mid = msg_id(f"result-{match_id}")
        env = self._base_league_envelope("MATCH_RESULT_REPORT", "LEAGUEMANAGER", mid,
                           round_id=round_id, game_id=game_id,
                           correlation_id=correlation_id)
        env["payload"] = {
            "match_id": match_id,
            "status": status,
            "winner_id": winner_id,
            "is_draw": is_draw,
            "scores": scores,
        }
        if abort_reason is not None:
            env["payload"]["abort_reason"] = abort_reason
        if player_states is not None:
            env["payload"]["player_states"] = player_states
        return env, self._email_subject("league.v2", mid, "MATCH_RESULT_REPORT")

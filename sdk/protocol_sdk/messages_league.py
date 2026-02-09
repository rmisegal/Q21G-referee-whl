"""
League Protocol Messages (league.v2)
=====================================
§5.3  BROADCAST_START_SEASON
§5.4  SEASON_REGISTRATION_REQUEST
§5.5  SEASON_REGISTRATION_RESPONSE
§5.6  BROADCAST_ASSIGNMENT_TABLE
§6.1  BROADCAST_NEW_LEAGUE_ROUND
§7.9  MATCH_RESULT_REPORT
§7.10 LEAGUE_COMPLETED
"""

from .core import (
    BaseMessage, FieldValidator, ValidationResult, FieldError,
    Protocol, MessageDirection, register_message,
)


# ═══════════════════════════════════════════════════════════════════
# §5.3  BROADCAST_START_SEASON
# Direction: LeagueManager → All registered participants
# Required context: league_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class BroadcastStartSeason(BaseMessage):
    MESSAGE_TYPE = "BROADCAST_START_SEASON"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.LM_TO_ALL
    REQUIRED_CONTEXT_FIELDS = ["league_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "broadcast_id", r, pf)
        self.fv.non_empty_string(p.get("broadcast_id"), "broadcast_id", r, pf)

        self.fv.required(p, "season_id", r, pf)
        self.fv.non_empty_string(p.get("season_id"), "season_id", r, pf)

        self.fv.required(p, "season_name", r, pf)
        self.fv.non_empty_string(p.get("season_name"), "season_name", r, pf)

        self.fv.required(p, "game_type", r, pf)
        self.fv.one_of(p.get("game_type"), "game_type", ["Q21"], r, pf)

        self.fv.required(p, "total_rounds", r, pf)
        self.fv.positive_int(p.get("total_rounds"), "total_rounds", r, pf)

        self.fv.required(p, "registration_deadline", r, pf)
        self.fv.iso_datetime(p.get("registration_deadline"), "registration_deadline", r, pf)

        # message_text is optional

    def process_payload(self) -> dict:
        return {
            "broadcast_id": self.payload["broadcast_id"],
            "season_id": self.payload["season_id"],
            "season_name": self.payload["season_name"],
            "game_type": self.payload["game_type"],
            "total_rounds": self.payload["total_rounds"],
            "registration_deadline": self.payload["registration_deadline"],
            "message_text": self.payload.get("message_text"),
        }


# ═══════════════════════════════════════════════════════════════════
# §5.4  SEASON_REGISTRATION_REQUEST
# Direction: Player/Referee → LeagueManager
# Required context: league_id
# Envelope should include correlation_id (links to BROADCAST_START_SEASON)
# ═══════════════════════════════════════════════════════════════════

@register_message
class SeasonRegistrationRequest(BaseMessage):
    MESSAGE_TYPE = "SEASON_REGISTRATION_REQUEST"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.PR_TO_LM
    REQUIRED_CONTEXT_FIELDS = ["league_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "season_id", r, pf)
        self.fv.non_empty_string(p.get("season_id"), "season_id", r, pf)

        self.fv.required(p, "user_id", r, pf)
        self.fv.non_empty_string(p.get("user_id"), "user_id", r, pf)

        self.fv.required(p, "participant_id", r, pf)
        self.fv.non_empty_string(p.get("participant_id"), "participant_id", r, pf)

        self.fv.required(p, "display_name", r, pf)
        self.fv.non_empty_string(p.get("display_name"), "display_name", r, pf)

    def process_payload(self) -> dict:
        return {
            "season_id": self.payload["season_id"],
            "user_id": self.payload["user_id"],
            "participant_id": self.payload["participant_id"],
            "display_name": self.payload["display_name"],
            "registration_received": True,
        }


# ═══════════════════════════════════════════════════════════════════
# §5.5  SEASON_REGISTRATION_RESPONSE
# Direction: LeagueManager → Player/Referee
# Required context: league_id, season_id
# Envelope should include correlation_id (links to SEASON_REGISTRATION_REQUEST)
# ═══════════════════════════════════════════════════════════════════

@register_message
class SeasonRegistrationResponse(BaseMessage):
    MESSAGE_TYPE = "SEASON_REGISTRATION_RESPONSE"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.LM_TO_PR
    REQUIRED_CONTEXT_FIELDS = ["league_id", "season_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "status", r, pf)
        self.fv.one_of(p.get("status"), "status", ["accepted", "rejected"], r, pf)

        self.fv.required(p, "season_id", r, pf)
        self.fv.non_empty_string(p.get("season_id"), "season_id", r, pf)

        # message is optional
        # reason is required IF status == "rejected"
        if p.get("status") == "rejected":
            self.fv.required(p, "reason", r, pf)
            self.fv.non_empty_string(p.get("reason"), "reason", r, pf)

    def process_payload(self) -> dict:
        return {
            "status": self.payload["status"],
            "season_id": self.payload["season_id"],
            "message": self.payload.get("message"),
            "reason": self.payload.get("reason"),
        }


# ═══════════════════════════════════════════════════════════════════
# §5.6  BROADCAST_ASSIGNMENT_TABLE
# Direction: LeagueManager → All season participants
# Required context: league_id, season_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class BroadcastAssignmentTable(BaseMessage):
    MESSAGE_TYPE = "BROADCAST_ASSIGNMENT_TABLE"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.LM_TO_ALL
    REQUIRED_CONTEXT_FIELDS = ["league_id", "season_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "broadcast_id", r, pf)
        self.fv.non_empty_string(p.get("broadcast_id"), "broadcast_id", r, pf)

        self.fv.required(p, "season_id", r, pf)
        self.fv.non_empty_string(p.get("season_id"), "season_id", r, pf)

        self.fv.required(p, "league_id", r, pf)
        self.fv.non_empty_string(p.get("league_id"), "league_id", r, pf)

        # assignments array
        assignments = self.fv.required(p, "assignments", r, pf)
        if assignments is not None and self.fv.is_list(assignments, "assignments", r, pf, min_length=1):
            for i, a in enumerate(assignments):
                ap = f"payload.assignments[{i}]."
                if not isinstance(a, dict):
                    r.add_error(FieldError(f"payload.assignments[{i}]", "invalid_type",
                                           expected="object", received=type(a).__name__))
                    continue
                # Each assignment: role, email, game_id, group_id
                self.fv.required(a, "role", r, ap)
                self.fv.one_of(a.get("role"), "role",
                               ["player1", "player2", "referee"], r, ap)
                self.fv.required(a, "email", r, ap)
                self.fv.non_empty_string(a.get("email"), "email", r, ap)
                self.fv.required(a, "game_id", r, ap)
                self.fv.non_empty_string(a.get("game_id"), "game_id", r, ap)
                # game_id format: 7-digit SSRRGGG
                if a.get("game_id"):
                    self.fv.game_id_format(a["game_id"], "game_id", r, ap)
                self.fv.required(a, "group_id", r, ap)
                self.fv.non_empty_string(a.get("group_id"), "group_id", r, ap)

        self.fv.required(p, "total_count", r, pf)
        self.fv.positive_int(p.get("total_count"), "total_count", r, pf)

        # message_text is optional

    def process_payload(self) -> dict:
        return {
            "broadcast_id": self.payload["broadcast_id"],
            "season_id": self.payload["season_id"],
            "league_id": self.payload["league_id"],
            "assignments": self.payload["assignments"],
            "total_count": self.payload["total_count"],
            "message_text": self.payload.get("message_text"),
        }


# ═══════════════════════════════════════════════════════════════════
# §6.1  BROADCAST_NEW_LEAGUE_ROUND
# Direction: LeagueManager → All season participants
# Required context: league_id, season_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class BroadcastNewLeagueRound(BaseMessage):
    MESSAGE_TYPE = "BROADCAST_NEW_LEAGUE_ROUND"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.LM_TO_ALL
    REQUIRED_CONTEXT_FIELDS = ["league_id", "season_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "broadcast_id", r, pf)
        self.fv.non_empty_string(p.get("broadcast_id"), "broadcast_id", r, pf)

        self.fv.required(p, "round_id", r, pf)
        self.fv.non_empty_string(p.get("round_id"), "round_id", r, pf)

        self.fv.required(p, "round_number", r, pf)
        self.fv.positive_int(p.get("round_number"), "round_number", r, pf)

        # message_text is optional

    def process_payload(self) -> dict:
        return {
            "broadcast_id": self.payload["broadcast_id"],
            "round_id": self.payload["round_id"],
            "round_number": self.payload["round_number"],
            "message_text": self.payload.get("message_text"),
        }


# ═══════════════════════════════════════════════════════════════════
# §7.9  MATCH_RESULT_REPORT
# Direction: Referee → LeagueManager
# Required context: league_id, season_id, round_id, game_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class MatchResultReport(BaseMessage):
    MESSAGE_TYPE = "MATCH_RESULT_REPORT"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.REFEREE_TO_LM
    REQUIRED_CONTEXT_FIELDS = ["league_id", "season_id", "round_id", "game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "status", r, pf)
        self.fv.one_of(p.get("status"), "status",
                        ["completed", "abandoned", "timeout"], r, pf)

        # winner_id is optional (null if draw)

        self.fv.required(p, "is_draw", r, pf)
        self.fv.expected_type(p.get("is_draw"), "is_draw", bool, r, pf)

        # scores array
        scores = self.fv.required(p, "scores", r, pf)
        if scores is not None and self.fv.is_list(scores, "scores", r, pf, min_length=1):
            for i, s in enumerate(scores):
                sp = f"payload.scores[{i}]."
                if not isinstance(s, dict):
                    r.add_error(FieldError(f"payload.scores[{i}]", "invalid_type",
                                           expected="object", received=type(s).__name__))
                    continue
                self.fv.required(s, "participant_id", r, sp)
                self.fv.non_empty_string(s.get("participant_id"), "participant_id", r, sp)
                self.fv.required(s, "email", r, sp)
                self.fv.non_empty_string(s.get("email"), "email", r, sp)
                self.fv.required(s, "league_points", r, sp)
                self.fv.non_negative_int(s.get("league_points"), "league_points", r, sp)
                self.fv.required(s, "private_score", r, sp)
                self.fv.number_in_range(s.get("private_score"), "private_score",
                                        0, 100, r, sp)

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "status": self.payload["status"],
            "winner_id": self.payload.get("winner_id"),
            "is_draw": self.payload["is_draw"],
            "scores": self.payload["scores"],
        }


# ═══════════════════════════════════════════════════════════════════
# §7.10  LEAGUE_COMPLETED
# Direction: LeagueManager → All season participants
# Required context: league_id, season_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class LeagueCompleted(BaseMessage):
    MESSAGE_TYPE = "LEAGUE_COMPLETED"
    PROTOCOL = Protocol.LEAGUE
    DIRECTION = MessageDirection.LM_TO_ALL
    REQUIRED_CONTEXT_FIELDS = ["league_id", "season_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "broadcast_id", r, pf)
        self.fv.non_empty_string(p.get("broadcast_id"), "broadcast_id", r, pf)

        self.fv.required(p, "season_id", r, pf)
        self.fv.non_empty_string(p.get("season_id"), "season_id", r, pf)

        # final_standings array
        standings = self.fv.required(p, "final_standings", r, pf)
        if standings is not None and self.fv.is_list(standings, "final_standings", r, pf, min_length=1):
            for i, s in enumerate(standings):
                sp = f"payload.final_standings[{i}]."
                if not isinstance(s, dict):
                    r.add_error(FieldError(f"payload.final_standings[{i}]",
                                           "invalid_type", expected="object",
                                           received=type(s).__name__))
                    continue
                self.fv.required(s, "rank", r, sp)
                self.fv.positive_int(s.get("rank"), "rank", r, sp)
                self.fv.required(s, "participant_id", r, sp)
                self.fv.non_empty_string(s.get("participant_id"), "participant_id", r, sp)
                self.fv.required(s, "display_name", r, sp)
                self.fv.non_empty_string(s.get("display_name"), "display_name", r, sp)
                self.fv.required(s, "total_points", r, sp)
                self.fv.non_negative_int(s.get("total_points"), "total_points", r, sp)

        # message_text is optional

    def process_payload(self) -> dict:
        return {
            "broadcast_id": self.payload["broadcast_id"],
            "season_id": self.payload["season_id"],
            "final_standings": self.payload["final_standings"],
            "message_text": self.payload.get("message_text"),
        }

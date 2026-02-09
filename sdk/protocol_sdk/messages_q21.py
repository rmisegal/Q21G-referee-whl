"""
Q21 Game Protocol Messages (Q21G.v1)
=====================================
§7.2  Q21WARMUPCALL
§7.3  Q21WARMUPRESPONSE
§7.4  Q21ROUNDSTART
§7.5  Q21QUESTIONSBATCH
§7.6  Q21ANSWERSBATCH
§7.7  Q21GUESSSUBMISSION
§7.8  Q21SCOREFEEDBACK

Note: Q21 game messages use protocol "Q21G.v1" (not "league.v2").
      Message types have NO underscores.
      Required context field: game_id
"""

from .core import (
    BaseMessage, FieldValidator, ValidationResult, FieldError,
    Protocol, MessageDirection, register_message,
)


# ═══════════════════════════════════════════════════════════════════
# §7.2  Q21WARMUPCALL
# Direction: Referee → Player
# Required context: game_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21WarmupCall(BaseMessage):
    MESSAGE_TYPE = "Q21WARMUPCALL"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.REFEREE_TO_PLAYER
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "warmup_question", r, pf)
        self.fv.non_empty_string(p.get("warmup_question"), "warmup_question", r, pf)

        self.fv.required(p, "deadline", r, pf)
        self.fv.iso_datetime(p.get("deadline"), "deadline", r, pf)

        # auth_token is optional

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "warmup_question": self.payload["warmup_question"],
            "deadline": self.payload["deadline"],
            "auth_token": self.payload.get("auth_token"),
        }


# ═══════════════════════════════════════════════════════════════════
# §7.3  Q21WARMUPRESPONSE
# Direction: Player → Referee
# Required context: game_id
# Envelope must include correlation_id → links to Q21WARMUPCALL.message_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21WarmupResponse(BaseMessage):
    MESSAGE_TYPE = "Q21WARMUPRESPONSE"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.PLAYER_TO_REFEREE
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "answer", r, pf)
        self.fv.non_empty_string(p.get("answer"), "answer", r, pf)

        self.fv.required(p, "auth_token", r, pf)
        self.fv.non_empty_string(p.get("auth_token"), "auth_token", r, pf)

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "answer": self.payload["answer"],
            "auth_token": self.payload["auth_token"],
        }


# ═══════════════════════════════════════════════════════════════════
# §7.4  Q21ROUNDSTART
# Direction: Referee → Player
# Required context: game_id
# Triggers upon receiving Q21WARMUPRESPONSE from BOTH players
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21RoundStart(BaseMessage):
    MESSAGE_TYPE = "Q21ROUNDSTART"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.REFEREE_TO_PLAYER
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "book_name", r, pf)
        self.fv.non_empty_string(p.get("book_name"), "book_name", r, pf)

        self.fv.required(p, "book_hint", r, pf)
        self.fv.non_empty_string(p.get("book_hint"), "book_hint", r, pf)

        self.fv.required(p, "association_word", r, pf)
        self.fv.non_empty_string(p.get("association_word"), "association_word", r, pf)

        self.fv.required(p, "questions_required", r, pf)
        self.fv.positive_int(p.get("questions_required"), "questions_required", r, pf)

        self.fv.required(p, "deadline", r, pf)
        self.fv.iso_datetime(p.get("deadline"), "deadline", r, pf)

        # auth_token is optional

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "book_name": self.payload["book_name"],
            "book_hint": self.payload["book_hint"],
            "association_word": self.payload["association_word"],
            "questions_required": self.payload["questions_required"],
            "deadline": self.payload["deadline"],
            "auth_token": self.payload.get("auth_token"),
        }


# ═══════════════════════════════════════════════════════════════════
# §7.5  Q21QUESTIONSBATCH
# Direction: Player → Referee
# Required context: game_id
# Envelope must include correlation_id → links to Q21ROUNDSTART.message_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21QuestionsBatch(BaseMessage):
    MESSAGE_TYPE = "Q21QUESTIONSBATCH"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.PLAYER_TO_REFEREE
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "auth_token", r, pf)
        self.fv.non_empty_string(p.get("auth_token"), "auth_token", r, pf)

        self.fv.required(p, "total_questions", r, pf)
        self.fv.positive_int(p.get("total_questions"), "total_questions", r, pf)

        # questions array
        questions = self.fv.required(p, "questions", r, pf)
        if questions is not None and self.fv.is_list(questions, "questions", r, pf, min_length=1):
            for i, q in enumerate(questions):
                qp = f"payload.questions[{i}]."
                if not isinstance(q, dict):
                    r.add_error(FieldError(f"payload.questions[{i}]",
                                           "invalid_type", expected="object",
                                           received=type(q).__name__))
                    continue

                self.fv.required(q, "question_number", r, qp)
                self.fv.positive_int(q.get("question_number"), "question_number", r, qp)

                self.fv.required(q, "question_text", r, qp)
                self.fv.non_empty_string(q.get("question_text"), "question_text", r, qp)

                # options object with keys A, B, C, D
                opts = self.fv.required(q, "options", r, qp)
                if opts is not None:
                    self.fv.expected_type(opts, "options", dict, r, qp)
                    if isinstance(opts, dict):
                        for key in ["A", "B", "C", "D"]:
                            self.fv.required(opts, key, r, f"{qp}options.")
                            self.fv.non_empty_string(opts.get(key), key, r, f"{qp}options.")

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "auth_token": self.payload["auth_token"],
            "questions": self.payload["questions"],
            "total_questions": self.payload["total_questions"],
        }


# ═══════════════════════════════════════════════════════════════════
# §7.6  Q21ANSWERSBATCH
# Direction: Referee → Player
# Required context: game_id
# Envelope must include correlation_id → links to Q21QUESTIONSBATCH.message_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21AnswersBatch(BaseMessage):
    MESSAGE_TYPE = "Q21ANSWERSBATCH"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.REFEREE_TO_PLAYER
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        # answers array
        answers = self.fv.required(p, "answers", r, pf)
        if answers is not None and self.fv.is_list(answers, "answers", r, pf, min_length=1):
            for i, a in enumerate(answers):
                ap = f"payload.answers[{i}]."
                if not isinstance(a, dict):
                    r.add_error(FieldError(f"payload.answers[{i}]",
                                           "invalid_type", expected="object",
                                           received=type(a).__name__))
                    continue

                self.fv.required(a, "question_number", r, ap)
                self.fv.positive_int(a.get("question_number"), "question_number", r, ap)

                self.fv.required(a, "answer", r, ap)
                self.fv.one_of(a.get("answer"), "answer",
                               ["A", "B", "C", "D", "Not Relevant"], r, ap)

        self.fv.required(p, "deadline", r, pf)
        self.fv.iso_datetime(p.get("deadline"), "deadline", r, pf)

        # auth_token is optional

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "answers": self.payload["answers"],
            "deadline": self.payload["deadline"],
            "auth_token": self.payload.get("auth_token"),
        }


# ═══════════════════════════════════════════════════════════════════
# §7.7  Q21GUESSSUBMISSION
# Direction: Player → Referee
# Required context: game_id
# Envelope must include correlation_id → links to Q21ANSWERSBATCH.message_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21GuessSubmission(BaseMessage):
    MESSAGE_TYPE = "Q21GUESSSUBMISSION"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.PLAYER_TO_REFEREE
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "auth_token", r, pf)
        self.fv.non_empty_string(p.get("auth_token"), "auth_token", r, pf)

        self.fv.required(p, "opening_sentence", r, pf)
        self.fv.non_empty_string(p.get("opening_sentence"), "opening_sentence", r, pf)

        # sentence_justification: required, 30-50 words
        self.fv.required(p, "sentence_justification", r, pf)
        self.fv.non_empty_string(p.get("sentence_justification"),
                                 "sentence_justification", r, pf)
        if p.get("sentence_justification") and isinstance(p["sentence_justification"], str):
            self.fv.word_count_range(p["sentence_justification"],
                                     "sentence_justification", 30, 50, r, pf)

        self.fv.required(p, "associative_word", r, pf)
        self.fv.non_empty_string(p.get("associative_word"), "associative_word", r, pf)

        # word_justification: required, 20-30 words
        self.fv.required(p, "word_justification", r, pf)
        self.fv.non_empty_string(p.get("word_justification"),
                                 "word_justification", r, pf)
        if p.get("word_justification") and isinstance(p["word_justification"], str):
            self.fv.word_count_range(p["word_justification"],
                                     "word_justification", 20, 30, r, pf)

        # confidence is optional, 0.0–1.0
        if "confidence" in p and p["confidence"] is not None:
            self.fv.number_in_range(p["confidence"], "confidence", 0.0, 1.0, r, pf)

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "auth_token": self.payload["auth_token"],
            "opening_sentence": self.payload["opening_sentence"],
            "sentence_justification": self.payload["sentence_justification"],
            "associative_word": self.payload["associative_word"],
            "word_justification": self.payload["word_justification"],
            "confidence": self.payload.get("confidence"),
        }


# ═══════════════════════════════════════════════════════════════════
# §7.8  Q21SCOREFEEDBACK
# Direction: Referee → Player  (terminal — no response expected)
# Required context: game_id
# Envelope must include correlation_id → links to Q21GUESSSUBMISSION.message_id
# ═══════════════════════════════════════════════════════════════════

@register_message
class Q21ScoreFeedback(BaseMessage):
    MESSAGE_TYPE = "Q21SCOREFEEDBACK"
    PROTOCOL = Protocol.Q21G
    DIRECTION = MessageDirection.REFEREE_TO_PLAYER
    REQUIRED_CONTEXT_FIELDS = ["game_id"]

    def validate_payload(self, r: ValidationResult) -> None:
        p = self.payload
        pf = "payload."

        self.fv.required(p, "match_id", r, pf)
        self.fv.non_empty_string(p.get("match_id"), "match_id", r, pf)

        self.fv.required(p, "league_points", r, pf)
        self.fv.non_negative_int(p.get("league_points"), "league_points", r, pf)
        # league_points should be 0-3
        if isinstance(p.get("league_points"), int):
            self.fv.number_in_range(p["league_points"], "league_points", 0, 3, r, pf)

        self.fv.required(p, "private_score", r, pf)
        self.fv.number_in_range(p.get("private_score"), "private_score", 0, 100, r, pf)

        # breakdown object
        bd = self.fv.required(p, "breakdown", r, pf)
        if bd is not None:
            self.fv.expected_type(bd, "breakdown", dict, r, pf)
            if isinstance(bd, dict):
                bp = "payload.breakdown."
                self.fv.required(bd, "opening_sentence_score", r, bp)
                self.fv.number_in_range(bd.get("opening_sentence_score"),
                                        "opening_sentence_score", 0, 100, r, bp)
                self.fv.required(bd, "sentence_justification_score", r, bp)
                self.fv.number_in_range(bd.get("sentence_justification_score"),
                                        "sentence_justification_score", 0, 100, r, bp)
                self.fv.required(bd, "associative_word_score", r, bp)
                self.fv.number_in_range(bd.get("associative_word_score"),
                                        "associative_word_score", 0, 100, r, bp)
                self.fv.required(bd, "word_justification_score", r, bp)
                self.fv.number_in_range(bd.get("word_justification_score"),
                                        "word_justification_score", 0, 100, r, bp)

        # feedback is optional
        if "feedback" in p and p["feedback"] is not None:
            self.fv.expected_type(p["feedback"], "feedback", dict, r, pf)

    def process_payload(self) -> dict:
        return {
            "match_id": self.payload["match_id"],
            "league_points": self.payload["league_points"],
            "private_score": self.payload["private_score"],
            "breakdown": self.payload["breakdown"],
            "feedback": self.payload.get("feedback"),
            "terminal": True,
        }

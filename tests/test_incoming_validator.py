# Area: GMC
# PRD: docs/prd-rlgm.md
"""Tests for q21_referee._gmc.incoming_validator — player message validation."""

from q21_referee._gmc.incoming_validator import validate_player_message


# ── Helpers ──────────────────────────────────────────────────


def _valid_warmup() -> dict:
    return {
        "message_type": "Q21_WARMUP_RESPONSE",
        "sender": {"email": "p1@test.com"},
        "payload": {"answer": "4"},
    }


def _valid_questions() -> dict:
    return {
        "message_type": "Q21_QUESTIONS_BATCH",
        "sender": {"email": "p1@test.com"},
        "payload": {"questions": [{"q": "What?"}]},
    }


def _valid_guess() -> dict:
    return {
        "message_type": "Q21_GUESS_SUBMISSION",
        "sender": {"email": "p1@test.com"},
        "payload": {"opening_sentence": "It was...", "associative_word": "cat"},
    }


# ── Valid messages ───────────────────────────────────────────


def test_valid_warmup_response():
    errors = validate_player_message(_valid_warmup())
    assert errors == []


def test_valid_questions_batch():
    errors = validate_player_message(_valid_questions())
    assert errors == []


def test_valid_guess_submission():
    errors = validate_player_message(_valid_guess())
    assert errors == []


# ── Top-level missing fields ────────────────────────────────


def test_missing_message_type():
    msg = _valid_warmup()
    del msg["message_type"]
    errors = validate_player_message(msg)
    assert len(errors) >= 1
    assert any("message_type" in e for e in errors)


def test_missing_sender():
    msg = _valid_warmup()
    del msg["sender"]
    errors = validate_player_message(msg)
    assert len(errors) >= 1


def test_missing_payload():
    msg = _valid_warmup()
    del msg["payload"]
    errors = validate_player_message(msg)
    assert len(errors) >= 1


def test_payload_not_dict():
    msg = _valid_warmup()
    msg["payload"] = "not a dict"
    errors = validate_player_message(msg)
    assert len(errors) >= 1


# ── Payload-specific rules ──────────────────────────────────


def test_warmup_missing_answer():
    msg = _valid_warmup()
    del msg["payload"]["answer"]
    errors = validate_player_message(msg)
    assert len(errors) >= 1
    assert any("answer" in e for e in errors)


def test_questions_missing_questions_field():
    msg = _valid_questions()
    del msg["payload"]["questions"]
    errors = validate_player_message(msg)
    assert len(errors) >= 1
    assert any("questions" in e for e in errors)


def test_questions_not_a_list():
    msg = _valid_questions()
    msg["payload"]["questions"] = "not a list"
    errors = validate_player_message(msg)
    assert len(errors) >= 1
    assert any("questions" in e for e in errors)


def test_guess_empty_payload():
    msg = _valid_guess()
    msg["payload"] = {}
    errors = validate_player_message(msg)
    assert len(errors) >= 1


# ── Sender validation ───────────────────────────────────────


def test_sender_missing_email():
    msg = _valid_warmup()
    msg["sender"] = {"name": "Someone"}
    errors = validate_player_message(msg)
    assert len(errors) >= 1
    assert any("email" in e for e in errors)


# ── Unknown types pass through ───────────────────────────────


def test_unknown_message_type_passes():
    msg = {
        "message_type": "SOME_UNKNOWN_TYPE",
        "sender": {"email": "p1@test.com"},
        "payload": {"anything": "goes"},
    }
    errors = validate_player_message(msg)
    assert errors == []

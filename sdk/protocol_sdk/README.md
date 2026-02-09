# Q21 League Protocol SDK

**Unified Protocol v2 — `league.v2` + `Q21G.v1`**

A Python SDK for validating and processing all messages in the Q21 League Protocol. Feed it any incoming JSON message (as a dict, JSON string, or `.json` file), and it will identify the message type, validate every field against the spec, and return either a clean result or detailed error information.

---

## Files

### `core.py` — Framework Foundation

Everything else depends on this file. It contains:

- **`FieldValidator`** — A class with reusable static validation methods: `required`, `non_empty_string`, `expected_type`, `one_of`, `positive_int`, `non_negative_int`, `number_in_range`, `iso_datetime`, `is_list`, `word_count_range`, `game_id_format`. Each method takes a `ValidationResult` and appends `FieldError` objects when checks fail, so errors accumulate rather than stopping at the first one.
- **`BaseMessage`** (abstract class) — The parent class for every message handler. It validates the §2 envelope structure (protocol, message_type, message_id, timestamp, sender object with email/role/logical_id, recipient_id, required context fields, payload dict). Subclasses implement `validate_payload()` for their specific payload fields and `process_payload()` for business logic.
- **`ValidationResult` / `FieldError` / `SDKError`** — Error types. `FieldError` describes one bad field (name, error type, expected vs received). `ValidationResult` aggregates multiple errors. `SDKError` is raised when validation fails and can serialize to JSON.
- **`EmailSubject`** — Parses and generates email subject lines in the §3 format: `protocol::ROLE::email::transaction_id::MESSAGE_TYPE`.
- **`ErrorResponseBuilder`** — Builds spec-compliant `ERROR_RESPONSE` messages per §8, with standard error codes like `INVALID_MESSAGE`, `UNAUTHORIZED`, `DEADLINE_PASSED`, etc.
- **`MessageRegistry`** — Maps `message_type` strings to their handler classes. The `@register_message` decorator auto-registers each class when its module is imported.
- **`MessageDispatcher`** — Accepts raw input (dict, JSON string, or `.json` file path), looks up the handler in the registry, runs validation + processing, and returns the result.

### `messages_league.py` — League Protocol Handlers (`league.v2`)

Depends on `core.py`. Contains 7 message handler classes, each with `@register_message`:

| Class | Message Type (§) | Direction | Required Context |
|---|---|---|---|
| `BroadcastStartSeason` | `BROADCAST_START_SEASON` (§5.3) | LM → All | `league_id` |
| `SeasonRegistrationRequest` | `SEASON_REGISTRATION_REQUEST` (§5.4) | Player/Referee → LM | `league_id` |
| `SeasonRegistrationResponse` | `SEASON_REGISTRATION_RESPONSE` (§5.5) | LM → Player/Referee | `league_id`, `season_id` |
| `BroadcastAssignmentTable` | `BROADCAST_ASSIGNMENT_TABLE` (§5.6) | LM → All | `league_id`, `season_id` |
| `BroadcastNewLeagueRound` | `BROADCAST_NEW_LEAGUE_ROUND` (§6.1) | LM → All | `league_id`, `season_id` |
| `MatchResultReport` | `MATCH_RESULT_REPORT` (§7.9) | Referee → LM | `league_id`, `season_id`, `round_id`, `game_id` |
| `LeagueCompleted` | `LEAGUE_COMPLETED` (§7.10) | LM → All | `league_id`, `season_id` |

Each class validates its exact payload fields from the spec. For example, `BroadcastAssignmentTable` checks that every assignment object has `role` (one of `player1`/`player2`/`referee`), `email`, `game_id` (7-digit SSRRGGG format), and `group_id`. `SeasonRegistrationResponse` requires a `reason` field when `status` is `"rejected"`.

### `messages_q21.py` — Q21 Game Protocol Handlers (`Q21G.v1`)

Depends on `core.py`. Contains 7 message handler classes for in-game communication:

| Class | Message Type (§) | Direction | Key Validations |
|---|---|---|---|
| `Q21WarmupCall` | `Q21WARMUPCALL` (§7.2) | Referee → Player | `warmup_question`, `deadline` |
| `Q21WarmupResponse` | `Q21WARMUPRESPONSE` (§7.3) | Player → Referee | `answer`, `auth_token` required |
| `Q21RoundStart` | `Q21ROUNDSTART` (§7.4) | Referee → Player | `book_name`, `book_hint`, `association_word`, `questions_required` |
| `Q21QuestionsBatch` | `Q21QUESTIONSBATCH` (§7.5) | Player → Referee | Each question needs `question_number`, `question_text`, `options` with keys A/B/C/D |
| `Q21AnswersBatch` | `Q21ANSWERSBATCH` (§7.6) | Referee → Player | Each answer must be A/B/C/D or "Not Relevant" |
| `Q21GuessSubmission` | `Q21GUESSSUBMISSION` (§7.7) | Player → Referee | `sentence_justification` 30–50 words, `word_justification` 20–30 words, `confidence` 0.0–1.0 |
| `Q21ScoreFeedback` | `Q21SCOREFEEDBACK` (§7.8) | Referee → Player | `league_points` 0–3, `private_score` 0–100, `breakdown` with 4 component scores |

All Q21 messages require `game_id` in the envelope and use protocol `"Q21G.v1"`.

### `sdk.py` — Public API Entry Point

Depends on `core.py`, `messages_league.py`, `messages_q21.py`. Importing this module triggers all `@register_message` decorators, populating the registry with all 14 handlers. Exposes:

| Function | Purpose |
|---|---|
| `process_message(input)` | Main dispatcher — accepts dict, JSON string, or `.json` file path. Returns success or error dict. |
| `list_supported_messages()` | All 14 registered `message_type` strings |
| `list_league_messages()` | The 7 `league.v2` types |
| `list_q21_messages()` | The 7 `Q21G.v1` types |
| `get_message_info()` | Metadata (class name, protocol, direction, required context) for each handler |
| `build_error_response(...)` | Create a spec-compliant `ERROR_RESPONSE` message (§8) |
| `parse_email_subject(subject)` | Parse a `protocol::ROLE::email::tx_id::MSG_TYPE` subject string |
| `generate_email_subject(msg)` | Generate the email subject from a message dict |

Also works as a CLI: `python sdk.py message.json`

### `test_demo.py` — Test Suite

Depends on `sdk.py`. Runs 39 tests covering every message type with valid inputs (using exact JSON examples from the spec) and invalid inputs (missing fields, wrong enum values, out-of-range numbers, bad formats, wrong protocols). Also tests email subject parsing, error response building, and file-based dispatch.

Run with: `python test_demo.py`

---

## Dependency Chain

```
core.py
  ├── messages_league.py   (7 league.v2 handlers)
  ├── messages_q21.py      (7 Q21G.v1 handlers)
  │
  └── sdk.py               (imports both, exposes public API)
        │
        └── test_demo.py   (validates everything)
```

---

## How to Use

### Installation

No external dependencies — pure Python 3.10+ standard library. Just place all `.py` files in the same directory.

### Basic Usage: Processing Incoming Messages

```python
from sdk import process_message

# From a dict (e.g., parsed from an email body):
result = process_message({
    "protocol": "Q21G.v1",
    "message_type": "Q21WARMUPCALL",
    "message_id": "warmup-r1m1-p001",
    "timestamp": "2026-02-17T19:00:00.000000+00:00",
    "sender": {
        "email": "referee@example.com",
        "role": "REFEREE",
        "logical_id": "R001"
    },
    "recipient_id": "P001",
    "game_id": "0101001",
    "payload": {
        "match_id": "R1M1",
        "warmup_question": "What is 2 + 2?",
        "deadline": "2026-02-17T19:02:00.000000+00:00",
        "auth_token": "tok_abc123"
    }
})

# From a .json file:
result = process_message("/path/to/message.json")

# From a raw JSON string:
result = process_message('{"protocol": "Q21G.v1", ...}')
```

### Checking the Result

```python
if result["status"] == "success":
    msg_type = result["message_type"]       # e.g. "Q21WARMUPCALL"
    protocol = result["protocol"]           # e.g. "Q21G.v1"
    subject  = result["email_subject"]      # generated email subject line
    payload  = result["processed_payload"]  # validated payload data

    # Route to your handler based on message type:
    if msg_type == "Q21WARMUPCALL":
        answer = solve(payload["warmup_question"])
        send_response(answer, payload["auth_token"])

    elif msg_type == "Q21ROUNDSTART":
        questions = generate_questions(
            payload["book_name"],
            payload["book_hint"],
            payload["association_word"]
        )
        send_questions(questions)

    elif msg_type == "BROADCAST_NEW_LEAGUE_ROUND":
        prepare_for_round(payload["round_number"])

else:
    # Validation failed — inspect errors
    for err in result["validation"]["errors"]:
        print(f"  Field: {err['field']}")
        print(f"  Error: {err['error_type']}")
        print(f"  Expected: {err.get('expected')}")
        print(f"  Got: {err.get('received')}")
```

### Using Email Subject Utilities

```python
from sdk import parse_email_subject, generate_email_subject

# Parse an incoming email subject to quickly identify message type:
info = parse_email_subject(
    "Q21G.v1::REFEREE::ref@example.com::warmup-r1m1-p001::Q21WARMUPCALL"
)
# Returns: {
#   "protocol": "Q21G.v1",
#   "role": "REFEREE",
#   "email": "ref@example.com",
#   "transaction_id": "warmup-r1m1-p001",
#   "message_type": "Q21WARMUPCALL"
# }

# Generate the subject line for an outgoing message:
subject = generate_email_subject(my_outgoing_message_dict)
```

### Building Error Responses

```python
from sdk import build_error_response

error_msg = build_error_response(
    error_code="DEADLINE_PASSED",
    error_message="Registration window has closed",
    original_message_type="SEASON_REGISTRATION_REQUEST",
    recoverable=True,
    sender_email="server@example.com",
    recipient_id="P001",
    correlation_id="sreg-player-def456"
)
# Returns a complete ERROR_RESPONSE envelope ready to send
```

### Running Tests

```bash
python test_demo.py
```

Expected output: `39/39 passed, 0 failed`

### CLI Usage

```bash
# Process a message file:
python sdk.py message.json

# List all supported message types:
python sdk.py
```

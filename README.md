# Q21 Referee SDK

Version: 2.0.0

A Python SDK for implementing Q21 League referee AI. Students implement 4 callback methods to create their referee logic.

## Getting Started

### Step 1: Clone and Install

```bash
git clone https://github.com/OmryTzabbar1/q21-referee-sdk.git
cd q21-referee-sdk
pip install -e .
```

### Step 2: Set Up OAuth Credentials

You need OAuth credentials from Google Cloud Console (no App Password needed):

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Gmail API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Select "Desktop app"
   - Download the JSON file as `credentials.json`
5. Place `credentials.json` in your project folder

### Step 3: Configure Settings

Run the setup script to generate `config.json` and `.env` files:

```bash
python setup_config.py
```

The script will prompt you for:
- Path to credentials.json (default: `credentials.json`)
- Referee ID and Group ID
- League Manager email

<details>
<summary>Manual configuration (alternative)</summary>

Create `config.json` manually:

```json
{
    "credentials_path": "credentials.json",
    "token_path": "token.json",
    "referee_id": "REF001",
    "group_id": "GROUP_01",
    "league_manager_email": "league.manager@example.com"
}
```

</details>

### Step 4: Run in Demo Mode

Test your setup immediately with the `--demo` argument (no code required):

```bash
python -m q21_referee --demo --config config.json
```

On first run, a browser will open for OAuth consent. After you approve:
- `token.json` is created automatically
- Future runs won't need browser authorization

This runs the referee using `DemoAI`, which provides pre-written responses from `demo_data/`. Use demo mode to:
- Verify your setup works before writing any code
- Understand the game flow
- Test email connectivity

### Step 5: Implement Your AI

Once demo mode works, implement your own referee logic (see [Custom Implementation](#custom-implementation) below).

---

## Demo Mode

Demo mode lets you run the referee without implementing any callbacks.

**Three ways to enable demo mode:**

| Method | How to Use |
|--------|------------|
| Command line argument | `python -m q21_referee --demo --config config.json` |
| Config file | Add `"demo_mode": true` to your config.json |
| Environment variable | `DEMO_MODE=true python -m q21_referee --config config.json` |

**All command line arguments:**

| Argument | Description |
|----------|-------------|
| `--demo` | Enable demo mode (use DemoAI) |
| `--config FILE` | Path to JSON config file |
| `--single-game` | Use RefereeRunner instead of RLGMRunner |
| `--demo-path PATH` | Custom path to demo data files |

**Using DemoAI in Python code:**

```python
from q21_referee import DemoAI, RLGMRunner

runner = RLGMRunner(config=config, ai=DemoAI())
runner.run()
```

---

## Custom Implementation

Once ready to implement your own AI:

```python
from q21_referee import RefereeAI, RLGMRunner

class MyRefereeAI(RefereeAI):
    """Your referee implementation."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is the capital of France?"}

    def get_round_start_info(self, ctx):
        return {
            "book_name": "The Great Gatsby",
            "book_hint": "A novel about the American Dream in the 1920s",
            "association_word": "green"
        }

    def get_answers(self, ctx):
        questions = ctx.get("questions", [])
        return {
            "answers": [
                {"question_number": q["question_number"], "answer": "B"}
                for q in questions
            ]
        }

    def get_score_feedback(self, ctx):
        return {
            "league_points": 2,
            "private_score": 75.0,
            "breakdown": {
                "opening_sentence_score": 80.0,
                "sentence_justification_score": 70.0,
                "associative_word_score": 60.0,
                "word_justification_score": 90.0
            },
            "feedback": {
                "opening_sentence": "Good attempt!",
                "associative_word": "Close, but not quite."
            }
        }

if __name__ == "__main__":
    config = {
        "credentials_path": "credentials.json",
        "token_path": "token.json",
        "referee_id": "REF001",
        "group_id": "GROUP_01",
        "display_name": "My Referee Bot",
        "league_manager_email": "league.manager@example.com",
        "poll_interval_seconds": 5,
    }
    runner = RLGMRunner(config=config, ai=MyRefereeAI())
    runner.run()
```

## Two Operating Modes

### Season Mode (RLGMRunner) - For League Play

Use `RLGMRunner` for full season integration with the League Manager:

```python
from q21_referee import RLGMRunner

runner = RLGMRunner(config=config, ai=MyRefereeAI())
runner.run()
```

**Season lifecycle:**
1. Receives `BROADCAST_START_SEASON` from League Manager
2. Sends `SEASON_REGISTRATION_REQUEST` to register
3. Receives `BROADCAST_ASSIGNMENT_TABLE` with game assignments
4. For each round: receives `BROADCAST_NEW_LEAGUE_ROUND`, runs games, reports results
5. Season ends with `LEAGUE_COMPLETED`

### Single-Game Mode (RefereeRunner) - For Testing

Use `RefereeRunner` for testing a single game without League Manager:

```python
from q21_referee import RefereeRunner

config = {
    "credentials_path": "credentials.json",
    "token_path": "token.json",
    "referee_id": "REF001",
    "game_id": "0101001",
    "match_id": "TEST_MATCH",
    "player1_email": "player1@example.com",
    "player1_id": "P001",
    "player2_email": "player2@example.com",
    "player2_id": "P002",
}
runner = RefereeRunner(config=config, ai=MyRefereeAI())
runner.run()
```

## Configuration

### OAuth Settings

| Key | Required | Description |
|-----|----------|-------------|
| `credentials_path` | No | Path to OAuth credentials.json (default: `credentials.json` or `GMAIL_CREDENTIALS_PATH` env var) |
| `token_path` | No | Path to store token.json (default: `token.json` or `GMAIL_TOKEN_PATH` env var) |

### Season Mode (RLGMRunner)

| Key | Required | Description |
|-----|----------|-------------|
| `referee_id` | Yes | Your assigned referee ID (e.g., "REF001") |
| `group_id` | Yes | Your group ID from league registration |
| `display_name` | No | Display name (default: "Q21 Referee") |
| `league_manager_email` | Yes | League Manager email |
| `poll_interval_seconds` | No | Email polling interval (default: 5) |

### Single-Game Mode (RefereeRunner)

| Key | Required | Description |
|-----|----------|-------------|
| `referee_id` | Yes | Your assigned referee ID |
| `game_id` | Yes | Game ID (e.g., "0101001") |
| `match_id` | Yes | Match ID |
| `player1_email` | Yes | Player 1 email |
| `player1_id` | Yes | Player 1 ID |
| `player2_email` | Yes | Player 2 email |
| `player2_id` | Yes | Player 2 ID |

## RefereeAI Interface

Implement these 4 methods:

### 1. `get_warmup_question(ctx) -> dict`

Called at round start to verify player connectivity.

```python
def get_warmup_question(self, ctx):
    return {"warmup_question": "What is 2 + 2?"}
```

### 2. `get_round_start_info(ctx) -> dict`

Called after both players respond to warmup. Provide book info.

```python
def get_round_start_info(self, ctx):
    return {
        "book_name": "The Great Gatsby",
        "book_hint": "A novel about the American Dream in the 1920s Jazz Age",
        "association_word": "green"
    }
```

### 3. `get_answers(ctx) -> dict`

Called when a player submits 20 questions. Answer each one.

```python
def get_answers(self, ctx):
    return {
        "answers": [
            {"question_number": 1, "answer": "A"},
            {"question_number": 2, "answer": "Not Relevant"},
            # ... for all 20 questions
        ]
    }
```

Valid answers: `"A"`, `"B"`, `"C"`, `"D"`, or `"Not Relevant"`

### 4. `get_score_feedback(ctx) -> dict`

Called when a player submits their final guess. Score it.

```python
def get_score_feedback(self, ctx):
    return {
        "league_points": 3,      # 0-3
        "private_score": 85.5,   # 0-100
        "breakdown": {
            "opening_sentence_score": 90.0,
            "sentence_justification_score": 80.0,
            "associative_word_score": 100.0,
            "word_justification_score": 70.0
        },
        "feedback": {
            "opening_sentence": "Excellent match!",
            "associative_word": "Perfect!"
        }
    }
```

## Scoring Guide

**League Points (0-3):**
- 3 points: Winner
- 1 point: Draw
- 0 points: Loser

**Private Score (0-100) - Weighted average:**
- Opening sentence match: 50%
- Sentence justification: 20%
- Associative word match: 20%
- Word justification: 10%

## Environment Setup

Create a `.env` file (or use `python setup_config.py`):

```bash
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
REFEREE_ID=REF001
GROUP_ID=GROUP_01
LEAGUE_MANAGER_EMAIL=league.manager@example.com
```

## Protocol Compliance

This SDK implements the UNIFIED_PROTOCOL.md specification:
- Season registration (§5.3-5.5)
- Assignment handling (§5.6)
- Q21 game flow (§7.1-7.8)
- Match result reporting (§7.9)

## License

MIT License

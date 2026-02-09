# Q21 Referee SDK

Version: 1.0.0

A Python SDK for implementing Q21 League referee AI. Students implement 4 callback methods to create their referee logic.

## Installation

```bash
# Basic installation
pip install git+https://github.com/OmryTzabbar1/q21-referee-sdk.git

# With LLM support (for AI-powered implementations)
pip install "git+https://github.com/OmryTzabbar1/q21-referee-sdk.git#egg=q21-referee[llm]"

# With Gmail support (for email-based communication)
pip install "git+https://github.com/OmryTzabbar1/q21-referee-sdk.git#egg=q21-referee[gmail]"

# Full installation (all features)
pip install "git+https://github.com/OmryTzabbar1/q21-referee-sdk.git#egg=q21-referee[all]"
```

## Quick Start

```python
from q21_referee import RefereeAI, RefereeRunner

class MyRefereeAI(RefereeAI):
    """Your referee implementation."""

    def get_warmup_question(self, ctx):
        """Generate a warmup question for players."""
        return {"warmup_question": "What is the capital of France?"}

    def get_round_start_info(self, ctx):
        """Provide book information for the round."""
        return {
            "book_name": "The Great Gatsby",
            "book_hint": "A novel about the American Dream in the 1920s",
            "association_word": "green"
        }

    def get_answers(self, ctx):
        """Answer player questions about the book."""
        questions = ctx.get("questions", [])
        answers = []
        for q in questions:
            # Your logic to answer each question
            answers.append({
                "question_number": q["question_number"],
                "answer": "B"  # A, B, C, D, or "Not Relevant"
            })
        return {"answers": answers}

    def get_score_feedback(self, ctx):
        """Score the player's guess."""
        return {
            "league_points": 2,  # 0-3
            "private_score": 75.0,  # 0-100
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

# Run the referee
if __name__ == "__main__":
    config = {
        "referee_email": "your.referee@gmail.com",
        "league_manager_email": "league.manager@gmail.com",
        "referee_id": "R001",
        "poll_interval_seconds": 30,
    }
    runner = RefereeRunner(config=config, ai=MyRefereeAI())
    runner.run()
```

## RefereeAI Interface

You must implement these 4 methods:

### 1. `get_warmup_question(ctx) -> dict`

**When called:** At the start of each round, after receiving `BROADCAST_NEW_LEAGUE_ROUND`.

**Input context:**
```python
{
    "round_number": 1,
    "round_id": "ROUND_1",
    "game_id": "0101001",
    "players": [
        {"email": "player1@example.com", "participant_id": "P001"},
        {"email": "player2@example.com", "participant_id": "P002"}
    ]
}
```

**Expected return:**
```python
{"warmup_question": "What is 2 + 2?"}
```

### 2. `get_round_start_info(ctx) -> dict`

**When called:** After both players respond to warmup.

**Input context:**
```python
{
    "round_number": 1,
    "game_id": "0101001",
    "match_id": "SEASON_0101001",
    "player1": {"email": "...", "participant_id": "P001", "warmup_answer": "4"},
    "player2": {"email": "...", "participant_id": "P002", "warmup_answer": "4"}
}
```

**Expected return:**
```python
{
    "book_name": "The Great Gatsby",
    "book_hint": "A novel about the American Dream in the 1920s Jazz Age",
    "association_word": "green"
}
```

### 3. `get_answers(ctx) -> dict`

**When called:** When a player submits their 20 questions.

**Input context:**
```python
{
    "match_id": "SEASON_0101001",
    "game_id": "0101001",
    "player_email": "player1@example.com",
    "player_id": "P001",
    "book_name": "The Great Gatsby",
    "book_hint": "A novel about the American Dream...",
    "association_word": "green",
    "questions": [
        {
            "question_number": 1,
            "question_text": "Is this book set in America?",
            "options": {"A": "Yes", "B": "No", "C": "Partially", "D": "Unknown"}
        },
        # ... 20 questions total
    ]
}
```

**Expected return:**
```python
{
    "answers": [
        {"question_number": 1, "answer": "A"},
        {"question_number": 2, "answer": "B"},
        # ... answers for all questions
        # Valid answers: "A", "B", "C", "D", or "Not Relevant"
    ]
}
```

### 4. `get_score_feedback(ctx) -> dict`

**When called:** When a player submits their final guess.

**Input context:**
```python
{
    "match_id": "SEASON_0101001",
    "game_id": "0101001",
    "player_email": "player1@example.com",
    "player_id": "P001",
    "book_name": "The Great Gatsby",
    "book_hint": "A novel about the American Dream...",
    "association_word": "green",
    "opening_sentence": "In my younger and more vulnerable years...",
    "sentence_justification": "Based on the questions about America and wealth...",
    "associative_word": "green",
    "word_justification": "The green light is a central symbol...",
    "confidence": 0.85
}
```

**Expected return:**
```python
{
    "league_points": 3,  # 0, 1, 2, or 3
    "private_score": 85.5,  # 0.0 to 100.0
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

## Using the LLM SDK (Optional)

For AI-powered implementations, use the included LLM SDK:

```python
from sdk.llm_sdk import (
    get_warmup_question,
    get_round_start_info,
    get_answers,
    get_score_feedback,
    configure
)

# Configure for demo mode (no API key needed)
configure(mode="demo", demo_path="./demo_data")

# Or configure for LLM mode
configure(mode="llm")  # Requires ANTHROPIC_API_KEY env var

# Use in your RefereeAI implementation
class MyRefereeAI(RefereeAI):
    def get_warmup_question(self, ctx):
        return get_warmup_question()

    def get_answers(self, ctx):
        return get_answers(
            questions=ctx["questions"],
            book_name=ctx["book_name"]
        )
```

## Configuration

Create a `.env` file with:

```bash
# Gmail Configuration
GMAIL_ACCOUNT=your.referee@gmail.com
GMAIL_CREDENTIALS_PATH=./credentials.json

# League Configuration
LEAGUE_MANAGER_EMAIL=league.manager@gmail.com
REFEREE_ID=R001

# Optional: For LLM-powered implementations
ANTHROPIC_API_KEY=your_api_key_here
```

## Examples

See the `examples/` directory for complete implementations:
- `my_ai.py` - Hardcoded responses (for testing)
- `sdk_ai.py` - LLM SDK-based implementation
- `main.py` - Entry point template
- `test_local.py` - Local testing without email

## Scoring Guide

**League Points (0-3):**
- 3 points: private_score >= 80
- 2 points: private_score >= 60
- 1 point: private_score >= 40
- 0 points: private_score < 40

**Private Score (0-100):**
Weighted average of:
- Opening sentence match: 40%
- Sentence justification quality: 10%
- Associative word match: 40%
- Word justification quality: 10%

## Troubleshooting

**Import errors:**
```bash
pip install --upgrade q21-referee
```

**Gmail authentication:**
1. Create OAuth credentials in Google Cloud Console
2. Download as `credentials.json`
3. Set `GMAIL_CREDENTIALS_PATH` in `.env`

**LLM SDK not working:**
```bash
pip install "q21-referee[llm]"
export ANTHROPIC_API_KEY=your_key
```

## License

MIT License - See LICENSE file for details.

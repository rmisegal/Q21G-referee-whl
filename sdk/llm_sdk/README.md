# Q21 LLM SDK

**Generate Q21 game content using LLM or demo files.**

This SDK provides four generators for creating Q21 game message payloads:

| Generator | Output Message | Description |
|-----------|----------------|-------------|
| `get_warmup_question()` | Q21WARMUPCALL | Warmup question text |
| `get_round_start_info()` | Q21ROUNDSTART | Book name, hint, association word |
| `get_answers()` | Q21ANSWERSBATCH | Answer key for player questions |
| `get_score_feedback()` | Q21SCOREFEEDBACK | Scores and feedback for player guess |

---

## Files

### `core.py` — Framework Foundation

- **`BaseLLMClient`** — Abstract base for LLM clients
- **`AnthropicClient`** — Anthropic Claude API client
- **`MockLLMClient`** — Mock client for testing
- **`ScoreCalculator`** — Calculates Q21 scores based on guess similarity
- **`FieldValidator`** — Reusable validation methods
- **`ValidationResult` / `FieldError` / `SDKError`** — Error types
- **Output validators** — `validate_warmup_question()`, `validate_round_start_info()`, etc.

### `generators.py` — Generator Classes

| Class | Generator Type | Demo File |
|-------|----------------|-----------|
| `WarmupQuestionGenerator` | warmup_question | Q21_WARMUP_CALL.REFEREE_step0_WarmupQuestion.md |
| `RoundStartInfoGenerator` | round_start_info | Q21_ROUND_START.REFEREE_step1_game_setup.md |
| `AnswersGenerator` | answers | Q21_ANSWERS_BATCH.REFEREE_step3_answers.md |
| `ScoreFeedbackGenerator` | score_feedback | Q21_SCORE_FEEDBACK.08_player_A_result.md |

Each generator supports:
- **LLM mode**: Uses Anthropic Claude API with prompts
- **Demo mode**: Reads from markdown files
- **Fallback mode**: Returns sensible defaults

### `sdk.py` — Public API Entry Point

Exposes:
- `get_warmup_question()` — Generate warmup question
- `get_round_start_info()` — Generate round start info
- `get_answers()` — Generate answer key
- `get_score_feedback()` — Generate scores and feedback
- `calculate_scores()` — Direct score calculation
- `determine_winner()` — Determine match winner
- `configure()` — SDK configuration
- `list_generators()` — List available generators

---

## Dependency Chain

```
core.py
  ├── generators.py   (4 generator classes)
  │
  └── sdk.py          (public API)
```

---

## How to Use

### Installation

No external dependencies for core functionality. For LLM mode:

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

### Basic Usage

```python
from sdk import (
    get_warmup_question,
    get_round_start_info,
    get_answers,
    get_score_feedback,
    configure,
)

# Optional: Configure SDK
configure(
    mode="auto",  # "auto", "llm", or "demo"
    demo_path="path/to/demo/files",
)

# Generate warmup question
warmup = get_warmup_question()
print(warmup["warmup_question"])
# "What is 2 + 2?"

# Generate round start info
round_info = get_round_start_info()
print(round_info)
# {
#     "book_name": "The Great Gatsby",
#     "book_hint": "A tale of wealth and obsession in 1920s New York",
#     "association_word": "color"
# }

# Generate answers for player questions
answers = get_answers(
    questions=[
        {
            "question_number": 1,
            "question_text": "Is the book fiction?",
            "options": {"A": "Yes", "B": "No", "C": "Partially", "D": "Unknown"}
        }
    ],
    book_name="Moby Dick",
    actual_opening_sentence="Call me Ishmael.",
    actual_associative_word="whale",
)
print(answers["answers"])
# [{"question_number": 1, "answer": "A"}, ...]

# Calculate scores for player guess
scores = get_score_feedback(
    actual_opening_sentence="Call me Ishmael.",
    actual_associative_word="whale",
    opening_sentence_guess="Call me Ishmael.",
    sentence_justification="The maritime theme and first-person narrative strongly suggest this classic opening from a famous seafaring novel.",
    associative_word_guess="whale",
    word_justification="The hunting theme and oceanic setting clearly point to this creature.",
)
print(scores)
# {
#     "league_points": 3,
#     "private_score": 95.0,
#     "breakdown": {
#         "opening_sentence_score": 100.0,
#         "sentence_justification_score": 75.0,
#         "associative_word_score": 100.0,
#         "word_justification_score": 70.0
#     },
#     "feedback": {
#         "opening_sentence": "Excellent match with the actual opening!",
#         "associative_word": "Correct!"
#     }
# }
```

### Using Demo Mode

```python
from sdk import configure, get_warmup_question

# Point to your demo markdown files
configure(
    mode="demo",
    demo_path="AIAgentConversationDemo/Q21G_QA_FLOW",
)

warmup = get_warmup_question()
# Reads from Q21_WARMUP_CALL.REFEREE_step0_WarmupQuestion.md
```

### Direct Score Calculation

```python
from sdk import calculate_scores, determine_winner

# Calculate scores without LLM/demo
scores = calculate_scores(
    actual_opening_sentence="It was the best of times.",
    actual_associative_word="revolution",
    opening_sentence_guess="It was the best of times.",
    sentence_justification="The contrasting themes suggest this famous opening.",
    associative_word_guess="france",
    word_justification="The setting in Paris indicates this country.",
)

print(scores["private_score"])  # 0-100
print(scores["league_points"])  # 0-3

# Determine winner
result = determine_winner(
    player_a_private_score=75.0,
    player_b_private_score=62.0,
)
print(result)  # {"winner": "A", "is_draw": False}
```

### CLI Usage

```bash
# Generate warmup question
python sdk.py warmup

# Generate round start info
python sdk.py round-start

# Generate default answers
python sdk.py answers

# Calculate example scores
python sdk.py score

# List generators
python sdk.py list

# Use demo mode
python sdk.py warmup --mode demo --demo-path ./demo_files
```

---

## Scoring Details

### Score Components

| Component | Weight | Range |
|-----------|--------|-------|
| Opening sentence similarity | 50% | 0-100 |
| Sentence justification quality | 20% | 0-100 |
| Associative word match | 20% | 0 or 100 |
| Word justification quality | 10% | 0-100 |

### League Points Conversion

| Private Score | League Points |
|---------------|---------------|
| 85-100 | 3 |
| 70-84 | 2 |
| 50-69 | 1 |
| 0-49 | 0 |

### Justification Scoring

- Based on word count and reasoning keywords
- Sentence justification: 30-50 words expected
- Word justification: 20-30 words expected
- Penalty (5%) applied if under minimum word count
- Bonus for keywords: "because", "therefore", "evidence", etc.

---

## Error Handling

```python
from sdk import get_warmup_question, SDKError

try:
    result = get_warmup_question()
except SDKError as e:
    print(e.generator_type)  # "warmup_question"
    print(e.message)         # "Validation failed"
    print(e.validation.to_dict())  # {"is_valid": False, "errors": [...]}
```

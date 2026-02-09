"""
Q21 LLM SDK — Core Framework
=============================
Provides LLM abstraction for generating Q21 game content.

Supports two modes:
  - LLM mode: Uses Anthropic Claude API
  - Demo mode: Reads from markdown files

Four generators:
  1. get_warmup_question()   → warmup question for Q21WARMUPCALL
  2. get_round_start_info()  → book info for Q21ROUNDSTART
  3. get_answers()           → answer key for Q21ANSWERSBATCH
  4. get_score_feedback()    → scores for Q21SCOREFEEDBACK
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
# 1. ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════

class GeneratorMode(Enum):
    LLM = "llm"
    DEMO = "demo"


class GeneratorType(Enum):
    WARMUP_QUESTION = "warmup_question"
    ROUND_START_INFO = "round_start_info"
    ANSWERS = "answers"
    SCORE_FEEDBACK = "score_feedback"


# Scoring weights per Q21 spec
SENTENCE_WEIGHT = 0.50
SENTENCE_REASONING_WEIGHT = 0.20
WORD_WEIGHT = 0.20
WORD_REASONING_WEIGHT = 0.10

# Word count limits for justifications
SENTENCE_JUST_MIN_WORDS = 30
SENTENCE_JUST_MAX_WORDS = 50
WORD_JUST_MIN_WORDS = 20
WORD_JUST_MAX_WORDS = 30

# Default LLM settings
DEFAULT_MODEL = "claude-3-haiku-20240307"
DEFAULT_MAX_TOKENS = 1000


# ═══════════════════════════════════════════════════════════════════
# 2. ERROR / VALIDATION TYPES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FieldError:
    """Single field-level validation failure."""
    field_name: str
    error_type: str
    expected: Optional[str] = None
    received: Optional[Any] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"field": self.field_name, "error_type": self.error_type}
        if self.expected:
            d["expected"] = self.expected
        if self.received is not None:
            d["received"] = str(self.received)
        if self.message:
            d["message"] = self.message
        return d


@dataclass
class ValidationResult:
    """Aggregated validation result."""
    is_valid: bool = True
    errors: List[FieldError] = field(default_factory=list)

    def add_error(self, err: FieldError):
        self.is_valid = False
        self.errors.append(err)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
        }


class SDKError(Exception):
    """Raised when generation or validation fails."""
    def __init__(self, generator_type: str, message: str, validation: Optional[ValidationResult] = None):
        self.generator_type = generator_type
        self.message = message
        self.validation = validation
        super().__init__(f"[{generator_type}] {message}")

    def to_dict(self) -> dict:
        result = {
            "status": "error",
            "generator_type": self.generator_type,
            "message": self.message,
        }
        if self.validation:
            result["validation"] = self.validation.to_dict()
        return result


# ═══════════════════════════════════════════════════════════════════
# 3. FIELD VALIDATORS
# ═══════════════════════════════════════════════════════════════════

class FieldValidator:
    """Static, composable field-check methods."""

    @staticmethod
    def required(data: dict, field_name: str, result: ValidationResult) -> Any:
        if field_name not in data or data[field_name] is None:
            result.add_error(FieldError(field_name, "missing",
                                        message=f"'{field_name}' is required"))
            return None
        return data[field_name]

    @staticmethod
    def non_empty_string(value: Any, field_name: str, result: ValidationResult) -> bool:
        if value is None:
            return False
        if not isinstance(value, str) or len(value.strip()) == 0:
            result.add_error(FieldError(field_name, "invalid_value",
                                        expected="non-empty string",
                                        received=value))
            return False
        return True

    @staticmethod
    def positive_int(value: Any, field_name: str, result: ValidationResult) -> bool:
        if value is None:
            return False
        if not isinstance(value, int) or value <= 0:
            result.add_error(FieldError(field_name, "out_of_range",
                                        expected="positive integer",
                                        received=value))
            return False
        return True

    @staticmethod
    def number_in_range(value: Any, field_name: str, min_val: float, max_val: float,
                        result: ValidationResult) -> bool:
        if value is None:
            return False
        if not isinstance(value, (int, float)):
            result.add_error(FieldError(field_name, "invalid_type",
                                        expected="number",
                                        received=type(value).__name__))
            return False
        if value < min_val or value > max_val:
            result.add_error(FieldError(field_name, "out_of_range",
                                        expected=f"{min_val}–{max_val}",
                                        received=value))
            return False
        return True

    @staticmethod
    def is_list(value: Any, field_name: str, result: ValidationResult,
                min_length: int = 0) -> bool:
        if value is None:
            return False
        if not isinstance(value, list):
            result.add_error(FieldError(field_name, "invalid_type",
                                        expected="array",
                                        received=type(value).__name__))
            return False
        if len(value) < min_length:
            result.add_error(FieldError(field_name, "out_of_range",
                                        expected=f"min length {min_length}",
                                        received=len(value)))
            return False
        return True

    @staticmethod
    def one_of(value: Any, field_name: str, choices: list, result: ValidationResult) -> bool:
        if value is None:
            return False
        if value not in choices:
            result.add_error(FieldError(field_name, "invalid_value",
                                        expected=f"one of {choices}",
                                        received=value))
            return False
        return True


# ═══════════════════════════════════════════════════════════════════
# 4. LLM CLIENT ABSTRACTION
# ═══════════════════════════════════════════════════════════════════

class BaseLLMClient(ABC):
    """Abstract base for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text from prompt. Returns empty string on error."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if client is properly configured."""
        ...


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from anthropic import Anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self._client = Anthropic()
        except ImportError:
            pass

    def is_available(self) -> bool:
        return self._client is not None

    def generate(self, prompt: str) -> str:
        if not self._client:
            return ""
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""
        except Exception:
            return ""


class MockLLMClient(BaseLLMClient):
    """Mock client for testing."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self._responses = responses or {}

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str) -> str:
        # Return pre-configured response or empty string
        for key, response in self._responses.items():
            if key in prompt:
                return response
        return ""


# ═══════════════════════════════════════════════════════════════════
# 5. SCORE CALCULATOR
# ═══════════════════════════════════════════════════════════════════

REASONING_KEYWORDS = [
    "because", "therefore", "based on", "indicates",
    "suggests", "deduced", "concluded", "reasoning",
    "evidence", "pattern", "contrast", "theme"
]


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def evaluate_justification_quality(text: str) -> float:
    """Evaluate justification text quality. Returns 0-100."""
    if not text:
        return 0.0

    words = text.split()
    length_score = min(len(words) / 20, 1.0) * 50

    keyword_bonus = 0
    text_lower = text.lower()
    for keyword in REASONING_KEYWORDS:
        if keyword in text_lower:
            keyword_bonus += 5

    return min(100.0, length_score + keyword_bonus)


def evaluate_sentence_justification(text: str) -> Tuple[float, bool]:
    """Evaluate sentence justification. Returns (score, was_penalized)."""
    word_count = count_words(text)
    was_penalized = False

    eval_text = text
    if word_count > SENTENCE_JUST_MAX_WORDS:
        eval_text = " ".join(text.split()[:SENTENCE_JUST_MAX_WORDS])

    base_score = evaluate_justification_quality(eval_text)

    if word_count < SENTENCE_JUST_MIN_WORDS:
        base_score *= 0.95
        was_penalized = True

    return round(base_score, 2), was_penalized


def evaluate_word_justification(text: str) -> Tuple[float, bool]:
    """Evaluate word justification. Returns (score, was_penalized)."""
    word_count = count_words(text)
    was_penalized = False

    eval_text = text
    if word_count > WORD_JUST_MAX_WORDS:
        eval_text = " ".join(text.split()[:WORD_JUST_MAX_WORDS])

    base_score = evaluate_justification_quality(eval_text)

    if word_count < WORD_JUST_MIN_WORDS:
        base_score *= 0.95
        was_penalized = True

    return round(base_score, 2), was_penalized


class ScoreCalculator:
    """Calculates Q21 game scores."""

    def calculate_similarity(self, actual: str, guessed: str) -> float:
        """Calculate similarity score between actual and guessed sentences. Returns 0-100."""
        if not actual or not guessed:
            return 0.0

        actual_lower = actual.lower()
        guessed_lower = guessed.lower()

        if actual_lower == guessed_lower:
            return 100.0

        actual_words = set(actual_lower.split())
        guessed_words = set(guessed_lower.split())

        if not actual_words:
            return 0.0

        intersection = actual_words & guessed_words
        union = actual_words | guessed_words

        if not union:
            return 0.0

        jaccard = len(intersection) / len(union)

        sequence_bonus = 0.0
        for i in range(min(len(guessed_lower), len(actual_lower))):
            if guessed_lower[i] == actual_lower[i]:
                sequence_bonus += 1
        sequence_ratio = sequence_bonus / max(len(actual_lower), 1)

        score = (jaccard * 70 + sequence_ratio * 30)
        return round(min(100.0, score), 2)

    def calculate_word_score(self, actual: str, guessed: str) -> float:
        """Calculate score for word guess. Returns 0 or 100."""
        if not actual or not guessed:
            return 0.0
        if actual.upper() == guessed.upper():
            return 100.0
        return 0.0

    def calculate_player_scores(
        self,
        actual_sentence: str,
        actual_word: str,
        opening_sentence_guess: str,
        sentence_justification: str,
        associative_word_guess: str,
        word_justification: str,
    ) -> Dict[str, Any]:
        """Calculate all scores for a player's guess."""
        sentence_score = self.calculate_similarity(actual_sentence, opening_sentence_guess)
        sentence_just_score, _ = evaluate_sentence_justification(sentence_justification)
        word_score = self.calculate_word_score(actual_word, associative_word_guess)
        word_just_score, _ = evaluate_word_justification(word_justification)

        private_score = (
            sentence_score * SENTENCE_WEIGHT
            + sentence_just_score * SENTENCE_REASONING_WEIGHT
            + word_score * WORD_WEIGHT
            + word_just_score * WORD_REASONING_WEIGHT
        )
        private_score = round(private_score, 2)
        league_points = self._calculate_league_points(private_score)

        return {
            "opening_sentence_score": sentence_score,
            "sentence_justification_score": sentence_just_score,
            "associative_word_score": word_score,
            "word_justification_score": word_just_score,
            "private_score": private_score,
            "league_points": league_points,
        }

    def _calculate_league_points(self, private_score: float) -> int:
        """Convert private score (0-100) to league points (0-3)."""
        if private_score >= 85:
            return 3
        elif private_score >= 70:
            return 2
        elif private_score >= 50:
            return 1
        return 0

    def determine_winner(
        self,
        player_a_private_score: float,
        player_b_private_score: float,
    ) -> Dict[str, Any]:
        """Determine the winner based on private scores."""
        if player_a_private_score > player_b_private_score:
            return {"winner": "A", "is_draw": False}
        elif player_b_private_score > player_a_private_score:
            return {"winner": "B", "is_draw": False}
        return {"winner": None, "is_draw": True}


# ═══════════════════════════════════════════════════════════════════
# 6. OUTPUT VALIDATORS
# ═══════════════════════════════════════════════════════════════════

def validate_warmup_question(data: Dict[str, Any]) -> ValidationResult:
    """Validate warmup question output."""
    result = ValidationResult()
    fv = FieldValidator()

    fv.required(data, "warmup_question", result)
    fv.non_empty_string(data.get("warmup_question"), "warmup_question", result)

    return result


def validate_round_start_info(data: Dict[str, Any]) -> ValidationResult:
    """Validate round start info output."""
    result = ValidationResult()
    fv = FieldValidator()

    fv.required(data, "book_name", result)
    fv.non_empty_string(data.get("book_name"), "book_name", result)

    fv.required(data, "book_hint", result)
    fv.non_empty_string(data.get("book_hint"), "book_hint", result)

    fv.required(data, "association_word", result)
    fv.non_empty_string(data.get("association_word"), "association_word", result)

    return result


def validate_answers(data: Dict[str, Any]) -> ValidationResult:
    """Validate answers output."""
    result = ValidationResult()
    fv = FieldValidator()

    answers = fv.required(data, "answers", result)
    if answers is not None and fv.is_list(answers, "answers", result, min_length=1):
        for i, ans in enumerate(answers):
            if not isinstance(ans, dict):
                result.add_error(FieldError(f"answers[{i}]", "invalid_type",
                                            expected="object", received=type(ans).__name__))
                continue

            fv.required(ans, "question_number", result)
            fv.positive_int(ans.get("question_number"), f"answers[{i}].question_number", result)

            fv.required(ans, "answer", result)
            fv.one_of(ans.get("answer"), f"answers[{i}].answer",
                      ["A", "B", "C", "D", "Not Relevant"], result)

    return result


def validate_score_feedback(data: Dict[str, Any]) -> ValidationResult:
    """Validate score feedback output."""
    result = ValidationResult()
    fv = FieldValidator()

    fv.required(data, "league_points", result)
    fv.number_in_range(data.get("league_points"), "league_points", 0, 3, result)

    fv.required(data, "private_score", result)
    fv.number_in_range(data.get("private_score"), "private_score", 0, 100, result)

    breakdown = fv.required(data, "breakdown", result)
    if breakdown is not None and isinstance(breakdown, dict):
        fv.required(breakdown, "opening_sentence_score", result)
        fv.number_in_range(breakdown.get("opening_sentence_score"),
                           "breakdown.opening_sentence_score", 0, 100, result)

        fv.required(breakdown, "sentence_justification_score", result)
        fv.number_in_range(breakdown.get("sentence_justification_score"),
                           "breakdown.sentence_justification_score", 0, 100, result)

        fv.required(breakdown, "associative_word_score", result)
        fv.number_in_range(breakdown.get("associative_word_score"),
                           "breakdown.associative_word_score", 0, 100, result)

        fv.required(breakdown, "word_justification_score", result)
        fv.number_in_range(breakdown.get("word_justification_score"),
                           "breakdown.word_justification_score", 0, 100, result)

    return result

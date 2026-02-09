"""
Q21 LLM SDK — Generators
=========================
Four generator classes for Q21 game content.

Each generator supports:
  - LLM mode: Uses Anthropic Claude API with prompts
  - Demo mode: Reads from markdown files
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import (
    BaseLLMClient,
    ScoreCalculator,
    SDKError,
    ValidationResult,
    validate_warmup_question,
    validate_round_start_info,
    validate_answers,
    validate_score_feedback,
)


# ═══════════════════════════════════════════════════════════════════
# 1. BASE GENERATOR
# ═══════════════════════════════════════════════════════════════════

class BaseGenerator(ABC):
    """Abstract base for all generators."""

    GENERATOR_TYPE: str = ""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        demo_path: Optional[str] = None,
    ):
        """Initialize generator.

        Args:
            llm_client: LLM client for generation (LLM mode)
            demo_path: Path to demo markdown files (Demo mode)
        """
        self._llm_client = llm_client
        self._demo_path = Path(demo_path) if demo_path else None

    @property
    def mode(self) -> str:
        """Return current mode: 'llm', 'demo', or 'none'."""
        if self._llm_client and self._llm_client.is_available():
            return "llm"
        elif self._demo_path and self._demo_path.exists():
            return "demo"
        return "none"

    @abstractmethod
    def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate output. Must be implemented by subclasses."""
        ...

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate output. Must be implemented by subclasses."""
        ...

    def _read_demo_file(self, filename: str) -> str:
        """Read content from demo markdown file."""
        if not self._demo_path:
            raise SDKError(self.GENERATOR_TYPE, "Demo path not configured")

        file_path = self._demo_path / filename
        if not file_path.exists():
            raise SDKError(self.GENERATOR_TYPE, f"Demo file not found: {file_path}")

        return file_path.read_text(encoding="utf-8")

    def _generate_with_llm(self, prompt: str) -> str:
        """Generate text using LLM client."""
        if not self._llm_client:
            raise SDKError(self.GENERATOR_TYPE, "LLM client not configured")

        response = self._llm_client.generate(prompt)
        if not response:
            raise SDKError(self.GENERATOR_TYPE, "LLM returned empty response")

        return response


# ═══════════════════════════════════════════════════════════════════
# 2. WARMUP QUESTION GENERATOR
# ═══════════════════════════════════════════════════════════════════

WARMUP_PROMPT = """Generate a simple warmup question for a Q21 game.
The question should be easy to answer and verify player connectivity.

Examples:
- "What is 2 + 2?"
- "What color is the sky on a clear day?"
- "Name a fruit that is typically red."

Generate ONE simple question. Reply with just the question, nothing else."""


class WarmupQuestionGenerator(BaseGenerator):
    """Generates warmup questions for Q21WARMUPCALL."""

    GENERATOR_TYPE = "warmup_question"
    DEMO_FILE = "Q21_WARMUP_CALL.REFEREE_step0_WarmupQuestion.md"

    def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate warmup question.

        Returns:
            {"warmup_question": "..."}
        """
        if self.mode == "demo":
            return self._generate_from_demo()
        elif self.mode == "llm":
            return self._generate_from_llm()
        else:
            # Fallback
            return {"warmup_question": "What is 2 + 2?"}

    def _generate_from_demo(self) -> Dict[str, Any]:
        """Parse warmup question from demo markdown."""
        content = self._read_demo_file(self.DEMO_FILE)
        return self._parse_warmup_markdown(content)

    def _generate_from_llm(self) -> Dict[str, Any]:
        """Generate warmup question using LLM."""
        response = self._generate_with_llm(WARMUP_PROMPT)
        return {"warmup_question": response.strip()}

    def _parse_warmup_markdown(self, content: str) -> Dict[str, Any]:
        """Parse warmup question from markdown content."""
        # Look for warmup_question field
        match = re.search(r'"warmup_question"\s*:\s*"([^"]+)"', content)
        if match:
            return {"warmup_question": match.group(1)}

        # Look for question in payload section
        match = re.search(r'question["\s:]+([^\n"]+)', content, re.IGNORECASE)
        if match:
            return {"warmup_question": match.group(1).strip().strip('"')}

        return {"warmup_question": "What is your favorite color?"}

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        return validate_warmup_question(data)


# ═══════════════════════════════════════════════════════════════════
# 3. ROUND START INFO GENERATOR
# ═══════════════════════════════════════════════════════════════════

ROUND_START_PROMPT = """Generate book information for a Q21 guessing game.

You need to provide:
1. BOOK_NAME: A real or fictional book title (the "mystery" to guess)
2. BOOK_HINT: A 10-15 word hint about the book (without revealing the title)
3. ASSOCIATION_WORD: A domain/category for the associative word (e.g., "color", "animal", "emotion")

The players will try to guess:
- The opening sentence of the book
- An associative word from the given domain

Format your response exactly like this:
BOOK_NAME: [title]
BOOK_HINT: [10-15 word description]
ASSOCIATION_WORD: [domain/category]"""


class RoundStartInfoGenerator(BaseGenerator):
    """Generates round start info for Q21ROUNDSTART."""

    GENERATOR_TYPE = "round_start_info"
    DEMO_FILE = "Q21_ROUND_START.REFEREE_step1_game_setup.md"

    def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate round start info.

        Returns:
            {"book_name": "...", "book_hint": "...", "association_word": "..."}
        """
        if self.mode == "demo":
            return self._generate_from_demo()
        elif self.mode == "llm":
            return self._generate_from_llm()
        else:
            # Fallback
            return {
                "book_name": "Mystery Book",
                "book_hint": "A classic novel about adventure and discovery",
                "association_word": "General",
            }

    def _generate_from_demo(self) -> Dict[str, Any]:
        """Parse round start info from demo markdown."""
        content = self._read_demo_file(self.DEMO_FILE)
        return self._parse_round_start_markdown(content)

    def _generate_from_llm(self) -> Dict[str, Any]:
        """Generate round start info using LLM."""
        response = self._generate_with_llm(ROUND_START_PROMPT)
        return self._parse_llm_response(response)

    def _parse_round_start_markdown(self, content: str) -> Dict[str, Any]:
        """Parse round start info from markdown content."""
        result = {
            "book_name": "Mystery Book",
            "book_hint": "",
            "association_word": "General",
        }

        # Try JSON format first: "book_name": "..."
        match = re.search(r'"book_name"\s*:\s*"([^"]+)"', content)
        if match:
            result["book_name"] = match.group(1)
        else:
            # Try markdown format: **Book Title:** ...
            match = re.search(r'\*\*Book Title:\*\*\s*(.+?)(?:\n|$)', content)
            if match:
                result["book_name"] = match.group(1).strip()

        # Try JSON format for hint
        match = re.search(r'"book_hint"\s*:\s*"([^"]+)"', content)
        if not match:
            match = re.search(r'"book_description"\s*:\s*"([^"]+)"', content)
        if match:
            result["book_hint"] = match.group(1)
        else:
            # Try markdown format: **Hint:** ...
            match = re.search(r'\*\*Hint:\*\*\s*(.+?)(?:\n|$)', content)
            if match:
                result["book_hint"] = match.group(1).strip()

        # Try JSON format for association_word
        match = re.search(r'"association_word"\s*:\s*"([^"]+)"', content)
        if not match:
            match = re.search(r'"associative_domain"\s*:\s*"([^"]+)"', content)
        if match:
            result["association_word"] = match.group(1)
        else:
            # Try markdown format: **Topic:** ...
            match = re.search(r'\*\*Topic:\*\*\s*(.+?)(?:\n|$)', content)
            if match:
                result["association_word"] = match.group(1).strip()

        return result

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into round start info."""
        result = {
            "book_name": "Mystery Book",
            "book_hint": "",
            "association_word": "General",
        }

        book_match = re.search(r"BOOK_NAME:\s*(.+?)(?:\n|$)", response)
        if book_match:
            result["book_name"] = book_match.group(1).strip()

        hint_match = re.search(r"BOOK_HINT:\s*(.+?)(?:\n|$)", response)
        if hint_match:
            result["book_hint"] = hint_match.group(1).strip()

        word_match = re.search(r"ASSOCIATION_WORD:\s*(.+?)(?:\n|$)", response)
        if word_match:
            result["association_word"] = word_match.group(1).strip()

        return result

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        return validate_round_start_info(data)


# ═══════════════════════════════════════════════════════════════════
# 4. ANSWERS GENERATOR
# ═══════════════════════════════════════════════════════════════════

ANSWERS_PROMPT_TEMPLATE = """You are the referee in a Q21 game. Answer these questions about the book.

BOOK: {book_name}
OPENING SENTENCE: {actual_opening_sentence}
ASSOCIATIVE WORD: {actual_associative_word}

QUESTIONS:
{questions_text}

For each question, provide the correct answer (A, B, C, or D).

Format your response as:
1: [A/B/C/D]
2: [A/B/C/D]
...and so on"""


class AnswersGenerator(BaseGenerator):
    """Generates answers for Q21ANSWERSBATCH."""

    GENERATOR_TYPE = "answers"
    DEMO_FILE = "Q21_ANSWERS_BATCH.REFEREE_step3_answers.md"

    def generate(
        self,
        questions: Optional[List[Dict[str, Any]]] = None,
        book_name: Optional[str] = None,
        actual_opening_sentence: Optional[str] = None,
        actual_associative_word: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate answers for questions.

        Args:
            questions: List of question objects (for LLM mode)
            book_name: Book title (for LLM mode)
            actual_opening_sentence: The actual opening sentence (for LLM mode)
            actual_associative_word: The actual associative word (for LLM mode)

        Returns:
            {"answers": [{"question_number": 1, "answer": "A"}, ...]}
        """
        if self.mode == "demo":
            return self._generate_from_demo()
        elif self.mode == "llm" and questions:
            return self._generate_from_llm(
                questions, book_name or "",
                actual_opening_sentence or "",
                actual_associative_word or ""
            )
        else:
            # Fallback: default answers
            num_questions = len(questions) if questions else 20
            return self._generate_default_answers(num_questions)

    def _generate_from_demo(self) -> Dict[str, Any]:
        """Parse answers from demo markdown."""
        content = self._read_demo_file(self.DEMO_FILE)
        return self._parse_answers_markdown(content)

    def _generate_from_llm(
        self,
        questions: List[Dict[str, Any]],
        book_name: str,
        actual_opening_sentence: str,
        actual_associative_word: str,
    ) -> Dict[str, Any]:
        """Generate answers using LLM."""
        questions_text = self._format_questions(questions)
        prompt = ANSWERS_PROMPT_TEMPLATE.format(
            book_name=book_name,
            actual_opening_sentence=actual_opening_sentence,
            actual_associative_word=actual_associative_word,
            questions_text=questions_text,
        )
        response = self._generate_with_llm(prompt)
        return self._parse_answers_response(response, len(questions))

    def _format_questions(self, questions: List[Dict[str, Any]]) -> str:
        """Format questions for LLM prompt."""
        lines = []
        for q in questions:
            num = q.get("question_number", q.get("number", 0))
            text = q.get("question_text", q.get("text", ""))
            options = q.get("options", q.get("choices", {}))
            lines.append(f"{num}. {text}")
            for key in ["A", "B", "C", "D"]:
                if key in options:
                    lines.append(f"   {key}: {options[key]}")
        return "\n".join(lines)

    def _parse_answers_markdown(self, content: str) -> Dict[str, Any]:
        """Parse answers from markdown content."""
        answers = []

        # Look for answers array in JSON
        match = re.search(r'"answers"\s*:\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            array_content = match.group(1)
            # Parse individual answer objects
            for ans_match in re.finditer(
                r'\{\s*"question_number"\s*:\s*(\d+)\s*,\s*"answer"\s*:\s*"([A-D])"\s*\}',
                array_content
            ):
                answers.append({
                    "question_number": int(ans_match.group(1)),
                    "answer": ans_match.group(2),
                })

        if not answers:
            # Generate default 20 answers
            return self._generate_default_answers(20)

        return {"answers": answers}

    def _parse_answers_response(self, response: str, num_questions: int) -> Dict[str, Any]:
        """Parse LLM response into answers."""
        answers = []

        for match in re.finditer(r'(\d+)\s*:\s*([A-D])', response):
            answers.append({
                "question_number": int(match.group(1)),
                "answer": match.group(2),
            })

        if not answers:
            return self._generate_default_answers(num_questions)

        return {"answers": answers}

    def _generate_default_answers(self, num_questions: int) -> Dict[str, Any]:
        """Generate default answers (all B)."""
        return {
            "answers": [
                {"question_number": i + 1, "answer": "B"}
                for i in range(num_questions)
            ]
        }

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        return validate_answers(data)


# ═══════════════════════════════════════════════════════════════════
# 5. SCORE FEEDBACK GENERATOR
# ═══════════════════════════════════════════════════════════════════

class ScoreFeedbackGenerator(BaseGenerator):
    """Generates score feedback for Q21SCOREFEEDBACK using ScoreCalculator."""

    GENERATOR_TYPE = "score_feedback"
    DEMO_FILE_A = "Q21_SCORE_FEEDBACK.08_player_A_result.md"
    DEMO_FILE_B = "Q21_SCORE_FEEDBACK.09_player_B_result.md"

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        demo_path: Optional[str] = None,
    ):
        super().__init__(llm_client, demo_path)
        self._calculator = ScoreCalculator()

    def generate(
        self,
        player: Optional[str] = None,
        actual_opening_sentence: Optional[str] = None,
        actual_associative_word: Optional[str] = None,
        opening_sentence_guess: Optional[str] = None,
        sentence_justification: Optional[str] = None,
        associative_word_guess: Optional[str] = None,
        word_justification: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate score feedback.

        Args:
            player: "A" or "B" (for demo mode)
            actual_opening_sentence: The actual opening sentence
            actual_associative_word: The actual associative word
            opening_sentence_guess: Player's sentence guess
            sentence_justification: Player's sentence justification
            associative_word_guess: Player's word guess
            word_justification: Player's word justification

        Returns:
            {"league_points": 0-3, "private_score": 0-100, "breakdown": {...}, "feedback": {...}}
        """
        if self.mode == "demo" and player:
            return self._generate_from_demo(player)
        elif actual_opening_sentence and opening_sentence_guess:
            return self._generate_from_calculator(
                actual_opening_sentence,
                actual_associative_word or "",
                opening_sentence_guess,
                sentence_justification or "",
                associative_word_guess or "",
                word_justification or "",
            )
        else:
            # Fallback
            return self._generate_default()

    def _generate_from_demo(self, player: str) -> Dict[str, Any]:
        """Parse score feedback from demo markdown."""
        player = player.upper()
        demo_file = self.DEMO_FILE_A if player == "A" else self.DEMO_FILE_B
        content = self._read_demo_file(demo_file)
        return self._parse_score_markdown(content)

    def _generate_from_calculator(
        self,
        actual_sentence: str,
        actual_word: str,
        sentence_guess: str,
        sentence_just: str,
        word_guess: str,
        word_just: str,
    ) -> Dict[str, Any]:
        """Generate scores using ScoreCalculator."""
        scores = self._calculator.calculate_player_scores(
            actual_sentence=actual_sentence,
            actual_word=actual_word,
            opening_sentence_guess=sentence_guess,
            sentence_justification=sentence_just,
            associative_word_guess=word_guess,
            word_justification=word_just,
        )

        # Generate feedback text
        feedback = self._generate_feedback(scores)

        return {
            "league_points": scores["league_points"],
            "private_score": scores["private_score"],
            "breakdown": {
                "opening_sentence_score": scores["opening_sentence_score"],
                "sentence_justification_score": scores["sentence_justification_score"],
                "associative_word_score": scores["associative_word_score"],
                "word_justification_score": scores["word_justification_score"],
            },
            "feedback": feedback,
        }

    def _parse_score_markdown(self, content: str) -> Dict[str, Any]:
        """Parse score feedback from markdown content."""
        result = self._generate_default()

        # Parse league_points
        match = re.search(r'"league_points"\s*:\s*(\d+)', content)
        if match:
            result["league_points"] = int(match.group(1))

        # Parse private_score
        match = re.search(r'"private_score"\s*:\s*([\d.]+)', content)
        if match:
            result["private_score"] = float(match.group(1))

        # Parse breakdown scores
        for field in ["opening_sentence_score", "sentence_justification_score",
                      "associative_word_score", "word_justification_score"]:
            match = re.search(rf'"{field}"\s*:\s*([\d.]+)', content)
            if match:
                result["breakdown"][field] = float(match.group(1))

        return result

    def _generate_feedback(self, scores: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback text based on scores."""
        sentence_score = scores.get("opening_sentence_score", 0)
        word_score = scores.get("associative_word_score", 0)

        if sentence_score >= 90:
            sentence_feedback = "Excellent match with the actual opening!"
        elif sentence_score >= 70:
            sentence_feedback = "Good attempt, minor differences."
        else:
            sentence_feedback = "Keep trying!"

        if word_score >= 100:
            word_feedback = "Correct!"
        else:
            word_feedback = "Not the word we were looking for."

        return {
            "opening_sentence": sentence_feedback,
            "associative_word": word_feedback,
        }

    def _generate_default(self) -> Dict[str, Any]:
        """Generate default score feedback."""
        return {
            "league_points": 0,
            "private_score": 0.0,
            "breakdown": {
                "opening_sentence_score": 0.0,
                "sentence_justification_score": 0.0,
                "associative_word_score": 0.0,
                "word_justification_score": 0.0,
            },
            "feedback": {
                "opening_sentence": "No guess provided.",
                "associative_word": "No guess provided.",
            },
        }

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        return validate_score_feedback(data)

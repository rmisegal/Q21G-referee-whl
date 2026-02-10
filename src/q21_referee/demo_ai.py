# Area: Shared
# PRD: docs/prd-rlgm.md
"""
q21_referee.demo_ai — Demo Referee AI Implementation
=====================================================

A ready-to-use RefereeAI implementation that works out of the box.
Uses the LLM SDK in demo mode to read from pre-written markdown files.

Usage:
    from q21_referee import DemoAI, RLGMRunner

    runner = RLGMRunner(config=config, ai=DemoAI())
    runner.run()
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from .callbacks import RefereeAI


# Default demo data path (relative to package)
DEFAULT_DEMO_PATH = Path(__file__).parent.parent.parent / "demo_data"


class DemoAI(RefereeAI):
    """
    Demo implementation of RefereeAI using pre-written responses.

    This class provides a working referee AI without requiring students
    to implement any callbacks. It reads from demo markdown files and
    uses the LLM SDK's scoring calculator.

    The "secret" answers (actual opening sentence and associative word)
    are loaded from Q21_INTERNAL.REFEREE_private_data.md and stored
    internally for scoring.
    """

    def __init__(self, demo_path: Optional[str] = None):
        """
        Initialize DemoAI.

        Args:
            demo_path: Path to demo markdown files. Defaults to demo_data/
        """
        self._demo_path = Path(demo_path) if demo_path else DEFAULT_DEMO_PATH
        self._actual_opening_sentence: Optional[str] = None
        self._actual_associative_word: Optional[str] = None
        self._book_name: Optional[str] = None
        self._book_hint: Optional[str] = None
        self._association_domain: Optional[str] = None
        self._load_private_data()

    def _load_private_data(self) -> None:
        """Load secret answers from internal data file."""
        private_file = self._demo_path / "Q21_INTERNAL.REFEREE_private_data.md"
        if not private_file.exists():
            # Use defaults if file doesn't exist
            self._actual_opening_sentence = (
                "In my younger and more vulnerable years my father gave me "
                "some advice that I've been turning over in my mind ever since."
            )
            self._actual_associative_word = "green"
            return

        content = private_file.read_text(encoding="utf-8")

        # Parse actual_opening_sentence
        match = re.search(
            r'"actual_opening_sentence"\s*:\s*"([^"]+)"', content
        )
        if match:
            self._actual_opening_sentence = match.group(1)

        # Parse actual_associative_word
        match = re.search(
            r'"actual_associative_word"\s*:\s*"([^"]+)"', content
        )
        if match:
            self._actual_associative_word = match.group(1)

    def _read_demo_file(self, filename: str) -> str:
        """Read content from a demo markdown file."""
        file_path = self._demo_path / filename
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")

    def get_warmup_question(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Return warmup question from demo file."""
        content = self._read_demo_file(
            "Q21_WARMUP_CALL.REFEREE_step0_WarmupQuestion.md"
        )

        # Parse warmup_question from content
        match = re.search(r'"warmup_question"\s*:\s*"([^"]+)"', content)
        if match:
            return {"warmup_question": match.group(1)}

        return {"warmup_question": "What is the capital of France?"}

    def get_round_start_info(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Return book info from demo file."""
        content = self._read_demo_file(
            "Q21_ROUND_START.REFEREE_step1_game_setup.md"
        )

        result = {
            "book_name": "The Great Gatsby",
            "book_hint": "A novel about the American Dream in the 1920s",
            "association_word": "color",
        }

        # Parse fields from content
        for field in ["book_name", "book_hint", "association_word"]:
            match = re.search(rf'"{field}"\s*:\s*"([^"]+)"', content)
            if match:
                result[field] = match.group(1)

        # Store for later use in scoring
        self._book_name = result["book_name"]
        self._book_hint = result["book_hint"]
        self._association_domain = result["association_word"]

        return result

    def get_answers(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Return answers from demo file or generate defaults."""
        content = self._read_demo_file(
            "Q21_ANSWERS_BATCH.REFEREE_step3_answers.md"
        )

        answers = []

        # Parse answers array from content
        for match in re.finditer(
            r'\{\s*"question_number"\s*:\s*(\d+)\s*,\s*'
            r'"answer"\s*:\s*"([A-D])"\s*\}',
            content,
        ):
            answers.append({
                "question_number": int(match.group(1)),
                "answer": match.group(2),
            })

        if answers:
            return {"answers": answers}

        # Fallback: generate answers for all questions
        dynamic = ctx.get("dynamic", ctx)
        questions = dynamic.get("questions", [])
        num_questions = len(questions) if questions else 20

        return {
            "answers": [
                {"question_number": i + 1, "answer": "B"}
                for i in range(num_questions)
            ]
        }

    def get_score_feedback(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate scores using the player's guess and secret answers."""
        dynamic = ctx.get("dynamic", ctx)
        guess = dynamic.get("player_guess", dynamic)

        # Get player's guesses
        sentence_guess = guess.get("opening_sentence", "")
        sentence_just = guess.get("sentence_justification", "")
        word_guess = guess.get("associative_word", "")
        word_just = guess.get("word_justification", "")

        # Use stored secrets for scoring
        actual_sentence = self._actual_opening_sentence or ""
        actual_word = self._actual_associative_word or ""

        # Calculate scores
        scores = self._calculate_scores(
            actual_sentence, actual_word,
            sentence_guess, sentence_just,
            word_guess, word_just,
        )

        return scores

    def _calculate_scores(
        self,
        actual_sentence: str,
        actual_word: str,
        sentence_guess: str,
        sentence_just: str,
        word_guess: str,
        word_just: str,
    ) -> Dict[str, Any]:
        """Calculate all scores for a player's guess."""
        # Sentence similarity (simple word overlap)
        sentence_score = self._calculate_similarity(
            actual_sentence, sentence_guess
        )

        # Word match (exact match = 100, else 0)
        word_score = 100.0 if (
            actual_word.lower().strip() == word_guess.lower().strip()
        ) else 0.0

        # Justification scores (based on length and keywords)
        sentence_just_score = self._score_justification(sentence_just, 30, 50)
        word_just_score = self._score_justification(word_just, 20, 30)

        # Weighted private score
        private_score = (
            sentence_score * 0.50 +
            sentence_just_score * 0.20 +
            word_score * 0.20 +
            word_just_score * 0.10
        )
        private_score = round(private_score, 2)

        # League points
        if private_score >= 85:
            league_points = 3
        elif private_score >= 70:
            league_points = 2
        elif private_score >= 50:
            league_points = 1
        else:
            league_points = 0

        return {
            "league_points": league_points,
            "private_score": private_score,
            "breakdown": {
                "opening_sentence_score": round(sentence_score, 2),
                "sentence_justification_score": round(sentence_just_score, 2),
                "associative_word_score": round(word_score, 2),
                "word_justification_score": round(word_just_score, 2),
            },
            "feedback": self._generate_feedback(
                sentence_score, word_score, actual_word
            ),
        }

    def _calculate_similarity(self, actual: str, guess: str) -> float:
        """Calculate similarity between actual and guessed sentences."""
        if not actual or not guess:
            return 0.0

        actual_lower = actual.lower()
        guess_lower = guess.lower()

        if actual_lower == guess_lower:
            return 100.0

        # Word overlap (Jaccard similarity)
        actual_words = set(actual_lower.split())
        guess_words = set(guess_lower.split())

        if not actual_words:
            return 0.0

        intersection = actual_words & guess_words
        union = actual_words | guess_words

        if not union:
            return 0.0

        jaccard = len(intersection) / len(union)
        return round(jaccard * 100, 2)

    def _score_justification(
        self, text: str, min_words: int, max_words: int
    ) -> float:
        """Score a justification based on length and quality."""
        if not text:
            return 0.0

        words = text.split()
        word_count = len(words)

        # Base score from length
        if word_count < min_words:
            length_score = (word_count / min_words) * 50
        elif word_count <= max_words:
            length_score = 70.0
        else:
            length_score = 60.0  # Slight penalty for being too long

        # Bonus for reasoning keywords
        keywords = [
            "because", "therefore", "based on", "indicates",
            "suggests", "evidence", "reasoning", "theme",
        ]
        keyword_bonus = sum(
            5 for kw in keywords if kw in text.lower()
        )

        return min(100.0, length_score + keyword_bonus)

    def _generate_feedback(
        self, sentence_score: float, word_score: float, actual_word: str
    ) -> Dict[str, str]:
        """Generate feedback text based on scores."""
        if sentence_score >= 90:
            sentence_fb = (
                "Excellent match with the actual opening sentence! Your guess "
                "captured the essence and phrasing of the original text with "
                "remarkable accuracy. The reflective tone and narrative voice "
                "were perfectly identified."
            )
        elif sentence_score >= 70:
            sentence_fb = (
                "Good attempt at the opening sentence. You captured some key "
                "elements of the original, though the exact phrasing differs. "
                "Your understanding of the narrative style is evident."
            )
        elif sentence_score >= 50:
            sentence_fb = (
                "Your guess showed understanding of the book's themes but "
                "missed the specific opening structure. Consider the narrative "
                "voice and how the author establishes the story's perspective."
            )
        else:
            sentence_fb = (
                "The opening sentence was quite different from your guess. "
                "Review how classic novels often begin with character "
                "introduction or scene-setting that establishes tone."
            )

        if word_score >= 100:
            word_fb = (
                f"Correct! '{actual_word}' is the associative word. Your "
                "understanding of the book's symbolism is excellent."
            )
        else:
            word_fb = (
                f"The associative word was '{actual_word}'. While your choice "
                "showed thoughtful engagement with the text, the primary "
                "symbolic element was different."
            )

        return {
            "opening_sentence": sentence_fb,
            "associative_word": word_fb,
        }

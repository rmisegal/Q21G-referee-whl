# Area: Shared
# PRD: docs/prd-rlgm.md
"""Demo Referee AI — ready-to-use RefereeAI using pre-written responses."""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from .callbacks import RefereeAI
from .demo_scorer import calculate_scores

DEFAULT_DEMO_PATH = Path(__file__).parent.parent.parent / "demo_data"


class DemoAI(RefereeAI):
    """Demo RefereeAI that reads from markdown files and scores via demo_scorer."""

    def __init__(self, demo_path: Optional[str] = None):
        """Initialize with optional path to demo markdown files."""
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
            self._actual_opening_sentence = (
                "In my younger and more vulnerable years my father gave me "
                "some advice that I've been turning over in my mind ever since."
            )
            self._actual_associative_word = "green"
            return
        content = private_file.read_text(encoding="utf-8")
        for field, attr in [
            ("actual_opening_sentence", "_actual_opening_sentence"),
            ("actual_associative_word", "_actual_associative_word"),
        ]:
            match = re.search(rf'"{field}"\s*:\s*"([^"]+)"', content)
            if match:
                setattr(self, attr, match.group(1))

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
        match = re.search(r'"warmup_question"\s*:\s*"([^"]+)"', content)
        if match:
            return {"warmup_question": match.group(1)}
        return {"warmup_question": "What is the capital of France?"}

    def get_round_start_info(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Return book info from demo file."""
        self._book_name = self._book_hint = self._association_domain = None
        content = self._read_demo_file(
            "Q21_ROUND_START.REFEREE_step1_game_setup.md"
        )
        result = {
            "book_name": "The Great Gatsby",
            "book_hint": "A novel about the American Dream in the 1920s",
            "association_word": "color",
        }
        for field in ["book_name", "book_hint", "association_word"]:
            match = re.search(rf'"{field}"\s*:\s*"([^"]+)"', content)
            if match:
                result[field] = match.group(1)
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
        scores = calculate_scores(
            actual_sentence, actual_word,
            sentence_guess, sentence_just,
            word_guess, word_just,
        )

        return scores

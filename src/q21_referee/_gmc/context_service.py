# Area: GMC
# PRD: docs/prd-rlgm.md
"""Service definitions for student callbacks."""

from __future__ import annotations
from typing import Any, Dict

SERVICE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "warmup_question": {
        "name": "warmup_question",
        "description": "Generate a simple question to verify player connectivity",
        "required_output_fields": ["warmup_question"],
        "deadline_seconds": 30,
    },
    "round_start_info": {
        "name": "round_start_info",
        "description": "Select a book, write a hint, and choose an association word",
        "required_output_fields": ["book_name", "book_hint", "association_word"],
        "deadline_seconds": 60,
    },
    "answers": {
        "name": "answers",
        "description": "Answer each multiple-choice question with A, B, C, D, or 'Not Relevant'",
        "required_output_fields": ["answers"],
        "deadline_seconds": 120,
    },
    "score_feedback": {
        "name": "score_feedback",
        "description": "Score the player's guess and provide 150-200 word feedback for each component",
        "required_output_fields": ["league_points", "private_score", "breakdown", "feedback"],
        "deadline_seconds": 180,
    },
}

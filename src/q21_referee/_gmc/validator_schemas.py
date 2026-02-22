# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.validator_schemas — Callback output schemas
=============================================================

Schema definitions and constants for callback output validation.
"""

from __future__ import annotations
from typing import Any, Dict


# ══════════════════════════════════════════════════════════════
# CALLBACK SCHEMAS
# ══════════════════════════════════════════════════════════════

CALLBACK_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "warmup_question": {
        "required": ["warmup_question"],
        "types": {"warmup_question": str},
        "constraints": {
            "warmup_question": {"min_length": 5},
        },
    },
    "round_start_info": {
        "required": ["book_name", "book_hint", "association_word"],
        "types": {
            "book_name": str,
            "book_hint": str,
            "association_word": str,
        },
        "constraints": {
            "book_hint": {"min_length": 10, "max_length": 200},
        },
    },
    "answers": {
        "required": ["answers"],
        "types": {"answers": list},
        "constraints": {
            "answers": {"min_length": 1},
        },
        "list_item_schema": {
            "answers": {
                "required": ["question_number", "answer"],
                "types": {"question_number": int, "answer": str},
                "constraints": {
                    "question_number": {"min": 1},
                    "answer": {"one_of": ["A", "B", "C", "D", "Not Relevant"]},
                },
            },
        },
    },
    "score_feedback": {
        "required": ["league_points", "private_score", "breakdown", "feedback"],
        "types": {
            "league_points": int,
            "private_score": (int, float),
            "breakdown": dict,
            "feedback": dict,
        },
        "constraints": {
            "league_points": {"min": 0, "max": 3},
            "private_score": {"min": 0, "max": 100},
        },
        "nested_schema": {
            "breakdown": {
                "required": [
                    "opening_sentence_score",
                    "sentence_justification_score",
                    "associative_word_score",
                    "word_justification_score",
                ],
                "types": {
                    "opening_sentence_score": (int, float),
                    "sentence_justification_score": (int, float),
                    "associative_word_score": (int, float),
                    "word_justification_score": (int, float),
                },
            },
            "feedback": {
                "required": ["opening_sentence", "associative_word"],
                "types": {
                    "opening_sentence": str,
                    "associative_word": str,
                },
                # Word count is a soft constraint - checked separately with penalty
            },
        },
    },
}

# Soft constraints for score_feedback (apply penalty instead of failing)
SCORE_FEEDBACK_WORD_LIMITS = {
    "opening_sentence": {"min_words": 150, "max_words": 200},
    "associative_word": {"min_words": 150, "max_words": 200},
}
WORD_COUNT_PENALTY_PERCENT = 5  # 5% penalty per field violation

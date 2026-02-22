# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.validator — Output schema validation
=====================================================

Validates callback outputs against expected schemas.
Returns list of validation errors (empty if valid).
"""

from __future__ import annotations
from typing import Any, Dict, List

from .validator_schemas import (
    CALLBACK_SCHEMAS,
    SCORE_FEEDBACK_WORD_LIMITS,
    WORD_COUNT_PENALTY_PERCENT,
)
from .validator_helpers import (
    _check_required_fields,
    _check_types,
    _check_constraints,
    _count_words,
)
from .validator_composite import (
    _check_list_items,
    _check_nested,
)


# ══════════════════════════════════════════════════════════════
# MAIN VALIDATION FUNCTION
# ══════════════════════════════════════════════════════════════

def validate_output(callback_name: str, output: Any) -> List[str]:
    """
    Validate a callback's output against its schema.

    Parameters
    ----------
    callback_name : str
        The callback name (e.g., "warmup_question", "score_feedback").
    output : Any
        The output returned by the callback.

    Returns
    -------
    List[str]
        List of validation error messages. Empty if valid.
    """
    errors: List[str] = []

    # Check if schema exists
    if callback_name not in CALLBACK_SCHEMAS:
        errors.append(f"Unknown callback: {callback_name}")
        return errors

    schema = CALLBACK_SCHEMAS[callback_name]

    # Check if output is a dict
    if not isinstance(output, dict):
        errors.append(f"Expected dict, got {type(output).__name__}")
        return errors

    # Check required fields
    errors.extend(_check_required_fields(schema, output))

    # Check types
    errors.extend(_check_types(schema, output))

    # Check constraints
    errors.extend(_check_constraints(schema, output))

    # Check list item schemas
    if "list_item_schema" in schema:
        errors.extend(_check_list_items(schema["list_item_schema"], output))

    # Check nested schemas
    if "nested_schema" in schema:
        errors.extend(_check_nested(schema["nested_schema"], output))

    return errors


def apply_score_feedback_penalties(output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check soft constraints on score_feedback and apply penalties.

    Modifies private_score by deducting 5% for each word count violation.
    Returns the modified output dict.
    """
    if "feedback" not in output or not isinstance(output["feedback"], dict):
        return output

    feedback = output["feedback"]
    violations = []

    for field, limits in SCORE_FEEDBACK_WORD_LIMITS.items():
        if field not in feedback:
            continue

        text = feedback[field]
        if not isinstance(text, str):
            continue

        word_count = _count_words(text)
        min_words = limits.get("min_words", 0)
        max_words = limits.get("max_words", float("inf"))

        if word_count < min_words:
            violations.append(f"{field}: {word_count} words < {min_words} min")
        elif word_count > max_words:
            violations.append(f"{field}: {word_count} words > {max_words} max")

    if violations:
        import logging
        logger = logging.getLogger("q21_referee.validator")

        # Apply penalty: 5% per violation
        penalty_percent = WORD_COUNT_PENALTY_PERCENT * len(violations)
        original_score = output.get("private_score", 0)
        penalty_amount = original_score * (penalty_percent / 100)
        new_score = max(0, original_score - penalty_amount)

        logger.warning(
            f"Word count violations in feedback: {violations}. "
            f"Applying {penalty_percent}% penalty: {original_score} -> {new_score}"
        )

        output["private_score"] = new_score

    return output

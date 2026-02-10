# Area: GMC
# PRD: docs/prd-rlgm.md
# NOTE: This file exceeds 150 lines and will be split in Part 22
"""
q21_referee._gmc.validator — Output schema validation
=====================================================

Validates callback outputs against expected schemas.
Returns list of validation errors (empty if valid).
"""

from __future__ import annotations
from typing import Any, Dict, List, Union


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
                "constraints": {
                    "opening_sentence": {"min_words": 150, "max_words": 200},
                    "associative_word": {"min_words": 150, "max_words": 200},
                },
            },
        },
    },
}


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


# ══════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════

def _check_required_fields(schema: Dict, output: Dict) -> List[str]:
    """Check that all required fields are present."""
    errors = []
    for field in schema.get("required", []):
        if field not in output:
            errors.append(f"Missing required field: '{field}'")
    return errors


def _check_types(schema: Dict, output: Dict) -> List[str]:
    """Check that fields have correct types."""
    errors = []
    type_specs = schema.get("types", {})

    for field, expected_type in type_specs.items():
        if field not in output:
            continue  # Already caught by required check

        value = output[field]

        # Handle tuple of types (e.g., (int, float))
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                type_names = " or ".join(t.__name__ for t in expected_type)
                errors.append(
                    f"Field '{field}' has wrong type: expected {type_names}, "
                    f"got {type(value).__name__}"
                )
        else:
            if not isinstance(value, expected_type):
                errors.append(
                    f"Field '{field}' has wrong type: expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

    return errors


def _check_constraints(schema: Dict, output: Dict) -> List[str]:
    """Check field constraints (min, max, min_length, etc.)."""
    errors = []
    constraints = schema.get("constraints", {})

    for field, field_constraints in constraints.items():
        if field not in output:
            continue

        value = output[field]
        errors.extend(_apply_constraints(field, value, field_constraints))

    return errors


def _apply_constraints(field: str, value: Any, constraints: Dict) -> List[str]:
    """Apply constraints to a single field value."""
    errors = []

    # min_length for strings/lists
    if "min_length" in constraints:
        min_len = constraints["min_length"]
        if hasattr(value, "__len__") and len(value) < min_len:
            errors.append(
                f"Field '{field}' is too short: {len(value)} < {min_len}"
            )

    # max_length for strings/lists
    if "max_length" in constraints:
        max_len = constraints["max_length"]
        if hasattr(value, "__len__") and len(value) > max_len:
            errors.append(
                f"Field '{field}' is too long: {len(value)} > {max_len}"
            )

    # min for numbers
    if "min" in constraints:
        min_val = constraints["min"]
        if isinstance(value, (int, float)) and value < min_val:
            errors.append(
                f"Field '{field}' is too small: {value} < {min_val}"
            )

    # max for numbers
    if "max" in constraints:
        max_val = constraints["max"]
        if isinstance(value, (int, float)) and value > max_val:
            errors.append(
                f"Field '{field}' is too large: {value} > {max_val}"
            )

    # min_words for strings
    if "min_words" in constraints:
        min_words = constraints["min_words"]
        if isinstance(value, str):
            word_count = _count_words(value)
            if word_count < min_words:
                errors.append(
                    f"Field '{field}' has too few words: {word_count} < {min_words}"
                )

    # max_words for strings
    if "max_words" in constraints:
        max_words = constraints["max_words"]
        if isinstance(value, str):
            word_count = _count_words(value)
            if word_count > max_words:
                errors.append(
                    f"Field '{field}' has too many words: {word_count} > {max_words}"
                )

    # one_of for enum values
    if "one_of" in constraints:
        allowed = constraints["one_of"]
        if value not in allowed:
            errors.append(
                f"Field '{field}' has invalid value: '{value}' not in {allowed}"
            )

    return errors


def _check_list_items(list_schemas: Dict, output: Dict) -> List[str]:
    """Validate items in list fields."""
    errors = []

    for field, item_schema in list_schemas.items():
        if field not in output or not isinstance(output[field], list):
            continue

        for i, item in enumerate(output[field]):
            if not isinstance(item, dict):
                errors.append(f"{field}[{i}]: expected dict, got {type(item).__name__}")
                continue

            # Check required fields in item
            for req_field in item_schema.get("required", []):
                if req_field not in item:
                    errors.append(f"{field}[{i}]: missing required field '{req_field}'")

            # Check types in item
            for type_field, expected_type in item_schema.get("types", {}).items():
                if type_field in item:
                    if not isinstance(item[type_field], expected_type):
                        errors.append(
                            f"{field}[{i}].{type_field}: expected {expected_type.__name__}, "
                            f"got {type(item[type_field]).__name__}"
                        )

            # Check constraints in item
            for constraint_field, field_constraints in item_schema.get("constraints", {}).items():
                if constraint_field in item:
                    item_errors = _apply_constraints(
                        f"{field}[{i}].{constraint_field}",
                        item[constraint_field],
                        field_constraints,
                    )
                    errors.extend(item_errors)

    return errors


def _check_nested(nested_schemas: Dict, output: Dict) -> List[str]:
    """Validate nested dict fields."""
    errors = []

    for field, nested_schema in nested_schemas.items():
        if field not in output or not isinstance(output[field], dict):
            continue

        nested_output = output[field]

        # Check required fields in nested
        for req_field in nested_schema.get("required", []):
            if req_field not in nested_output:
                errors.append(f"{field}.{req_field}: missing required field")

        # Check types in nested
        for type_field, expected_type in nested_schema.get("types", {}).items():
            if type_field in nested_output:
                value = nested_output[type_field]
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        type_names = " or ".join(t.__name__ for t in expected_type)
                        errors.append(
                            f"{field}.{type_field}: expected {type_names}, "
                            f"got {type(value).__name__}"
                        )
                else:
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"{field}.{type_field}: expected {expected_type.__name__}, "
                            f"got {type(value).__name__}"
                        )

        # Check constraints in nested
        for constraint_field, field_constraints in nested_schema.get("constraints", {}).items():
            if constraint_field in nested_output:
                nested_errors = _apply_constraints(
                    f"{field}.{constraint_field}",
                    nested_output[constraint_field],
                    field_constraints,
                )
                errors.extend(nested_errors)

    return errors


def _count_words(text: str) -> int:
    """Count words in a text string."""
    if not text:
        return 0
    return len(text.split())

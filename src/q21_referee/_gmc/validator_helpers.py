# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.validator_helpers — Field-level validation helpers
===================================================================

Core helper functions for validating individual fields against schemas.
"""

from __future__ import annotations
from typing import Any, Dict, List


# ══════════════════════════════════════════════════════════════
# FIELD-LEVEL VALIDATION HELPERS
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


def _count_words(text: str) -> int:
    """Count words in a text string."""
    if not text:
        return 0
    return len(text.split())

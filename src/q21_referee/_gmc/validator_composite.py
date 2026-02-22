# Area: GMC
# PRD: docs/prd-rlgm.md
"""Composite validation helpers for list items and nested dicts."""

from __future__ import annotations
from typing import Any, Dict, List

from .validator_helpers import _apply_constraints


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
            for req_field in item_schema.get("required", []):
                if req_field not in item:
                    errors.append(f"{field}[{i}]: missing required field '{req_field}'")
            for type_field, expected_type in item_schema.get("types", {}).items():
                if type_field in item:
                    if not isinstance(item[type_field], expected_type):
                        errors.append(
                            f"{field}[{i}].{type_field}: expected {expected_type.__name__}, "
                            f"got {type(item[type_field]).__name__}")
            for constraint_field, field_constraints in item_schema.get("constraints", {}).items():
                if constraint_field in item:
                    errors.extend(_apply_constraints(
                        f"{field}[{i}].{constraint_field}",
                        item[constraint_field], field_constraints))
    return errors


def _check_nested(nested_schemas: Dict, output: Dict) -> List[str]:
    """Validate nested dict fields."""
    errors = []
    for field, nested_schema in nested_schemas.items():
        if field not in output or not isinstance(output[field], dict):
            continue
        nested_output = output[field]
        for req_field in nested_schema.get("required", []):
            if req_field not in nested_output:
                errors.append(f"{field}.{req_field}: missing required field")
        for type_field, expected_type in nested_schema.get("types", {}).items():
            if type_field in nested_output:
                value = nested_output[type_field]
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        type_names = " or ".join(t.__name__ for t in expected_type)
                        errors.append(
                            f"{field}.{type_field}: expected {type_names}, "
                            f"got {type(value).__name__}")
                else:
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"{field}.{type_field}: expected {expected_type.__name__}, "
                            f"got {type(value).__name__}")
        for constraint_field, field_constraints in nested_schema.get("constraints", {}).items():
            if constraint_field in nested_output:
                errors.extend(_apply_constraints(
                    f"{field}.{constraint_field}",
                    nested_output[constraint_field], field_constraints))
    return errors

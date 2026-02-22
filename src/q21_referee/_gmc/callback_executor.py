# Area: GMC
# PRD: docs/prd-rlgm.md
"""
q21_referee._gmc.callback_executor — Safe callback execution
============================================================

Wraps callback invocation with timeout enforcement, JSON/schema
validation, and error handling (log + terminate on failure).
"""

from __future__ import annotations
from typing import Any, Callable, Dict
import logging

from ..errors import (
    CallbackTimeoutError,
    InvalidJSONResponseError,
    SchemaValidationError,
)
from .timeout import TimeoutHandler
from .validator import validate_output, apply_score_feedback_penalties
from .._shared.logging_config import log_and_terminate
from .._shared.protocol_logger import get_protocol_logger

logger = logging.getLogger("q21_referee.executor")


def execute_callback(
    callback_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    callback_name: str,
    ctx: Dict[str, Any],
    deadline_seconds: int,
    terminate_on_error: bool = True,
) -> Dict[str, Any]:
    """Execute a callback with timeout, validation, and error handling.

    When *terminate_on_error* is True (default), errors call
    ``log_and_terminate`` instead of raising.
    """
    logger.debug(f"[CALLBACK] Executing {callback_name} (timeout={deadline_seconds}s)")
    protocol_logger = get_protocol_logger()
    protocol_logger.log_callback_call(callback_name)

    # ── Step 1: Execute with timeout ──────────────────────────
    try:
        with TimeoutHandler(deadline_seconds, callback_name, ctx):
            result = callback_fn(ctx)
    except CallbackTimeoutError as e:
        if terminate_on_error:
            log_and_terminate(e)
        raise

    # ── Step 2: Validate return type is dict ──────────────────
    if not isinstance(result, dict):
        error = InvalidJSONResponseError(
            callback_name=callback_name,
            input_payload=ctx,
            raw_output=result,
        )
        if terminate_on_error:
            log_and_terminate(error)
        raise error

    # ── Step 3: Validate against schema ───────────────────────
    validation_errors = validate_output(callback_name, result)
    if validation_errors:
        error = SchemaValidationError(
            callback_name=callback_name,
            input_payload=ctx,
            output_payload=result,
            validation_errors=validation_errors,
        )
        if terminate_on_error:
            log_and_terminate(error)
        raise error

    # ── Step 4: Apply soft constraint penalties ───────────────
    if callback_name == "score_feedback":
        result = apply_score_feedback_penalties(result)

    logger.debug(f"[CALLBACK] {callback_name} completed successfully")
    protocol_logger.log_callback_response(callback_name)
    return result


def execute_callback_safe(
    callback_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    callback_name: str,
    ctx: Dict[str, Any],
    deadline_seconds: int,
) -> Dict[str, Any]:
    """Execute a callback, raising exceptions instead of terminating.

    Convenience wrapper that calls ``execute_callback`` with
    ``terminate_on_error=False``. Useful for testing.
    """
    return execute_callback(
        callback_fn=callback_fn,
        callback_name=callback_name,
        ctx=ctx,
        deadline_seconds=deadline_seconds,
        terminate_on_error=False,
    )

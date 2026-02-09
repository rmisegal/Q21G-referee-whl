"""
q21_referee.callback_executor — Safe callback execution
========================================================

Wraps callback invocation with:
1. Timeout enforcement
2. JSON validation (ensure dict returned)
3. Schema validation
4. Error handling (log + terminate on failure)
"""

from __future__ import annotations
import signal
import sys
from typing import Any, Callable, Dict
import logging

from .errors import (
    CallbackTimeoutError,
    InvalidJSONResponseError,
    SchemaValidationError,
)
from .validator import validate_output
from .logging_config import log_and_terminate

logger = logging.getLogger("q21_referee.executor")


class TimeoutHandler:
    """Context manager for callback timeout enforcement."""

    def __init__(self, seconds: int, callback_name: str, input_payload: Dict):
        self.seconds = seconds
        self.callback_name = callback_name
        self.input_payload = input_payload
        self._old_handler = None

    def _timeout_handler(self, signum, frame):
        raise CallbackTimeoutError(
            callback_name=self.callback_name,
            deadline_seconds=self.seconds,
            input_payload=self.input_payload,
        )

    def __enter__(self):
        # Only use signal-based timeout on Unix systems
        if hasattr(signal, "SIGALRM"):
            self._old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)  # Cancel the alarm
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False  # Don't suppress exceptions


def execute_callback(
    callback_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    callback_name: str,
    ctx: Dict[str, Any],
    deadline_seconds: int,
    terminate_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Execute a callback with timeout, validation, and error handling.

    Parameters
    ----------
    callback_fn : Callable
        The callback function to execute.
    callback_name : str
        Name of the callback (for error messages and validation).
    ctx : dict
        The context dict to pass to the callback.
    deadline_seconds : int
        Maximum time allowed for the callback to complete.
    terminate_on_error : bool
        If True, terminate process on error. If False, raise exception.
        Defaults to True.

    Returns
    -------
    dict
        The validated output from the callback.

    Raises
    ------
    CallbackTimeoutError
        If callback exceeds deadline (only if terminate_on_error=False).
    InvalidJSONResponseError
        If callback returns non-dict (only if terminate_on_error=False).
    SchemaValidationError
        If output fails validation (only if terminate_on_error=False).
    """
    logger.info(f"[CALLBACK] Executing {callback_name} (timeout={deadline_seconds}s)")

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

    logger.info(f"[CALLBACK] {callback_name} completed successfully")
    return result


def execute_callback_safe(
    callback_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    callback_name: str,
    ctx: Dict[str, Any],
    deadline_seconds: int,
) -> Dict[str, Any]:
    """
    Execute a callback, raising exceptions instead of terminating.

    This is useful for testing where you want to catch and inspect errors.

    Parameters
    ----------
    callback_fn : Callable
        The callback function to execute.
    callback_name : str
        Name of the callback.
    ctx : dict
        The context dict to pass to the callback.
    deadline_seconds : int
        Maximum time allowed for the callback.

    Returns
    -------
    dict
        The validated output from the callback.

    Raises
    ------
    CallbackTimeoutError, InvalidJSONResponseError, SchemaValidationError
        On any validation failure.
    """
    return execute_callback(
        callback_fn=callback_fn,
        callback_name=callback_name,
        ctx=ctx,
        deadline_seconds=deadline_seconds,
        terminate_on_error=False,
    )

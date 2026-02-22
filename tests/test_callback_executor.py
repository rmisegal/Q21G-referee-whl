# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for callback_executor resilience."""

import pytest
from q21_referee._gmc.callback_executor import execute_callback, execute_callback_safe
from q21_referee.errors import CallbackTimeoutError, InvalidJSONResponseError


class TestExecuteCallbackDefault:
    """Test that execute_callback defaults to raising, not terminating."""

    def test_invalid_return_raises_not_exits(self):
        """With default terminate_on_error=False, bad return raises exception."""
        def bad_callback(ctx):
            return "not a dict"

        with pytest.raises(InvalidJSONResponseError):
            execute_callback(
                callback_fn=bad_callback,
                callback_name="test_cb",
                ctx={},
                deadline_seconds=5,
            )

    def test_callback_exception_propagates(self):
        """Arbitrary exceptions from callbacks should propagate."""
        def failing_callback(ctx):
            raise ValueError("student code broke")

        with pytest.raises(ValueError, match="student code broke"):
            execute_callback(
                callback_fn=failing_callback,
                callback_name="test_cb",
                ctx={},
                deadline_seconds=5,
            )

    def test_successful_callback_returns_result(self):
        """A valid callback still works normally."""
        def good_callback(ctx):
            return {"warmup_question": "What is 1+1?"}

        result = execute_callback(
            callback_fn=good_callback,
            callback_name="warmup_question",
            ctx={},
            deadline_seconds=5,
        )
        assert result["warmup_question"] == "What is 1+1?"


class TestExecuteCallbackSafe:
    """Test execute_callback_safe still works (now equivalent to default)."""

    def test_safe_raises_on_bad_return(self):
        def bad_callback(ctx):
            return 42

        with pytest.raises(InvalidJSONResponseError):
            execute_callback_safe(
                callback_fn=bad_callback,
                callback_name="test_cb",
                ctx={},
                deadline_seconds=5,
            )

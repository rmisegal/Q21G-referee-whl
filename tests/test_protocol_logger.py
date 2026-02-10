# Area: Shared Tests
# PRD: docs/LOGGER_OUTPUT_REFEREE.md
"""Tests for protocol logger."""

import pytest
import io
import sys
from unittest.mock import patch

from q21_referee._shared.protocol_logger import (
    ProtocolLogger,
    get_protocol_logger,
    RECEIVE_DISPLAY_NAMES,
    SEND_DISPLAY_NAMES,
    EXPECTED_RESPONSES,
    CALLBACK_DISPLAY_NAMES,
    GREEN,
    ORANGE,
    RED,
    RESET,
)


class TestMessageTypeMappings:
    """Tests for message type → display name mappings."""

    def test_receive_display_names_complete(self):
        """Test that all received message types have display names."""
        expected = {
            "BROADCAST_START_SEASON": "START-SEASON",
            "SEASON_REGISTRATION_RESPONSE": "SIGNUP-RESPONSE",
            "BROADCAST_ASSIGNMENT_TABLE": "ASSIGNMENT-TABLE",
            "BROADCAST_NEW_LEAGUE_ROUND": "START-ROUND",
            "Q21WARMUPRESPONSE": "PING-RESPONSE",
            "Q21_WARMUP_RESPONSE": "PING-RESPONSE",
            "Q21QUESTIONSBATCH": "ASK-20-QUESTIONS",
            "Q21_QUESTIONS_BATCH": "ASK-20-QUESTIONS",
            "Q21GUESSSUBMISSION": "MY-GUESS",
            "Q21_GUESS_SUBMISSION": "MY-GUESS",
            "LEAGUE_COMPLETED": "SEASON-ENDED",
        }
        for msg_type, display in expected.items():
            assert RECEIVE_DISPLAY_NAMES.get(msg_type) == display

    def test_send_display_names_complete(self):
        """Test that all sent message types have display names."""
        expected = {
            "SEASON_REGISTRATION_REQUEST": "SEASON-SIGNUP",
            "Q21WARMUPCALL": "PING-CALL",
            "Q21ROUNDSTART": "START-GAME",
            "Q21ANSWERSBATCH": "QUESTION-ANSWERS",
            "Q21SCOREFEEDBACK": "ROUND-SCORE-REPORT",
            "MATCH_RESULT_REPORT": "SEASON-RESULTS",
        }
        for msg_type, display in expected.items():
            assert SEND_DISPLAY_NAMES.get(msg_type) == display

    def test_expected_responses_defined(self):
        """Test that all message types have expected responses."""
        # All receive types should have expected responses
        for msg_type in RECEIVE_DISPLAY_NAMES:
            assert msg_type in EXPECTED_RESPONSES

        # All send types should have expected responses
        for msg_type in SEND_DISPLAY_NAMES:
            assert msg_type in EXPECTED_RESPONSES

    def test_callback_display_names(self):
        """Test callback name → display name mappings."""
        expected = {
            "warmup_question": "generate_warmup",
            "round_start_info": "select_book",
            "answers": "answer_questions",
            "score_feedback": "calculate_score",
        }
        assert CALLBACK_DISPLAY_NAMES == expected


class TestProtocolLogger:
    """Tests for ProtocolLogger class."""

    def test_logger_creation(self):
        """Test that logger can be created."""
        logger = ProtocolLogger()
        assert logger.role_active is True
        assert logger._current_game_id == "0000000"

    def test_set_game_id(self):
        """Test setting game ID."""
        logger = ProtocolLogger()
        logger.set_game_id("1234567")
        assert logger._current_game_id == "1234567"

    def test_set_game_id_none(self):
        """Test setting game ID to None defaults to zeros."""
        logger = ProtocolLogger()
        logger.set_game_id(None)
        assert logger._current_game_id == "0000000"

    def test_set_role_active(self):
        """Test setting role active status."""
        logger = ProtocolLogger()
        logger.set_role_active(False)
        assert logger.role_active is False
        logger.set_role_active(True)
        assert logger.role_active is True

    def test_get_role_active(self):
        """Test getting role string when active."""
        logger = ProtocolLogger()
        logger.set_role_active(True)
        assert logger._get_role() == "REFEREE-ACTIVE"

    def test_get_role_inactive(self):
        """Test getting role string when inactive."""
        logger = ProtocolLogger()
        logger.set_role_active(False)
        assert logger._get_role() == "REFEREE-INACTIVE"

    def test_log_received_output(self, capsys):
        """Test log_received prints formatted output."""
        logger = ProtocolLogger()
        logger.set_game_id("0101001")
        logger.log_received(
            email="player@test.com",
            message_type="Q21WARMUPRESPONSE",
        )
        captured = capsys.readouterr()
        output = captured.out

        assert "RECEIVED" in output
        assert "player@test.com" in output
        assert "PING-RESPONSE" in output
        assert GREEN in output
        assert RESET in output

    def test_log_sent_output(self, capsys):
        """Test log_sent prints formatted output."""
        logger = ProtocolLogger()
        logger.set_game_id("0101001")
        logger.log_sent(
            email="player@test.com",
            message_type="Q21WARMUPCALL",
        )
        captured = capsys.readouterr()
        output = captured.out

        assert "SENT" in output
        assert "player@test.com" in output
        assert "PING-CALL" in output
        assert GREEN in output
        assert RESET in output

    def test_log_callback_call_output(self, capsys):
        """Test log_callback_call prints formatted output."""
        logger = ProtocolLogger()
        logger.log_callback_call("warmup_question")
        captured = capsys.readouterr()
        output = captured.out

        assert "CALLBACK" in output
        assert "generate_warmup" in output
        assert "CALL" in output
        assert ORANGE in output
        assert RESET in output

    def test_log_callback_response_output(self, capsys):
        """Test log_callback_response prints formatted output."""
        logger = ProtocolLogger()
        logger.log_callback_response("score_feedback")
        captured = capsys.readouterr()
        output = captured.out

        assert "CALLBACK" in output
        assert "calculate_score" in output
        assert "RESPONSE" in output
        assert ORANGE in output
        assert RESET in output

    def test_log_error_output(self, capsys):
        """Test log_error prints to stderr."""
        logger = ProtocolLogger()
        logger.log_error("Something went wrong")
        captured = capsys.readouterr()
        output = captured.err

        assert "[ERROR]" in output
        assert "Something went wrong" in output
        assert RED in output
        assert RESET in output


class TestGetProtocolLogger:
    """Tests for get_protocol_logger singleton."""

    def test_returns_same_instance(self):
        """Test that get_protocol_logger returns singleton."""
        logger1 = get_protocol_logger()
        logger2 = get_protocol_logger()
        assert logger1 is logger2

    def test_is_protocol_logger_instance(self):
        """Test that returned instance is ProtocolLogger."""
        logger = get_protocol_logger()
        assert isinstance(logger, ProtocolLogger)

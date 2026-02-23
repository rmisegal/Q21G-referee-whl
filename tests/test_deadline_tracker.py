# Area: GMC
# PRD: docs/prd-rlgm.md
"""Tests for DeadlineTracker — player response timeout tracking."""

from unittest.mock import patch

import pytest

from q21_referee._gmc.deadline_tracker import DeadlineTracker


MOCK_TIME = "q21_referee._gmc.deadline_tracker.time"


class TestDeadlineTracker:
    """Unit tests for DeadlineTracker."""

    def test_no_deadlines_initially(self):
        tracker = DeadlineTracker()
        assert tracker.check_expired() == []

    def test_set_and_check_not_expired(self):
        tracker = DeadlineTracker()
        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 60)
            # Immediately check — still within deadline
            expired = tracker.check_expired()
            assert expired == []

    def test_set_and_check_expired(self):
        tracker = DeadlineTracker()
        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 40)

            # At 139s — not yet expired (deadline is 140)
            mock_time.monotonic.return_value = 139.0
            assert tracker.check_expired() == []

            # At 141s — expired (deadline was 140)
            mock_time.monotonic.return_value = 141.0
            expired = tracker.check_expired()
            assert len(expired) == 1
            assert expired[0]["phase"] == "warmup_sent"
            assert expired[0]["player_email"] == "p1@test.com"

    def test_cancel_removes_deadline(self):
        tracker = DeadlineTracker()
        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 30)

            tracker.cancel("p1@test.com")

            mock_time.monotonic.return_value = 200.0
            assert tracker.check_expired() == []

    def test_cancel_unknown_email_is_noop(self):
        tracker = DeadlineTracker()
        # Should not raise
        tracker.cancel("unknown@test.com")

    def test_clear_removes_all(self):
        tracker = DeadlineTracker()
        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 30)
            tracker.set_deadline("warmup_sent", "p2@test.com", 30)

            tracker.clear()

            mock_time.monotonic.return_value = 200.0
            assert tracker.check_expired() == []

    def test_multiple_players_one_expires(self):
        tracker = DeadlineTracker()
        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 20)
            tracker.set_deadline("warmup_sent", "p2@test.com", 60)

            # At 125s — only p1 expired (deadline 120), p2 still alive (160)
            mock_time.monotonic.return_value = 125.0
            expired = tracker.check_expired()
            assert len(expired) == 1
            assert expired[0]["player_email"] == "p1@test.com"

    def test_set_deadline_overwrites_previous(self):
        tracker = DeadlineTracker()
        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 20)

            # 10s later, overwrite with longer deadline
            mock_time.monotonic.return_value = 110.0
            tracker.set_deadline("warmup_sent", "p1@test.com", 60)

            # At 125s — old deadline (120) would have expired, but new (170) hasn't
            mock_time.monotonic.return_value = 125.0
            assert tracker.check_expired() == []

            # At 175s — new deadline (170) has expired
            mock_time.monotonic.return_value = 175.0
            expired = tracker.check_expired()
            assert len(expired) == 1
            assert expired[0]["player_email"] == "p1@test.com"

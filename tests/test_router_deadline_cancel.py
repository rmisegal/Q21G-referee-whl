# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for deadline cancellation on valid player response in handlers."""

from unittest.mock import Mock, patch, MagicMock

from q21_referee._gmc.deadline_tracker import DeadlineTracker
from q21_referee._gmc.router import MessageRouter
from q21_referee._gmc.state import GameState, GamePhase, PlayerState
from q21_referee._gmc.envelope_builder import EnvelopeBuilder

MOCK_TIME = "q21_referee._gmc.deadline_tracker.time"


def _make_router(phase=GamePhase.WARMUP_SENT):
    """Build a MessageRouter with real DeadlineTracker and minimal mocks."""
    ai = MagicMock()
    state = GameState(
        game_id="0101001",
        match_id="0101001",
        season_id="S01",
        league_id="Q21G",
        phase=phase,
        player1=PlayerState(email="p1@test.com", participant_id="P1"),
        player2=PlayerState(email="p2@test.com", participant_id="P2"),
    )
    builder = MagicMock(spec=EnvelopeBuilder)
    config = {"referee_email": "ref@test.com", "referee_id": "REF001",
              "league_id": "Q21G"}
    tracker = DeadlineTracker()
    router = MessageRouter(
        ai=ai, state=state, builder=builder, config=config,
        deadline_tracker=tracker,
    )
    return router, tracker


class TestRouterDeadlineCancel:
    """Deadline cancel happens in handler after phase validation, not in router."""

    def test_cancel_on_valid_warmup_response(self):
        """Warmup response in correct phase cancels deadline."""
        router, tracker = _make_router(phase=GamePhase.WARMUP_SENT)

        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup", "p1@test.com", 60)

            router.route(
                "Q21WARMUPRESPONSE",
                {"payload": {"answer": "4"}},
                "p1@test.com",
            )

            mock_time.monotonic.return_value = 200.0
            expired = tracker.check_expired()
            assert expired == []

    def test_no_cancel_for_unknown_sender(self):
        """Deadline for p1 must NOT be cancelled by unknown sender."""
        router, tracker = _make_router(phase=GamePhase.WARMUP_SENT)

        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup", "p1@test.com", 60)

            router.route(
                "Q21WARMUPRESPONSE",
                {"payload": {"answer": "4"}},
                "unknown@test.com",
            )

            mock_time.monotonic.return_value = 200.0
            expired = tracker.check_expired()
            assert len(expired) == 1
            assert expired[0]["player_email"] == "p1@test.com"

    def test_wrong_phase_does_not_cancel_deadline(self):
        """A message in the wrong phase must NOT cancel the deadline."""
        router, tracker = _make_router(phase=GamePhase.WARMUP_SENT)

        with patch(MOCK_TIME) as mock_time:
            mock_time.monotonic.return_value = 100.0
            tracker.set_deadline("warmup", "p1@test.com", 60)

            # Send a guess submission during WARMUP_SENT phase — wrong phase
            router.route(
                "Q21GUESSSUBMISSION",
                {"payload": {"book_title": "Moby Dick"}},
                "p1@test.com",
            )

            mock_time.monotonic.return_value = 200.0
            expired = tracker.check_expired()
            assert len(expired) == 1
            assert expired[0]["player_email"] == "p1@test.com"

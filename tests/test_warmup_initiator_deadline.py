# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for warmup_initiator deadline setting after sending warmup calls."""

from unittest.mock import patch, MagicMock

from q21_referee._rlgm.warmup_initiator import initiate_warmup
from q21_referee._rlgm.gprm import GPRM
from q21_referee._gmc.gmc import GameManagementCycle
from q21_referee.callbacks import RefereeAI


def _make_gprm():
    return GPRM(
        player1_email="p1@test.com", player1_id="P001",
        player2_email="p2@test.com", player2_id="P002",
        season_id="S01", game_id="0101001", match_id="0101001",
        round_id="ROUND_1", round_number=1,
    )


def _make_config(**overrides):
    cfg = {
        "referee_email": "ref@test.com",
        "referee_id": "REF001",
        "league_id": "LEAGUE001",
    }
    cfg.update(overrides)
    return cfg


def _make_ai():
    ai = MagicMock(spec=RefereeAI)
    ai.get_warmup_question.return_value = {"warmup_question": "Hello?"}
    return ai


class TestWarmupSetsDeadlines:
    """Verify warmup_initiator sets deadlines for active players."""

    def test_warmup_sets_deadline_for_each_active_player(self):
        """After initiate_warmup, both players should have deadlines set."""
        gprm = _make_gprm()
        config = _make_config()
        ai = _make_ai()
        gmc = GameManagementCycle(gprm, ai, config)

        # Use a real monotonic base so set_deadline records real values
        base_time = 1000.0
        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            initiate_warmup(gmc, gprm, ai, config)

            # Force expiry by advancing time far into the future
            mock_time.monotonic.return_value = 9999999.0
            expired = gmc.deadline_tracker.check_expired()

        assert len(expired) == 2
        expired_emails = {e["player_email"] for e in expired}
        assert expired_emails == {"p1@test.com", "p2@test.com"}
        assert all(e["phase"] == "warmup" for e in expired)

    def test_warmup_uses_config_timeout(self):
        """When config sets player_response_timeout_seconds=120, use it."""
        gprm = _make_gprm()
        config = _make_config(player_response_timeout_seconds=120)
        ai = _make_ai()
        gmc = GameManagementCycle(gprm, ai, config)

        base_time = 100.0
        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            initiate_warmup(gmc, gprm, ai, config)
            # expires_at = 100 + 120 = 220

            # At 219s (< 220 expiry) => not expired
            mock_time.monotonic.return_value = 219.0
            expired_early = gmc.deadline_tracker.check_expired()
            assert len(expired_early) == 0

            # At 221s (> 220 expiry) => expired
            mock_time.monotonic.return_value = 221.0
            expired_late = gmc.deadline_tracker.check_expired()
            assert len(expired_late) == 2

    def test_warmup_uses_default_timeout_when_not_configured(self):
        """Without config key, default timeout of 40s applies."""
        gprm = _make_gprm()
        config = _make_config()  # No player_response_timeout_seconds
        ai = _make_ai()
        gmc = GameManagementCycle(gprm, ai, config)

        base_time = 1000.0
        with patch("q21_referee._gmc.deadline_tracker.time") as mock_time:
            mock_time.monotonic.return_value = base_time
            initiate_warmup(gmc, gprm, ai, config)

            # At base + 141s (> 40s default) => expired
            mock_time.monotonic.return_value = base_time + 141.0
            expired = gmc.deadline_tracker.check_expired()

        assert len(expired) == 2
        assert all(e["phase"] == "warmup" for e in expired)

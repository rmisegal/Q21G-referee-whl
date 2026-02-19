# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for EnvelopeBuilder match result with abort fields."""

from q21_referee._gmc.envelope_builder import EnvelopeBuilder


class TestEnvelopeBuilderMatchResult:
    """Tests for build_match_result with abort support."""

    def create_builder(self):
        return EnvelopeBuilder(
            referee_email="ref@test.com",
            referee_id="REF001",
            league_id="LEAGUE001",
            season_id="S01",
        )

    def test_match_result_defaults_to_completed(self):
        """Test that match result defaults to completed status."""
        builder = self.create_builder()
        env, subject = builder.build_match_result(
            game_id="0101001", match_id="R1M1",
            round_id="ROUND_1", winner_id="P001",
            is_draw=False, scores=[],
        )
        assert env["payload"]["status"] == "completed"
        assert "abort_reason" not in env["payload"]
        assert "player_states" not in env["payload"]

    def test_match_result_aborted(self):
        """Test that match result includes abort fields."""
        builder = self.create_builder()
        player_states = {
            "player1": {
                "phase_reached": "warmup_answered",
                "scored": False,
                "last_actor": "P001",
            },
            "player2": {
                "phase_reached": "idle",
                "scored": False,
                "last_actor": "referee",
            },
        }
        env, subject = builder.build_match_result(
            game_id="0101001", match_id="R1M1",
            round_id="ROUND_1", winner_id=None,
            is_draw=True, scores=[],
            status="aborted",
            abort_reason="new_round_started",
            player_states=player_states,
        )
        assert env["payload"]["status"] == "aborted"
        assert env["payload"]["abort_reason"] == "new_round_started"
        assert env["payload"]["player_states"]["player1"]["last_actor"] == "P001"

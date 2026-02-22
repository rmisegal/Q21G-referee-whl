# Area: GMC Tests
# PRD: docs/prd-rlgm.md
"""Tests for EnvelopeBuilder — match result, abort fields, falsy guards."""

from q21_referee._gmc.envelope_builder import EnvelopeBuilder


def make_builder():
    return EnvelopeBuilder("ref@test.com", "REF001", "L01", "S01")


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


class TestEnvelopeBuilderFalsyFields:
    """Test that falsy but valid values are included."""

    def test_empty_feedback_included(self):
        """Empty string feedback should be in score envelope."""
        builder = make_builder()
        env, _ = builder.build_score_feedback(
            player_id="P001", game_id="0101001", match_id="M01",
            league_points=0, private_score=0.0, breakdown={},
            feedback="",
        )
        assert "feedback" in env["payload"]
        assert env["payload"]["feedback"] == ""

    def test_none_feedback_excluded(self):
        """None feedback should NOT be in score envelope."""
        builder = make_builder()
        env, _ = builder.build_score_feedback(
            player_id="P001", game_id="0101001", match_id="M01",
            league_points=0, private_score=0.0, breakdown={},
            feedback=None,
        )
        assert "feedback" not in env["payload"]

    def test_empty_correlation_id_in_q21(self):
        """Empty correlation_id should be in Q21 envelope."""
        builder = make_builder()
        env = builder._base_q21_envelope(
            "TEST", "P001", "0101001", "msg1", correlation_id="")
        assert "correlation_id" in env

    def test_empty_round_id_in_league(self):
        """Empty round_id should be in league envelope."""
        builder = make_builder()
        env = builder._base_league_envelope(
            "TEST", "LM", "msg1", round_id="")
        assert "round_id" in env

    def test_empty_game_id_in_league(self):
        """Empty game_id should be in league envelope."""
        builder = make_builder()
        env = builder._base_league_envelope(
            "TEST", "LM", "msg1", game_id="")
        assert "game_id" in env

    def test_empty_correlation_id_in_league(self):
        """Empty correlation_id should be in league envelope."""
        builder = make_builder()
        env = builder._base_league_envelope(
            "TEST", "LM", "msg1", correlation_id="")
        assert "correlation_id" in env

    def test_empty_abort_reason_included(self):
        """Empty string abort_reason should be in match result."""
        builder = make_builder()
        env, _ = builder.build_match_result(
            game_id="0101001", match_id="M01", round_id="R01",
            winner_id="P001", is_draw=False, scores=[],
            abort_reason="",
        )
        assert "abort_reason" in env["payload"]
        assert env["payload"]["abort_reason"] == ""

    def test_empty_player_states_included(self):
        """Empty dict player_states should be in match result."""
        builder = make_builder()
        env, _ = builder.build_match_result(
            game_id="0101001", match_id="M01", round_id="R01",
            winner_id="P001", is_draw=False, scores=[],
            player_states={},
        )
        assert "player_states" in env["payload"]
        assert env["payload"]["player_states"] == {}

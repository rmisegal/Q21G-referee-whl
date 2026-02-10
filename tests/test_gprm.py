# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for GPRM (Game Parameters) dataclass."""

import pytest
from q21_referee._rlgm.gprm import GPRM


class TestGPRM:
    """Tests for GPRM dataclass."""

    def test_gprm_creation(self):
        """Test that GPRM can be created with all fields."""
        gprm = GPRM(
            player1_email="player1@test.com",
            player1_id="P001",
            player2_email="player2@test.com",
            player2_id="P002",
            season_id="SEASON_2026_Q1",
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            round_number=1,
        )
        assert gprm.player1_email == "player1@test.com"
        assert gprm.player1_id == "P001"
        assert gprm.player2_email == "player2@test.com"
        assert gprm.player2_id == "P002"
        assert gprm.season_id == "SEASON_2026_Q1"
        assert gprm.game_id == "0101001"
        assert gprm.match_id == "R1M1"
        assert gprm.round_id == "ROUND_1"
        assert gprm.round_number == 1

    def test_gprm_all_fields_required(self):
        """Test that GPRM requires all 9 fields."""
        with pytest.raises(TypeError):
            # Missing fields should raise TypeError
            GPRM(player1_email="test@test.com")

    def test_gprm_equality(self):
        """Test that two GPRMs with same values are equal."""
        gprm1 = GPRM(
            player1_email="a@test.com",
            player1_id="P001",
            player2_email="b@test.com",
            player2_id="P002",
            season_id="S1",
            game_id="G1",
            match_id="M1",
            round_id="R1",
            round_number=1,
        )
        gprm2 = GPRM(
            player1_email="a@test.com",
            player1_id="P001",
            player2_email="b@test.com",
            player2_id="P002",
            season_id="S1",
            game_id="G1",
            match_id="M1",
            round_id="R1",
            round_number=1,
        )
        assert gprm1 == gprm2

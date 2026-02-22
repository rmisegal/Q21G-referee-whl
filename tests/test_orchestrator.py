# Area: RLGM Tests
# PRD: docs/prd-rlgm.md
"""Tests for RLGM Orchestrator."""

import pytest
from unittest.mock import Mock, MagicMock
from q21_referee._rlgm.orchestrator import RLGMOrchestrator
from q21_referee._rlgm.gprm import GPRM
from q21_referee._rlgm.enums import RLGMState, RLGMEvent
from q21_referee.callbacks import RefereeAI


class MockRefereeAI(RefereeAI):
    """Mock AI for testing."""

    def get_warmup_question(self, ctx):
        return {"warmup_question": "What is 2+2?"}

    def get_round_start_info(self, ctx):
        return {"book_name": "Test", "book_hint": "A test", "association_word": "test"}

    def get_answers(self, ctx):
        return {"answers": ["A", "B", "C"]}

    def get_score_feedback(self, ctx):
        return {"league_points": 10, "private_score": 5.0, "breakdown": {}}


class TestRLGMOrchestrator:
    """Tests for RLGMOrchestrator class."""

    def create_config(self):
        """Create sample config."""
        return {
            "referee_id": "REF001",
            "referee_email": "ref@test.com",
            "group_id": "GROUP_A",
            "league_id": "LEAGUE001",
            "season_id": "SEASON_2026_Q1",
            "game_id": "0101001",
            "league_manager_email": "lm@test.com",
        }

    def test_initial_state(self):
        """Test orchestrator starts in INIT state."""
        config = self.create_config()
        ai = MockRefereeAI()

        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        assert orchestrator.state_machine.current_state == RLGMState.INIT_START_STATE
        assert orchestrator.current_game is None

    def test_handle_start_season(self):
        """Test handling BROADCAST_START_SEASON message."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        message = {
            "message_type": "BROADCAST_START_SEASON",
            "broadcast_id": "BC001",
            "payload": {"season_id": "SEASON_2026_Q1", "league_id": "LEAGUE001"},
        }

        result = orchestrator.handle_lm_message(message)

        assert orchestrator.state_machine.current_state == RLGMState.WAITING_FOR_CONFIRMATION
        assert result is not None
        assert result["message_type"] == "SEASON_REGISTRATION_REQUEST"

    def test_start_game_creates_gmc(self):
        """Test that start_game creates a GMC instance."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        gprm = GPRM(
            player1_email="p1@test.com",
            player1_id="P001",
            player2_email="p2@test.com",
            player2_id="P002",
            season_id="SEASON_2026_Q1",
            game_id="0101001",
            match_id="R1M1",
            round_id="ROUND_1",
            round_number=1,
        )

        orchestrator.start_game(gprm)

        assert orchestrator.current_game is not None
        assert orchestrator.current_game.gprm == gprm

    def test_route_player_message_no_handler(self):
        """Test routing player message with no matching handler returns empty."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        gprm = GPRM(
            player1_email="p1@test.com", player1_id="P001",
            player2_email="p2@test.com", player2_id="P002",
            season_id="SEASON_2026_Q1", game_id="0101001",
            match_id="R1M1", round_id="ROUND_1", round_number=1,
        )
        orchestrator.start_game(gprm)

        outgoing = orchestrator.route_player_message(
            "UNKNOWN_TYPE", {}, "p1@test.com"
        )
        assert outgoing == []

    def test_no_game_returns_empty(self):
        """Test routing when no game is active returns empty."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        outgoing = orchestrator.route_player_message(
            "Q21WARMUPRESPONSE", {}, "p1@test.com"
        )

        assert outgoing == []

    def test_handle_new_round_uses_start_round(self):
        """Test that handle_lm_message for new round calls start_round."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        # Set up assignments
        orchestrator._assignments = [{
            "round_number": 1,
            "game_id": "0101001",
            "player1_email": "p1@test.com",
            "player1_id": "P001",
            "player2_email": "p2@test.com",
            "player2_id": "P002",
        }]
        orchestrator._new_round_handler.assignments = orchestrator._assignments
        # Get state machine to RUNNING
        orchestrator.state_machine.transition(RLGMEvent.SEASON_START)
        orchestrator.state_machine.transition(RLGMEvent.REGISTRATION_ACCEPTED)
        orchestrator.state_machine.transition(RLGMEvent.ASSIGNMENT_RECEIVED)

        message = {
            "message_type": "BROADCAST_NEW_LEAGUE_ROUND",
            "broadcast_id": "BC003",
            "payload": {"round_number": 1, "round_id": "ROUND_1"},
        }

        result = orchestrator.handle_lm_message(message)

        assert result is None
        assert orchestrator.current_game is not None
        assert orchestrator.current_round_number == 1
        pending = orchestrator.get_pending_outgoing()
        assert len(pending) == 2  # warmup calls

    def test_keep_alive_handler_registered(self):
        """Issue #2: BroadcastKeepAliveHandler must be registered."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        handler = orchestrator.router.get_handler("BROADCAST_KEEP_ALIVE")
        assert handler is not None

    def test_critical_pause_handler_registered(self):
        """Issue #3: BroadcastCriticalPauseHandler must be registered."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        handler = orchestrator.router.get_handler("BROADCAST_CRITICAL_PAUSE")
        assert handler is not None

    def test_critical_reset_handler_registered(self):
        """Issue #3: BroadcastCriticalResetHandler must be registered."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        handler = orchestrator.router.get_handler("BROADCAST_CRITICAL_RESET")
        assert handler is not None

    def test_round_results_handler_registered(self):
        """Issue #4: BroadcastRoundResultsHandler must be registered."""
        config = self.create_config()
        ai = MockRefereeAI()
        orchestrator = RLGMOrchestrator(config=config, ai=ai)

        handler = orchestrator.router.get_handler("BROADCAST_ROUND_RESULTS")
        assert handler is not None

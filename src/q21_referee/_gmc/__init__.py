# Area: GMC
# PRD: docs/prd-rlgm.md
"""
GMC (Game Management Cycle) - Single-game execution engine.

This package handles:
- Player message routing
- Game state management
- Callback invocation
- Player score tracking
- Match result generation
"""

from .state import GameState, GamePhase, PlayerState
from .envelope_builder import EnvelopeBuilder
from .context_builder import ContextBuilder, SERVICE_DEFINITIONS
from .callback_executor import execute_callback
from .router import MessageRouter
from .validator import validate_output
from .gmc import GameManagementCycle

__all__ = [
    "GameState",
    "GamePhase",
    "PlayerState",
    "EnvelopeBuilder",
    "ContextBuilder",
    "SERVICE_DEFINITIONS",
    "execute_callback",
    "MessageRouter",
    "validate_output",
    "GameManagementCycle",
]

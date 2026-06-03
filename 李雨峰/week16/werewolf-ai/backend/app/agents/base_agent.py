"""Abstract base class for game agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.models.game_state import GamePhase, GameState, PlayerRole
from app.models.messages import AgentAction


class BaseAgent(ABC):
    """
    Abstract base class for all game agents (AI and human proxy).

    Each agent type implements its own decision logic based on role,
    game state, and available information.
    """

    def __init__(self, player_id: str, name: str, role: PlayerRole):
        self.player_id = player_id
        self.name = name
        self.role = role
        self.is_alive = True

    @abstractmethod
    async def decide(
        self,
        game_state: GameState,
        phase: GamePhase,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentAction:
        """
        Make a decision based on the current game state.

        Args:
            game_state: Current state of the game (may be partial/hide info).
            phase: Current game phase.
            context: Additional context (e.g., discussion messages, death info).

        Returns:
            AgentAction with the decision made.
        """
        ...

    @abstractmethod
    async def speak(
        self,
        game_state: GameState,
        phase: GamePhase,
        discussion_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Generate a speaking message for the discussion phase.

        Args:
            game_state: Current game state visible to this agent.
            phase: Current phase (should be DISCUSSION).
            discussion_history: Previous messages in this discussion round.

        Returns:
            String containing the agent's spoken message.
        """
        ...

    def update_state(self, game_state: GameState) -> None:
        """Update internal state when game state changes."""
        player = game_state.get_player(self.player_id)
        if player:
            self.is_alive = player.is_alive

    def _get_visible_game_state(self, full_state: GameState) -> GameState:
        """
        Create a filtered game state that only shows information
        this agent is allowed to know.
        """
        # Default: hide other players' roles
        return full_state

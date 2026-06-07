"""Human player proxy agent."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import structlog

from app.agents.base_agent import BaseAgent
from app.models.game_state import GamePhase, GameState, PlayerRole
from app.models.messages import AgentAction

logger = structlog.get_logger()


class HumanProxyAgent(BaseAgent):
    """
    Proxy agent that forwards a human player's decisions to the game engine.

    This agent doesn't make its own decisions — instead, it waits for
    the human player to submit their action via WebSocket.
    """

    def __init__(self, player_id: str, name: str, role: PlayerRole):
        super().__init__(player_id, name, role)
        self._pending_action: Optional[AgentAction] = None
        self._pending_speech: Optional[str] = None
        self._action_event = asyncio.Event()
        self._speech_event = asyncio.Event()

    def submit_action(self, action: AgentAction) -> None:
        """Submit an action on behalf of the human player."""
        self._pending_action = action
        self._action_event.set()

    def submit_speech(self, text: str) -> None:
        """Submit speech on behalf of the human player."""
        self._pending_speech = text
        self._speech_event.set()

    async def decide(
        self,
        game_state: GameState,
        phase: GamePhase,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentAction:
        """Wait for the human player to submit an action."""
        self._action_event.clear()
        self._pending_action = None

        logger.info(
            "Waiting for human decision",
            player_id=self.player_id,
            phase=phase.value,
        )

        # Wait for the human to submit (with timeout)
        try:
            await asyncio.wait_for(self._action_event.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            logger.warning("Human player timed out, skipping action", player_id=self.player_id)
            return AgentAction(
                action_type="skip",
                reasoning="Timed out waiting for human decision",
            )

        if self._pending_action is None:
            return AgentAction(
                action_type="skip",
                reasoning="No action submitted",
            )

        action = self._pending_action
        self._pending_action = None
        return action

    async def speak(
        self,
        game_state: GameState,
        phase: GamePhase,
        discussion_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Wait for the human player to submit speech."""
        self._speech_event.clear()
        self._pending_speech = None

        logger.info("Waiting for human speech", player_id=self.player_id)

        try:
            await asyncio.wait_for(self._speech_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            return "[Player is thinking...]"

        if self._pending_speech is None:
            return "[No response]"

        text = self._pending_speech
        self._pending_speech = None
        return text

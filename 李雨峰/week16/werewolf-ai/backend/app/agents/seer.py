"""Seer AI Agent."""

from __future__ import annotations

from typing import Any, Optional

import structlog

from app.agents.base_agent import BaseAgent
from app.llm.client import llm_client
from app.models.game_state import GamePhase, GameState, PlayerRole
from app.models.messages import AgentAction

logger = structlog.get_logger()


class SeerAgent(BaseAgent):
    """AI agent playing the seer role."""

    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, PlayerRole.SEER)
        self.inspection_history: list[dict[str, Any]] = []

    async def decide(
        self,
        game_state: GameState,
        phase: GamePhase,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentAction:
        if phase != GamePhase.SEER_TURN:
            return AgentAction(action_type="skip", reasoning="Not seer turn")

        game_info = self._build_game_info(game_state)

        action = await llm_client.generate_action(
            role="seer",
            game_state_info=game_info,
            phase=phase.value,
            context=context,
        )

        logger.info(
            "Seer decision",
            player_id=self.player_id,
            action=action.action_type.value,
            target=action.target_id,
        )

        return action

    async def speak(
        self,
        game_state: GameState,
        phase: GamePhase,
        discussion_history: list[dict[str, str]] | None = None,
    ) -> str:
        game_info = self._build_game_info(game_state)
        return await llm_client.generate_speech(
            role="seer",
            game_state_info=game_info,
            discussion_history=discussion_history,
        )

    def record_inspection(self, target_id: str, is_werewolf: bool) -> None:
        """Record the result of an inspection."""
        self.inspection_history.append({"target": target_id, "is_werewolf": is_werewolf})

    def _build_game_info(self, game_state: GameState) -> dict[str, Any]:
        alive_players = [
            p for p in game_state.get_alive_players() if p.player_id != self.player_id
        ]
        dead_players = [p for p in game_state.players.values() if not p.is_alive]

        # Don't re-inspect known players
        known_targets = {r["target"] for r in self.inspection_history}
        valid_targets = [
            p.player_id
            for p in alive_players
            if p.player_id not in known_targets
        ]

        return {
            "player_id": self.player_id,
            "day": game_state.day_number,
            "alive_players": [p.player_id for p in alive_players],
            "dead_players": [p.player_id for p in dead_players],
            "inspection_history": self.inspection_history,
            "valid_targets": valid_targets or [p.player_id for p in alive_players],
        }

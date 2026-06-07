"""Villager AI Agent."""

from __future__ import annotations

from typing import Any, Optional

import structlog

from app.agents.base_agent import BaseAgent
from app.llm.client import llm_client
from app.models.game_state import GamePhase, GameState, PlayerRole
from app.models.messages import AgentAction

logger = structlog.get_logger()


class VillagerAgent(BaseAgent):
    """AI agent playing the villager role."""

    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, PlayerRole.VILLAGER)

    async def decide(
        self,
        game_state: GameState,
        phase: GamePhase,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentAction:
        if phase != GamePhase.VOTING:
            return AgentAction(action_type="skip", reasoning="Not voting phase")

        game_info = self._build_game_info(game_state)

        action = await llm_client.generate_action(
            role="villager",
            game_state_info=game_info,
            phase=phase.value,
            context=context,
        )

        logger.info(
            "Villager vote",
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
            role="villager",
            game_state_info=game_info,
            discussion_history=discussion_history,
        )

    def _build_game_info(self, game_state: GameState) -> dict[str, Any]:
        alive_players = [
            p for p in game_state.get_alive_players() if p.player_id != self.player_id
        ]
        dead_players = [p for p in game_state.players.values() if not p.is_alive]

        return {
            "player_id": self.player_id,
            "day": game_state.day_number,
            "alive_players": [p.player_id for p in alive_players],
            "dead_players": [p.player_id for p in dead_players],
            "valid_targets": [p.player_id for p in alive_players],
        }

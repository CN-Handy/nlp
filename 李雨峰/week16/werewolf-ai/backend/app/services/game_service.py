"""Game service: manages game lifecycle, agent creation, and engine orchestration."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import structlog

from app.agents.base_agent import BaseAgent
from app.agents.hunter import HunterAgent
from app.agents.human_proxy import HumanProxyAgent
from app.agents.seer import SeerAgent
from app.agents.villager import VillagerAgent
from app.agents.werewolf import WerewolfAgent
from app.agents.witch import WitchAgent
from app.core.events import create_generic_event
from app.core.game_engine import GameEngine
from app.core.rules import assign_roles, check_win_condition
from app.models.events import GameEvent
from app.models.game_state import GamePhase, GameState, Player, PlayerRole
from app.services.room_service import room_service
from app.ws.manager import ws_manager

logger = structlog.get_logger()


class GameService:
    """
    Service that manages game instances, agents, and the game engine.

    Creates agents, initializes the game engine, and coordinates
    the game loop.
    """

    def __init__(self):
        self._games: dict[str, GameState] = {}
        self._engines: dict[str, GameEngine] = {}
        self._agents: dict[str, dict[str, BaseAgent]] = {}  # game_id -> {player_id -> agent}

    def create_game(self, room_id: str) -> GameState:
        """Create a new game state for a room."""
        from app.utils.id_gen import generate_id

        game_id = generate_id()
        game_state = GameState(
            game_id=game_id,
            room_id=room_id,
            phase=GamePhase.WAITING,
        )

        self._games[game_id] = game_state
        self._agents[game_id] = {}

        logger.info("Game created", game_id=game_id, room_id=room_id)
        return game_state

    def get_game(self, game_id: str) -> Optional[GameState]:
        """Get game state by ID."""
        return self._games.get(game_id)

    def get_game_by_room(self, room_id: str) -> Optional[GameState]:
        """Find game by room ID."""
        for game in self._games.values():
            if game.room_id == room_id:
                return game
        return None

    def initialize_agents(self, game_id: str, human_player_ids: list[str]) -> None:
        """
        Create agents for all players in the game.
        Human players get HumanProxyAgent, AI players get role-specific agents.
        """
        game_state = self._games.get(game_id)
        if not game_state:
            raise ValueError(f"Game {game_id} not found")

        room = room_service.get_room(game_state.room_id)
        if not room:
            raise ValueError(f"Room {game_state.room_id} not found")

        # Assign roles
        role_dist = game_state.get_role_distribution(len(room.player_ids))
        role_assignment = assign_roles(room.player_ids, role_dist)

        # Create agents
        agents: dict[str, BaseAgent] = {}
        for player_id, role in role_assignment.items():
            is_human = player_id in human_player_ids
            player = Player(
                player_id=player_id,
                name=f"Player_{player_id[:6]}",
                role=role,
                is_human=is_human,
            )
            if role == PlayerRole.HUNTER:
                player.can_shoot_on_death = True
            game_state.players[player_id] = player

            if is_human:
                agent: BaseAgent = HumanProxyAgent(
                    player_id=player_id,
                    name=player.name,
                    role=role,
                )
            else:
                agent = self._create_ai_agent(player_id, player.name, role, room, role_assignment)

            agents[player_id] = agent

        self._agents[game_id] = agents
        logger.info(
            "Agents initialized",
            game_id=game_id,
            agent_count=len(agents),
            human_count=len(human_player_ids),
        )

    def _create_ai_agent(
        self,
        player_id: str,
        name: str,
        role: PlayerRole,
        room,
        role_assignment: dict[str, PlayerRole],
    ) -> BaseAgent:
        """Create an AI agent for the given role."""
        match role:
            case PlayerRole.WEREWOLF:
                teammates = [
                    pid for pid, r in role_assignment.items()
                    if r == PlayerRole.WEREWOLF and pid != player_id
                ]
                return WerewolfAgent(player_id, name, teammates)
            case PlayerRole.SEER:
                return SeerAgent(player_id, name)
            case PlayerRole.WITCH:
                return WitchAgent(player_id, name)
            case PlayerRole.HUNTER:
                return HunterAgent(player_id, name)
            case _:
                return VillagerAgent(player_id, name)

    async def start_game(self, game_id: str) -> None:
        """Start the game engine and run the game loop."""
        game_state = self._games.get(game_id)
        if not game_state:
            raise ValueError(f"Game {game_id} not found")

        # Speech callback: called by engine during discussion to get agent speech
        async def get_speech(state, speaker_id):
            agents = self._agents.get(game_id, {})
            agent = agents.get(speaker_id)
            if agent:
                return await agent.speak(state, state.phase)
            return "(沉默)"

        engine = GameEngine(game_state, speech_callback=get_speech)
        engine.on_event(self._on_game_event)
        self._engines[game_id] = engine

        # Broadcast game started
        await ws_manager.broadcast_to_room(
            game_state.room_id,
            {
                "type": "game_state",
                "data": {"phase": "started", "game_id": game_id},
            },
        )

        # Start game in background
        asyncio.create_task(self._run_game(engine, game_id))

    async def _run_game(self, engine: GameEngine, game_id: str) -> None:
        """Run the game engine loop."""
        try:
            await engine.start_game()
        except Exception:
            logger.exception("Game engine error", game_id=game_id)
        finally:
            game_state = self._games.get(game_id)
            if game_state:
                await ws_manager.broadcast_to_room(
                    game_state.room_id,
                    {
                        "type": "game_over",
                        "data": {
                            "winner": game_state.winner,
                            "game_id": game_id,
                        },
                    },
                )

    def _on_game_event(self, event: GameEvent) -> None:
        """Handle events from the game engine and broadcast them."""
        game_state = self._games.get(event.game_id)
        if not game_state:
            return

        # Build actor/target names
        actor_name = None
        actor_role = None
        if event.actor_id and event.actor_id in game_state.players:
            p = game_state.players[event.actor_id]
            actor_name = p.name
            actor_role = p.role.value if p.role else None

        target_name = None
        target_role = None
        if event.target_id and event.target_id in game_state.players:
            p = game_state.players[event.target_id]
            target_name = p.name
            target_role = p.role.value if p.role else None

        # Enrich event data based on type
        extra_data = event.data or {}
        event_type = event.event_type.value

        if event_type == "death":
            # Include killed player's role and death info
            extra_data = {**extra_data}
            if event.target_id and event.target_id in game_state.players:
                dead_player = game_state.players[event.target_id]
                extra_data["target_role"] = dead_player.role.value if dead_player.role else None
                extra_data["target_name"] = target_name

        elif event_type == "speak":
            # Ensure text is included
            extra_data = {**extra_data}
            extra_data["actor_name"] = actor_name

        elif event_type == "vote_result":
            extra_data = {**extra_data}
            if event.target_id and event.target_id in game_state.players:
                extra_data["target_name"] = target_name
                extra_data["target_role"] = game_state.players[event.target_id].role.value if game_state.players[event.target_id].role else None

        elif event_type == "witch_heal":
            extra_data = {**extra_data, "description": "女巫使用了解药"}
        elif event_type == "witch_poison":
            extra_data = {**extra_data, "description": "女巫使用了毒药"}
        elif event_type == "seer_inspect":
            extra_data = {**extra_data, "result": extra_data.get("is_werewolf", False)}

        # Build spectator-friendly event payload
        event_payload = {
            "type": "game_event",
            "data": {
                "event_type": event_type,
                "game_id": event.game_id,
                "phase": game_state.phase.value,
                "day_number": game_state.day_number,
                "actor_id": event.actor_id,
                "actor_name": actor_name,
                "actor_role": actor_role,
                "target_id": event.target_id,
                "target_name": target_name,
                "target_role": target_role,
                "data": extra_data,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            },
        }

        # Record event in game state log for spectator replay
        game_state.event_log.append(event_payload["data"])

        # Broadcast to all players and spectators in the room
        asyncio.create_task(
            ws_manager.broadcast_to_room(
                game_state.room_id,
                event_payload,
            )
        )

        logger.info(
            "Game event",
            event_type=event.event_type.value,
            game_id=event.game_id,
            actor_id=event.actor_id,
        )

    async def submit_human_action(
        self, game_id: str, player_id: str, action_data: dict[str, Any]
    ) -> bool:
        """Submit a human player's action to the game engine."""
        engine = self._engines.get(game_id)
        if not engine:
            return False

        # Submit to engine
        result = await engine.submit_action(player_id, action_data)

        # Also notify the agent
        agents = self._agents.get(game_id, {})
        agent = agents.get(player_id)
        if isinstance(agent, HumanProxyAgent):
            from app.models.messages import AgentAction, AgentActionType
            action = AgentAction(
                action_type=AgentActionType(action_data.get("action_type", "skip")),
                target_id=action_data.get("target_id"),
                reasoning=action_data.get("reasoning", ""),
                speak_text=action_data.get("speak_text"),
            )
            agent.submit_action(action)

        return result

    async def submit_human_speech(self, game_id: str, player_id: str, text: str) -> bool:
        """Submit a human player's speech."""
        agents = self._agents.get(game_id, {})
        agent = agents.get(player_id)
        if isinstance(agent, HumanProxyAgent):
            agent.submit_speech(text)
            return True
        return False

    async def run_agent_decisions(self, game_id: str) -> None:
        """
        Trigger all agent decisions for the current phase.
        Called by the game engine when it's time for agents to act.
        """
        game_state = self._games.get(game_id)
        engine = self._engines.get(game_id)
        agents = self._agents.get(game_id, {})

        if not game_state or not engine:
            return

        # Collect decisions from AI agents
        for player_id, agent in agents.items():
            if isinstance(agent, HumanProxyAgent):
                continue  # Wait for human to submit

            player = game_state.get_player(player_id)
            if not player or not player.is_alive:
                continue

            if not self._can_agent_act(agent, game_state.phase):
                continue

            # Run decision in background
            asyncio.create_task(self._run_single_agent_decision(game_id, player_id, agent))

    async def _run_single_agent_decision(
        self, game_id: str, player_id: str, agent: BaseAgent
    ) -> None:
        """Run a single agent's decision."""
        game_state = self._games.get(game_id)
        engine = self._engines.get(game_id)

        if not game_state or not engine:
            return

        try:
            action = await agent.decide(game_state, game_state.phase)
            await engine.submit_action(player_id, {
                "action_type": action.action_type.value,
                "target_id": action.target_id,
                "reasoning": action.reasoning,
            })
        except Exception:
            logger.exception("Agent decision error", player_id=player_id, game_id=game_id)

    def _can_agent_act(self, agent: BaseAgent, phase: GamePhase) -> bool:
        """Check if the agent can act in the current phase."""
        from app.core.rules import can_act

        player = Player(player_id=agent.player_id, name=agent.name, role=agent.role)
        return can_act(player, phase)

    def get_game_state_for_player(self, game_id: str, player_id: str) -> dict[str, Any]:
        """Get a filtered game state visible to a specific player."""
        game_state = self._games.get(game_id)
        if not game_state:
            return {}

        player = game_state.get_player(player_id)
        if not player:
            return {}

        # Build visible state
        visible_players = {}
        for pid, p in game_state.players.items():
            if pid == player_id:
                # Own player sees everything about themselves
                visible_players[pid] = p.model_dump()
            elif not p.is_alive:
                # Dead players' roles are revealed
                visible_players[pid] = p.model_dump()
            elif player.role == PlayerRole.WEREWOLF and p.role == PlayerRole.WEREWOLF:
                # Werewolves see each other
                visible_players[pid] = p.model_dump()
            else:
                # Hide role for alive players
                p_copy = p.model_dump()
                p_copy["role"] = None
                visible_players[pid] = p_copy

        return {
            "game_id": game_state.game_id,
            "phase": game_state.phase.value,
            "day_number": game_state.day_number,
            "players": visible_players,
            "deaths_today": game_state.deaths_today,
            "all_deaths": game_state.all_deaths,
            "current_speaker_id": game_state.current_speaker_id,
        }


# Singleton
game_service = GameService()

"""Core game engine - state machine driving game flow."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

import structlog

from app.core.events import (
    create_death_event,
    create_generic_event,
    create_phase_change_event,
    create_vote_event,
)
from app.core.phases import get_next_phase, is_decision_phase, is_night_phase
from app.core.rules import (
    assign_roles,
    can_act,
    check_win_condition,
    resolve_night_actions,
    resolve_votes,
)
from app.models.events import GameEvent
from app.models.game_state import (
    GamePhase,
    GameState,
    NightAction,
    Player,
    PlayerRole,
    VoteRecord,
)

logger = structlog.get_logger()


class GameEngine:
    """
    State machine that drives the werewolf game flow.

    The engine manages phase transitions, collects actions from agents,
    resolves outcomes, and emits events.
    """

    def __init__(self, game_state: GameState, speech_callback=None):
        self.state = game_state
        self._event_handlers: list[Callable[[GameEvent], None]] = []
        self._running = False
        self._phase_complete = asyncio.Event()
        # Optional async callback: (game_state, speaker_id) -> speech_text
        self._speech_callback = speech_callback

    def on_event(self, handler: Callable[[GameEvent], None]) -> None:
        """Register an event handler."""
        self._event_handlers.append(handler)

    def _emit_event(self, event: GameEvent) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Error in event handler", event_type=event.event_type)

    async def _transition_to(self, new_phase: GamePhase) -> None:
        """Transition to a new game phase and emit event."""
        old_phase = self.state.phase
        self.state.phase = new_phase

        event = create_phase_change_event(
            self.state.game_id,
            from_phase=old_phase.value,
            to_phase=new_phase.value,
        )
        self._emit_event(event)
        logger.info(
            "Phase transition",
            game_id=self.state.game_id,
            from_phase=old_phase.value,
            to_phase=new_phase.value,
        )

    async def start_game(self) -> None:
        """Initialize and start the game."""
        if self.state.phase != GamePhase.WAITING:
            raise RuntimeError("Game already started")

        self._running = True

        # Emit game start event with player info
        players_info = [
            {
                "id": p.player_id,
                "name": p.name,
                "role": None,  # Hidden at start
                "is_alive": True,
            }
            for p in self.state.players.values()
        ]
        start_event = create_generic_event(
            self.state.game_id,
            event_type="game_start",
            data={"player_count": len(self.state.players), "players": players_info},
        )
        self._emit_event(start_event)

        # Start first night
        await self._transition_to(GamePhase.NIGHT_START)
        await self._run_night_start()

    async def _run_night_start(self) -> None:
        """Night start: increment day, reset nightly state."""
        self.state.day_number += 1
        self.state.night_actions = []
        self.state.night_kill_targets = []
        self.state.votes = []
        self.state.deaths_today = []
        self.state.speak_index = 0

        # Set speaking order (randomized among alive players)
        import random

        alive_ids = [p.player_id for p in self.state.get_alive_players()]
        random.shuffle(alive_ids)
        self.state.speaking_order = alive_ids

        await self._transition_to(GamePhase.WEREWOLF_TURN)
        await self._run_werewolf_turn()

    async def _run_werewolf_turn(self) -> None:
        """Werewolf kill phase."""
        await self._collect_werewolf_actions()
        await self._transition_to(GamePhase.SEER_TURN)
        await self._run_seer_turn()

    async def _run_seer_turn(self) -> None:
        """Seer inspection phase."""
        await self._collect_seer_actions()
        await self._transition_to(GamePhase.WITCH_TURN)
        await self._run_witch_turn()

    async def _run_witch_turn(self) -> None:
        """Witch potion phase."""
        await self._collect_witch_actions()
        await self._transition_to(GamePhase.NIGHT_END)
        await self._run_night_end()

    async def _run_night_end(self) -> None:
        """Resolve night actions and announce deaths."""
        # Resolve kills, heals, and poison
        deaths = resolve_night_actions(self.state)

        # Apply deaths
        for player_id in deaths:
            player = self.state.get_player(player_id)
            if player and player.is_alive:
                player.is_alive
                if player.role == PlayerRole.HUNTER:
                    player.can_shoot_on_death = True
                player.is_alive = False
                self.state.deaths_today.append(player_id)
                self.state.all_deaths.append(player_id)

                death_event = create_death_event(
                    self.state.game_id,
                    target_id=player_id,
                    killed_by="werewolf",
                    is_night_death=True,
                )
                self._emit_event(death_event)

        # Check for witch poison deaths separately
        if self.state.witch_poison_target:
            poison_event = create_generic_event(
                self.state.game_id,
                event_type="witch_poison",
                target_id=self.state.witch_poison_target,
            )
            self._emit_event(poison_event)

        # Check win condition
        winner = check_win_condition(self.state)
        if winner:
            await self._end_game(winner)
            return

        await self._transition_to(GamePhase.DAY_START)
        await self._run_day_start()

    async def _run_day_start(self) -> None:
        """Day start: prepare for discussion."""
        await self._transition_to(GamePhase.DEATH_ANNOUNCE)
        await self._run_death_announce()

    async def _run_death_announce(self) -> None:
        """Announce deaths from the night."""
        # Emit death announcements
        for player_id in self.state.deaths_today:
            player = self.state.get_player(player_id)
            if player:
                death_event = create_death_event(
                    self.state.game_id,
                    target_id=player_id,
                    killed_by="werewolf",
                    is_night_death=False,
                )
                self._emit_event(death_event)

        await self._transition_to(GamePhase.DISCUSSION)
        await self._run_discussion()

    async def _run_discussion(self) -> None:
        """Discussion phase: players speak in order."""
        # Emit speaking turn events for each alive player
        for speaker_id in self.state.speaking_order:
            player = self.state.get_player(speaker_id)
            if player and player.is_alive:
                self.state.current_speaker_id = speaker_id
                # Call speech callback to get actual speech text
                speech_text = ""
                if self._speech_callback:
                    try:
                        speech_text = await self._speech_callback(self.state, speaker_id)
                    except Exception:
                        logger.exception("Speech callback error", speaker_id=speaker_id)

                speak_event = create_generic_event(
                    self.state.game_id,
                    event_type="speak",
                    actor_id=speaker_id,
                    data={"speaker_id": speaker_id, "text": speech_text, "speaking_order_index": self.state.speak_index},
                )
                self._emit_event(speak_event)
                self.state.speak_index += 1
                # Brief pause between speakers
                await asyncio.sleep(0.5)

        await self._transition_to(GamePhase.VOTING)
        await self._run_voting()

    async def _run_voting(self) -> None:
        """Voting phase: collect votes from all alive players."""
        await self._collect_votes()
        await self._transition_to(GamePhase.VOTE_RESULT)
        await self._run_vote_result()

    async def _run_vote_result(self) -> None:
        """Resolve votes and check for elimination."""
        eliminated_id, is_tie = resolve_votes(self.state)

        votes_received: dict[str, int] = {}
        for vote in self.state.votes:
            if vote.target_id:
                votes_received[vote.target_id] = votes_received.get(vote.target_id, 0) + 1

        vote_event = create_vote_event(
            self.state.game_id,
            votes_received=votes_received,
            eliminated_id=eliminated_id,
            tie=is_tie,
        )
        self._emit_event(vote_event)

        if eliminated_id:
            player = self.state.get_player(eliminated_id)
            if player:
                # Check hunter ability
                if player.role == PlayerRole.HUNTER and player.is_alive:
                    player.can_shoot_on_death = True
                player.is_alive = False
                self.state.deaths_today.append(eliminated_id)
                self.state.all_deaths.append(eliminated_id)

        # Check win condition
        winner = check_win_condition(self.state)
        if winner:
            await self._end_game(winner)
            return

        # Check if we should go to next night
        if self.state.phase != GamePhase.GAME_OVER:
            await self._transition_to(GamePhase.NIGHT_START)
            await self._run_night_start()

    async def _end_game(self, winner: str) -> None:
        """End the game with the specified winner."""
        self.state.winner = winner
        self.state.phase = GamePhase.GAME_OVER
        self._running = False

        # Include all player roles for final reveal
        all_roles = [
            {
                "id": p.player_id,
                "name": p.name,
                "role": p.role.value if p.role else None,
                "is_alive": p.is_alive,
            }
            for p in self.state.players.values()
        ]

        end_event = create_generic_event(
            self.state.game_id,
            event_type="game_over",
            data={"winner": winner, "all_roles": all_roles},
        )
        self._emit_event(end_event)
        logger.info("Game ended", game_id=self.state.game_id, winner=winner)

    # --- Action collection methods ---

    async def _collect_werewolf_actions(self) -> None:
        """Collect kill actions from all alive werewolves."""
        werewolves = self.state.get_alive_werewolves()
        self.state.current_actor_id = None  # Will be set per werewolf

        for werewolf in werewolves:
            self.state.current_actor_id = werewolf.player_id
            # Action will be submitted via submit_action() from agents
            await asyncio.sleep(0.1)  # Small delay for async flow

    async def _collect_seer_actions(self) -> None:
        """Collect inspect action from seer."""
        seers = [p for p in self.state.get_alive_players() if p.role == PlayerRole.SEER]
        if seers:
            self.state.current_actor_id = seers[0].player_id
            await asyncio.sleep(0.1)

    async def _collect_witch_actions(self) -> None:
        """Collect potion actions from witch."""
        witches = [p for p in self.state.get_alive_players() if p.role == PlayerRole.WITCH]
        if witches:
            self.state.current_actor_id = witches[0].player_id
            await asyncio.sleep(0.1)

    async def _collect_votes(self) -> None:
        """Collect votes from all alive players."""
        alive_players = self.state.get_alive_players()
        for player in alive_players:
            self.state.current_actor_id = player.player_id
            await asyncio.sleep(0.1)

    async def submit_action(self, player_id: str, action_data: dict[str, Any]) -> bool:
        """
        Submit an action from a player/agent.
        Returns True if action was accepted.
        """
        player = self.state.get_player(player_id)
        if not player or not player.is_alive:
            return False

        if not can_act(player, self.state.phase):
            return False

        action_type = action_data.get("action_type", "")
        target_id = action_data.get("target_id")

        match self.state.phase:
            case GamePhase.WEREWOLF_TURN:
                if player.role == PlayerRole.WEREWOLF and action_type == "kill":
                    self.state.night_actions.append(
                        NightAction(
                            actor_id=player_id,
                            actor_role=PlayerRole.WEREWOLF,
                            target_id=target_id,
                            action_type="kill",
                        )
                    )
                    return True

            case GamePhase.SEER_TURN:
                if player.role == PlayerRole.SEER and action_type == "inspect":
                    # Determine if target is werewolf
                    target = self.state.get_player(target_id) if target_id else None
                    is_werewolf = target is not None and target.role == PlayerRole.WEREWOLF
                    if target_id:
                        self.state.seer_inspect_results[target_id] = is_werewolf
                    self.state.night_actions.append(
                        NightAction(
                            actor_id=player_id,
                            actor_role=PlayerRole.SEER,
                            target_id=target_id,
                            action_type="inspect",
                        )
                    )
                    return True

            case GamePhase.WITCH_TURN:
                if player.role == PlayerRole.WITCH:
                    if action_type == "save" and player.has_heal_potion:
                        self.state.night_actions.append(
                            NightAction(
                                actor_id=player_id,
                                actor_role=PlayerRole.WITCH,
                                target_id=target_id,
                                action_type="heal",
                            )
                        )
                        player.has_heal_potion = False
                        return True
                    elif action_type == "poison" and player.has_poison_potion:
                        self.state.night_actions.append(
                            NightAction(
                                actor_id=player_id,
                                actor_role=PlayerRole.WITCH,
                                target_id=target_id,
                                action_type="poison",
                            )
                        )
                        player.has_poison_potion = False
                        return True

            case GamePhase.VOTING:
                if action_type == "vote":
                    self.state.votes.append(
                        VoteRecord(
                            voter_id=player_id,
                            target_id=target_id,
                            is_human_vote=player.is_human,
                        )
                    )
                    return True

        return False

    async def stop(self) -> None:
        """Stop the game engine."""
        self._running = False

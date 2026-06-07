"""Game state models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PlayerRole(str, Enum):
    """Player role in the game."""
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"


class GamePhase(str, Enum):
    """Game phase."""
    WAITING = "waiting"
    NIGHT_START = "night_start"
    WEREWOLF_TURN = "werewolf_turn"
    SEER_TURN = "seer_turn"
    WITCH_TURN = "witch_turn"
    NIGHT_END = "night_end"
    DAY_START = "day_start"
    DEATH_ANNOUNCE = "death_announce"
    DISCUSSION = "discussion"
    VOTING = "voting"
    VOTE_RESULT = "vote_result"
    GAME_OVER = "game_over"


class Player(BaseModel):
    """Represents a player in the game."""

    player_id: str
    name: str
    role: Optional[PlayerRole] = None
    is_alive: bool = True
    is_human: bool = False
    # Witch-specific
    has_heal_potion: bool = True
    has_poison_potion: bool = True
    # Hunter-specific
    can_shoot_on_death: bool = False

    model_config = {"use_enum_values": False}

    def model_dump(self, *, hide_role_for_dead: bool = False, **kwargs):
        data = super().model_dump(**kwargs)
        if hide_role_for_dead and not self.is_alive and self.role is not None:
            data["role"] = None
        return data


class NightAction(BaseModel):
    """A night action taken by a player."""

    actor_id: str
    actor_role: PlayerRole
    target_id: Optional[str] = None
    action_type: str = "kill"  # kill, heal, poison, inspect
    success: bool = True


class VoteRecord(BaseModel):
    """A vote cast during discussion."""

    voter_id: str
    target_id: Optional[str] = None  # None = skip vote
    is_human_vote: bool = False


class GameState(BaseModel):
    """Complete state of an ongoing game."""

    game_id: str
    room_id: str
    phase: GamePhase = GamePhase.WAITING
    day_number: int = 0
    players: dict[str, Player] = Field(default_factory=dict)

    # Night actions tracking
    night_actions: list[NightAction] = Field(default_factory=list)
    night_kill_targets: list[str] = Field(default_factory=list)
    witch_heal_used: bool = False
    witch_poison_target: Optional[str] = None
    seer_inspect_results: dict[str, bool] = Field(default_factory=dict)  # target_id -> is_werewolf

    # Voting
    votes: list[VoteRecord] = Field(default_factory=list)
    vote_timeout: bool = False

    # Death tracking
    deaths_today: list[str] = Field(default_factory=list)
    all_deaths: list[str] = Field(default_factory=list)

    # Winner
    winner: Optional[str] = None  # "werewolf" or "village"

    # Current actor for phase
    current_actor_id: Optional[str] = None
    current_speaker_id: Optional[str] = None
    speaking_order: list[str] = Field(default_factory=list)
    speak_index: int = 0

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Event log for spectator replay
    event_log: list[dict] = Field(default_factory=list)

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive]

    def get_alive_werewolves(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive and p.role == PlayerRole.WEREWOLF]

    def get_alive_villagers(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive and p.role != PlayerRole.WEREWOLF]

    def get_player(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)

    def get_alive_werewolf_count(self) -> int:
        return len(self.get_alive_werewolves())

    def get_alive_non_werewolf_count(self) -> int:
        return len(self.get_alive_villagers())

    def is_werewolf_majority(self) -> bool:
        """Check if werewolves are >= non-werewolves (werewolf win condition)."""
        return self.get_alive_werewolf_count() >= self.get_alive_non_werewolf_count()

    def all_werewolves_dead(self) -> bool:
        """Check if all werewolves are dead (village win condition)."""
        return self.get_alive_werewolf_count() == 0

    def get_role_distribution(self, total_players: int) -> dict[PlayerRole, int]:
        """Calculate role counts for game setup."""
        num_werewolves = max(2, total_players // 4)
        num_seers = 1
        num_witches = 1
        num_hunters = 1 if total_players >= 8 else 0
        num_villagers = total_players - num_werewolves - num_seers - num_witches - num_hunters
        return {
            PlayerRole.WEREWOLF: num_werewolves,
            PlayerRole.SEER: num_seers,
            PlayerRole.WITCH: num_witches,
            PlayerRole.HUNTER: num_hunters,
            PlayerRole.VILLAGER: max(0, num_villagers),
        }

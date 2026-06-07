"""Game event models for logging and broadcasting."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class GameEventType(str, Enum):
    """Types of game events."""
    GAME_START = "game_start"
    PHASE_CHANGE = "phase_change"
    DEATH = "death"
    SPEAK = "speak"
    VOTE_CAST = "vote_cast"
    VOTE_RESULT = "vote_result"
    NIGHT_ACTION = "night_action"
    SEER_INSPECTION = "seer_inspection"
    WITCH_HEAL = "witch_heal"
    WITCH_POISON = "witch_poison"
    HUNTER_SHOOT = "hunter_shoot"
    GAME_OVER = "game_over"
    PLAYER_JOIN = "player_join"
    PLAYER_LEAVE = "player_leave"


class GameEvent(BaseModel):
    """Base game event."""

    event_type: GameEventType
    game_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    actor_id: Optional[str] = None
    target_id: Optional[str] = None

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to a dict suitable for structured logging."""
        return {
            "event": self.event_type.value,
            "game_id": self.game_id,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }


class DeathEvent(GameEvent):
    """Player death event."""

    event_type: GameEventType = GameEventType.DEATH
    killed_by: str = ""  # "werewolf", "vote", "witch_poison", "hunter"
    is_night_death: bool = False


class VoteEvent(GameEvent):
    """Vote-related event."""

    event_type: GameEventType = GameEventType.VOTE_RESULT
    votes_received: dict[str, int] = Field(default_factory=dict)  # player_id -> vote_count
    eliminated_id: Optional[str] = None
    tie: bool = False


class PhaseChangeEvent(GameEvent):
    """Phase transition event."""

    event_type: GameEventType = GameEventType.PHASE_CHANGE
    from_phase: str = ""
    to_phase: str = ""


class SpeakEvent(GameEvent):
    """Player speaking event."""

    event_type: GameEventType = GameEventType.SPEAK
    speaker_id: Optional[str] = None
    text: str = ""

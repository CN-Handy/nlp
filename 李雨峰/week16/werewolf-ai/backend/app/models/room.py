"""Room models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RoomStatus(str, Enum):
    """Room lifecycle status."""
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"
    CLOSED = "closed"


class Room(BaseModel):
    """Represents a game room."""

    room_id: str
    room_code: str = Field(..., description="Short code for joining rooms")
    host_id: str
    status: RoomStatus = RoomStatus.WAITING
    player_ids: list[str] = Field(default_factory=list)
    max_players: int = 12
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # Game configuration
    num_werewolves: int = 2
    num_seers: int = 1
    num_witches: int = 1
    num_hunters: int = 1

    @property
    def player_count(self) -> int:
        return len(self.player_ids)

    @property
    def num_villagers(self) -> int:
        """Calculate number of plain villagers based on role counts."""
        total_roles = self.num_werewolves + self.num_seers + self.num_witches + self.num_hunters
        return max(0, self.player_count - total_roles)

    def can_join(self) -> bool:
        return self.status == RoomStatus.WAITING and self.player_count < self.max_players

    def is_full(self) -> bool:
        return self.player_count >= self.max_players

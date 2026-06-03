"""Message models for agent input/output and WebSocket communication."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentActionType(str, Enum):
    """Types of actions an agent can take."""
    KILL = "kill"
    SAVE = "save"
    POISON = "poison"
    INSPECT = "inspect"
    VOTE = "vote"
    SKIP = "skip"
    SPEAK = "speak"
    SHOOT = "shoot"
    PASS = "pass"


class AgentAction(BaseModel):
    """Decision output from an agent."""

    action_type: AgentActionType
    target_id: Optional[str] = None
    reasoning: str = ""
    speak_text: Optional[str] = None  # For SPEAK action
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    model_config = {"use_enum_values": False}


class ClientMessageType(str, Enum):
    """Message types sent by clients."""
    JOIN = "join"
    READY = "ready"
    DECISION = "decision"
    SPEAK = "speak"
    VOTE = "vote"
    CHAT = "chat"
    LEAVE = "leave"


class ServerMessageType(str, Enum):
    """Message types sent by server."""
    GAME_STATE = "game_state"
    PHASE_CHANGE = "phase_change"
    SPEAKING_TURN = "speaking_turn"
    DEATH_ANNOUNCEMENT = "death_announcement"
    VOTE_RESULT = "vote_result"
    GAME_OVER = "game_over"
    ERROR = "error"
    WELCOME = "welcome"


class WSMessage(BaseModel):
    """Generic WebSocket message."""

    type: str  # One of ServerMessageType values
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    game_id: Optional[str] = None
    player_id: Optional[str] = None


class ClientMessage(BaseModel):
    """Message received from a client."""

    type: str  # One of ClientMessageType values
    data: dict[str, Any] = Field(default_factory=dict)
    player_id: Optional[str] = None

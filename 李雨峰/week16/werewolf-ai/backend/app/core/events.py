"""Game event creation helpers."""

from __future__ import annotations

from typing import Any, Optional

from app.models.events import (
    DeathEvent,
    GameEvent,
    GameEventType,
    PhaseChangeEvent,
    SpeakEvent,
    VoteEvent,
)


def create_phase_change_event(
    game_id: str, from_phase: str, to_phase: str, actor_id: Optional[str] = None
) -> PhaseChangeEvent:
    """Create a phase change event."""
    return PhaseChangeEvent(
        game_id=game_id,
        actor_id=actor_id,
        data={"from_phase": from_phase, "to_phase": to_phase},
        from_phase=from_phase,
        to_phase=to_phase,
    )


def create_death_event(
    game_id: str,
    target_id: str,
    killed_by: str,
    is_night_death: bool = False,
    actor_id: Optional[str] = None,
) -> DeathEvent:
    """Create a death event."""
    return DeathEvent(
        game_id=game_id,
        actor_id=actor_id,
        target_id=target_id,
        data={"killed_by": killed_by, "is_night_death": is_night_death},
        killed_by=killed_by,
        is_night_death=is_night_death,
    )


def create_vote_event(
    game_id: str,
    votes_received: dict[str, int],
    eliminated_id: Optional[str] = None,
    tie: bool = False,
) -> VoteEvent:
    """Create a vote result event."""
    return VoteEvent(
        game_id=game_id,
        data={"votes_received": votes_received, "eliminated_id": eliminated_id, "tie": tie},
        votes_received=votes_received,
        eliminated_id=eliminated_id,
        tie=tie,
    )


def create_speak_event(
    game_id: str, speaker_id: str, text: str
) -> SpeakEvent:
    """Create a speak event."""
    return SpeakEvent(
        game_id=game_id,
        actor_id=speaker_id,
        target_id=speaker_id,
        data={"text": text},
        speaker_id=speaker_id,
        text=text,
    )


def create_generic_event(
    game_id: str,
    event_type: GameEventType,
    actor_id: Optional[str] = None,
    target_id: Optional[str] = None,
    data: Optional[dict[str, Any]] = None,
) -> GameEvent:
    """Create a generic game event."""
    return GameEvent(
        event_type=event_type,
        game_id=game_id,
        actor_id=actor_id,
        target_id=target_id,
        data=data or {},
    )

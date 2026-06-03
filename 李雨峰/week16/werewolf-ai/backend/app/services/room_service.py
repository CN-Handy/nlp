"""Room lifecycle management."""

from __future__ import annotations

from typing import Optional

import structlog

from app.config import settings
from app.models.room import Room, RoomStatus
from app.utils.id_gen import generate_id, generate_short_id

logger = structlog.get_logger()


class RoomService:
    """Manages room lifecycle: creation, joining, leaving, status changes."""

    def __init__(self):
        self._rooms: dict[str, Room] = {}
        self._code_to_id: dict[str, str] = {}  # room_code -> room_id

    def create_room(self, host_id: str, max_players: int | None = None) -> Room:
        """Create a new room with the given host."""
        room_id = generate_id()
        room_code = generate_short_id()
        max_p = max_players or settings.max_players_per_room

        room = Room(
            room_id=room_id,
            room_code=room_code,
            host_id=host_id,
            max_players=max_p,
        )
        room.player_ids.append(host_id)

        self._rooms[room_id] = room
        self._code_to_id[room_code] = room_id

        logger.info("Room created", room_id=room_id, room_code=room_code, host_id=host_id)
        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get a room by ID."""
        return self._rooms.get(room_id)

    def get_room_by_code(self, code: str) -> Optional[Room]:
        """Get a room by join code."""
        room_id = self._code_to_id.get(code)
        if room_id:
            return self._rooms.get(room_id)
        return None

    def join_room(self, room_id: str, player_id: str) -> tuple[bool, str]:
        """
        Attempt to join a room.
        Returns (success, error_message).
        """
        room = self._rooms.get(room_id)
        if not room:
            return False, "Room not found"

        if room.status != RoomStatus.WAITING:
            return False, f"Room is not waiting (status: {room.status.value})"

        if player_id in room.player_ids:
            return False, "Player already in room"

        if room.is_full():
            return False, "Room is full"

        room.player_ids.append(player_id)
        logger.info("Player joined room", room_id=room_id, player_id=player_id)
        return True, ""

    def leave_room(self, room_id: str, player_id: str) -> tuple[bool, str]:
        """Remove a player from a room."""
        room = self._rooms.get(room_id)
        if not room:
            return False, "Room not found"

        if player_id not in room.player_ids:
            return False, "Player not in room"

        room.player_ids.remove(player_id)

        # If host leaves and room is waiting, reassign or close
        if room.host_id == player_id and room.status == RoomStatus.WAITING:
            if room.player_ids:
                room.host_id = room.player_ids[0]
                logger.info("Host left room, reassigned", room_id=room_id, new_host=room.host_id)
            else:
                room.status = RoomStatus.CLOSED
                logger.info("Host left empty room, closed", room_id=room_id)

        logger.info("Player left room", room_id=room_id, player_id=player_id)
        return True, ""

    def start_room(self, room_id: str) -> tuple[bool, str]:
        """Transition room to playing status."""
        room = self._rooms.get(room_id)
        if not room:
            return False, "Room not found"

        if room.status != RoomStatus.WAITING:
            return False, f"Cannot start room in {room.status.value} status"

        from app.config import settings
        if room.player_count < settings.min_players_to_start:
            return False, f"Need at least {settings.min_players_to_start} players to start"

        room.status = RoomStatus.PLAYING
        import datetime
        room.started_at = datetime.datetime.now(datetime.timezone.utc)

        logger.info("Room started playing", room_id=room_id, player_count=room.player_count)
        return True, ""

    def finish_room(self, room_id: str) -> None:
        """Mark room as finished."""
        room = self._rooms.get(room_id)
        if room:
            room.status = RoomStatus.FINISHED
            import datetime
            room.finished_at = datetime.datetime.now(datetime.timezone.utc)
            logger.info("Room finished", room_id=room_id)

    def list_rooms(self) -> list[Room]:
        """List all rooms that are in waiting status."""
        return [r for r in self._rooms.values() if r.status == RoomStatus.WAITING]


# Singleton
room_service = RoomService()

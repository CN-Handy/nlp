"""WebSocket connection manager."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections for clients.

    Organizes connections by room so events can be broadcast
    to all players in a room. Also supports spectator connections.
    """

    def __init__(self):
        # room_id -> {player_id -> websocket}
        self._connections: dict[str, dict[str, WebSocket]] = {}
        # player_id -> room_id (reverse lookup)
        self._player_room: dict[str, str] = {}
        # room_id -> list of spectator websockets
        self._spectators: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, player_id: str) -> None:
        """Accept a WebSocket connection and register it."""
        await websocket.accept()

        if room_id not in self._connections:
            self._connections[room_id] = {}

        self._connections[room_id][player_id] = websocket
        self._player_room[player_id] = room_id

        logger.info(
            "WebSocket connected",
            player_id=player_id,
            room_id=room_id,
            total_in_room=len(self._connections[room_id]),
        )

    async def connect_spectator(self, websocket: WebSocket, room_id: str) -> None:
        """Accept a spectator WebSocket connection."""
        await websocket.accept()

        if room_id not in self._spectators:
            self._spectators[room_id] = []

        self._spectators[room_id].append(websocket)
        logger.info("Spectator connected", room_id=room_id)

    async def disconnect(self, player_id: str) -> None:
        """Remove a player's WebSocket connection."""
        room_id = self._player_room.pop(player_id, None)
        if room_id and room_id in self._connections:
            self._connections[room_id].pop(player_id, None)
            if not self._connections[room_id]:
                del self._connections[room_id]
            logger.info("WebSocket disconnected", player_id=player_id, room_id=room_id)

    async def disconnect_spectator(self, websocket: WebSocket, room_id: str) -> None:
        """Remove a spectator WebSocket connection."""
        if room_id in self._spectators:
            try:
                self._spectators[room_id].remove(websocket)
            except ValueError:
                pass
            if not self._spectators[room_id]:
                del self._spectators[room_id]

    async def send_to_player(self, player_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific player."""
        room_id = self._player_room.get(player_id)
        if not room_id:
            return False

        ws = self._connections.get(room_id, {}).get(player_id)
        if not ws:
            return False

        try:
            import json
            await ws.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning("Failed to send to player", player_id=player_id, error=str(e))
            return False

    async def broadcast_to_room(self, room_id: str, message: dict[str, Any], exclude: set[str] | None = None) -> int:
        """
        Broadcast a message to all players and spectators in a room.
        Returns number of successful sends.
        """
        connections = self._connections.get(room_id, {})
        exclude = exclude or set()
        sent_count = 0

        import json
        json_message = json.dumps(message)

        # Send to players
        for player_id, ws in list(connections.items()):
            if player_id in exclude:
                continue
            try:
                await ws.send_text(json_message)
                sent_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to broadcast to player",
                    player_id=player_id,
                    room_id=room_id,
                    error=str(e),
                )

        # Send to spectators
        for ws in list(self._spectators.get(room_id, [])):
            try:
                await ws.send_text(json_message)
                sent_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to broadcast to spectator",
                    room_id=room_id,
                    error=str(e),
                )

        return sent_count

    def get_connected_players(self, room_id: str) -> list[str]:
        """Get list of connected player IDs in a room."""
        return list(self._connections.get(room_id, {}).keys())

    def is_connected(self, player_id: str) -> bool:
        """Check if a player has an active WebSocket connection."""
        room_id = self._player_room.get(player_id)
        if not room_id:
            return False
        return player_id in self._connections.get(room_id, {})

    def get_room_id_for_player(self, player_id: str) -> str | None:
        """Get the room ID for a connected player."""
        return self._player_room.get(player_id)


# Singleton
ws_manager = WebSocketManager()

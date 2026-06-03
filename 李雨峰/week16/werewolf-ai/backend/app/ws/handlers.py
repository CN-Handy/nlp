"""WebSocket message handlers for client connections."""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.human_proxy import HumanProxyAgent
from app.models.messages import ClientMessage
from app.services.game_service import game_service
from app.ws.manager import ws_manager

logger = structlog.get_logger()


async def handle_websocket(websocket: Any, room_id: str, player_id: str) -> None:
    """
    Handle a WebSocket connection for a player.

    This is the main entry point for WebSocket connections.
    It manages the connection lifecycle and dispatches messages.
    """
    await ws_manager.connect(websocket, room_id, player_id)

    # Send welcome message
    await ws_manager.send_to_player(
        player_id,
        {
            "type": "welcome",
            "data": {
                "player_id": player_id,
                "room_id": room_id,
                "message": "Connected to game",
            },
        },
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            await handle_client_message(player_id, raw_message)
    except Exception as e:
        logger.info(
            "WebSocket connection ended",
            player_id=player_id,
            error=str(e),
        )
    finally:
        await ws_manager.disconnect(player_id)


async def handle_client_message(player_id: str, raw_message: str) -> None:
    """Parse and dispatch a client message."""
    try:
        data = json.loads(raw_message)
    except json.JSONDecodeError:
        await ws_manager.send_to_player(
            player_id,
            {"type": "error", "data": {"message": "Invalid JSON"}},
        )
        return

    try:
        message = ClientMessage.model_validate(data)
    except Exception as e:
        await ws_manager.send_to_player(
            player_id,
            {"type": "error", "data": {"message": f"Invalid message format: {e}"}},
        )
        return

    message.player_id = player_id

    # Dispatch based on message type
    match message.type:
        case "decision":
            await _handle_decision(player_id, message)
        case "speak":
            await _handle_speak(player_id, message)
        case "vote":
            await _handle_vote(player_id, message)
        case "ready":
            await _handle_ready(player_id, message)
        case "chat":
            await _handle_chat(player_id, message)
        case _:
            logger.warning("Unknown message type", type=message.type, player_id=player_id)
            await ws_manager.send_to_player(
                player_id,
                {"type": "error", "data": {"message": f"Unknown message type: {message.type}"}},
            )


async def _handle_decision(player_id: str, message: ClientMessage) -> None:
    """Handle a decision message from a human player."""
    room_id = ws_manager.get_room_id_for_player(player_id)
    if not room_id:
        return

    game_state = game_service.get_game_by_room(room_id)
    if not game_state:
        return

    result = await game_service.submit_human_action(
        game_state.game_id, player_id, message.data
    )

    if not result:
        await ws_manager.send_to_player(
            player_id,
            {"type": "error", "data": {"message": "Action rejected (wrong phase or invalid)"}},
        )
    else:
        logger.info("Human action submitted", player_id=player_id, action=message.data.get("action_type"))


async def _handle_speak(player_id: str, message: ClientMessage) -> None:
    """Handle a speak message from a human player."""
    room_id = ws_manager.get_room_id_for_player(player_id)
    if not room_id:
        return

    game_state = game_service.get_game_by_room(room_id)
    if not game_state:
        return

    text = message.data.get("text", "")
    await game_service.submit_human_speech(game_state.game_id, player_id, text)

    # Broadcast speech to room
    await ws_manager.broadcast_to_room(
        room_id,
        {
            "type": "speak",
            "data": {
                "speaker_id": player_id,
                "text": text,
            },
            "game_id": game_state.game_id,
        },
    )


async def _handle_vote(player_id: str, message: ClientMessage) -> None:
    """Handle a vote message from a human player (alias for decision)."""
    vote_data = {
        "action_type": "vote",
        "target_id": message.data.get("target_id"),
        "reasoning": message.data.get("reasoning", ""),
    }
    await _handle_decision(player_id, ClientMessage(type="decision", data=vote_data))


async def _handle_ready(player_id: str, message: ClientMessage) -> None:
    """Handle a ready message from a human player."""
    logger.info("Player ready", player_id=player_id)
    await ws_manager.send_to_player(
        player_id,
        {"type": "game_state", "data": {"player_id": player_id, "status": "ready"}},
    )


async def _handle_chat(player_id: str, message: ClientMessage) -> None:
    """Handle a chat message (meta-communication, not game speech)."""
    room_id = ws_manager.get_room_id_for_player(player_id)
    if not room_id:
        return

    await ws_manager.broadcast_to_room(
        room_id,
        {
            "type": "chat",
            "data": {
                "sender_id": player_id,
                "text": message.data.get("text", ""),
            },
        },
        exclude={player_id},
    )

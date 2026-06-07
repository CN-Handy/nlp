"""Quick Start API: one-click game start for spectator mode."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.game_service import game_service
from app.services.room_service import room_service
from app.utils.id_gen import generate_id

router = APIRouter()


@router.post("/start", summary="One-click start game (spectator mode)")
async def quick_start_game():
    """
    Creates a room with 9 AI players, initializes the game, and starts it.
    Returns the room_id and game_id for spectator connection.
    """
    # 1. Create a room with a synthetic host
    host_id = generate_id()
    room = room_service.create_room(host_id=host_id, max_players=9)

    # 2. Add 8 more AI players (total 9)
    for _ in range(8):
        player_id = generate_id()
        room_service.join_room(room.room_id, player_id)

    # 3. Create game (no human players - all AI)
    game_state = game_service.create_game(room.room_id)
    game_service.initialize_agents(game_state.game_id, human_player_ids=[])

    # 4. Start room
    room_service.start_room(room.room_id)

    # 5. Start game engine in background
    await game_service.start_game(game_state.game_id)

    return {
        "room_id": room.room_id,
        "game_id": game_state.game_id,
        "player_count": room.player_count,
    }

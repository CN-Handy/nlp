"""Game API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.game_service import game_service
from app.services.room_service import room_service
from app.ws.manager import ws_manager

router = APIRouter()


class InitGameRequest(BaseModel):
    room_id: str
    human_player_ids: list[str] = []


class GameInfoResponse(BaseModel):
    game_id: str
    room_id: str
    phase: str
    day_number: int
    player_count: int


class GameStateResponse(BaseModel):
    game_id: str
    phase: str
    day_number: int
    players: dict
    deaths_today: list[str]
    all_deaths: list[str]
    winner: Optional[str] = None


@router.post("/init", response_model=dict, summary="Initialize a new game")
async def init_game(req: InitGameRequest):
    """
    Initialize a new game for a room.

    Creates the game state, assigns roles, and creates agents.
    human_player_ids specifies which players are controlled by humans via WebSocket.
    """
    room = room_service.get_room(req.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != "waiting":
        # Allow starting from API even if room status wasn't set yet
        pass

    # Check minimum players
    from app.config import settings
    if room.player_count < settings.min_players_to_start:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {settings.min_players_to_start} players",
        )

    # Create game and initialize agents
    game_state = game_service.create_game(req.room_id)
    game_service.initialize_agents(game_state.game_id, req.human_player_ids)

    # Start room
    room_service.start_room(req.room_id)

    return {
        "message": "Game initialized",
        "game_id": game_state.game_id,
        "room_id": req.room_id,
        "player_count": room.player_count,
        "human_players": req.human_player_ids,
        "ai_players": [pid for pid in room.player_ids if pid not in req.human_player_ids],
    }


@router.post("/{game_id}/start", summary="Start the game engine")
async def start_game(game_id: str):
    """
    Start the game engine. This begins the game loop.

    The game runs asynchronously in the background.
    """
    game_state = game_service.get_game(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")

    await game_service.start_game(game_id)

    return {"message": "Game started", "game_id": game_id}


@router.get("/{game_id}", response_model=GameStateResponse, summary="Get game state")
async def get_game(game_id: str):
    """Get the current game state."""
    game_state = game_service.get_game(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameStateResponse(
        game_id=game_state.game_id,
        phase=game_state.phase.value,
        day_number=game_state.day_number,
        players={
            pid: {
                "player_id": p.player_id,
                "name": p.name,
                "is_alive": p.is_alive,
                "is_human": p.is_human,
                # Role is hidden for alive non-current players
                "role": p.role.value if p.role else None,
            }
            for pid, p in game_state.players.items()
        },
        deaths_today=game_state.deaths_today,
        all_deaths=game_state.all_deaths,
        winner=game_state.winner,
    )


@router.get("/{game_id}/player/{player_id}", response_model=dict, summary="Get game state for a player")
async def get_game_for_player(game_id: str, player_id: str):
    """Get the filtered game state visible to a specific player (hides other roles)."""
    game_state = game_service.get_game(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")

    visible_state = game_service.get_game_state_for_player(game_id, player_id)
    return visible_state


@router.post("/{game_id}/action", summary="Submit a human player action")
async def submit_action(game_id: str, action: dict):
    """
    Submit a decision/action from a human player.

    Expected format:
    {
        "player_id": "player_xxx",
        "action_type": "kill" | "vote" | "save" | "poison" | "inspect" | "skip",
        "target_id": "player_yyy",
        "reasoning": "optional explanation"
    }
    """
    player_id = action.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id is required")

    success = await game_service.submit_human_action(
        game_id, player_id, action
    )
    if not success:
        raise HTTPException(status_code=400, detail="Action rejected")

    return {"message": "Action accepted", "player_id": player_id}


@router.websocket("/spectate/{room_id}")
async def websocket_spectate(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for spectators (god mode).

    Connect to: /api/v1/games/spectate/{room_id}

    Receives ALL game events (no information hiding).
    """
    import json as _json
    room = room_service.get_room(room_id)
    if not room:
        await websocket.close(code=4004, reason="Room not found")
        return

    await ws_manager.connect_spectator(websocket, room_id)

    try:
        # Send initial connection info
        await websocket.send_text(
            '{"type": "spectate_start", "data": {"room_id": "' + room_id + '"}}'
        )

        # Send current game state if a game is running
        game_state = game_service.get_game_by_room(room_id)
        if game_state:
            # Send players list with full info (spectator = god mode)
            players_data = [
                {
                    "id": p.player_id,
                    "name": p.name,
                    "role": p.role.value if p.role else None,
                    "is_alive": p.is_alive,
                }
                for p in game_state.players.values()
            ]
            await websocket.send_text(_json.dumps({
                "type": "game_event",
                "data": {
                    "event_type": "game_start",
                    "game_id": game_state.game_id,
                    "phase": game_state.phase.value,
                    "day_number": game_state.day_number,
                    "actor_id": None,
                    "actor_name": None,
                    "actor_role": None,
                    "target_id": None,
                    "target_name": None,
                    "target_role": None,
                    "data": {
                        "player_count": len(players_data),
                        "players": players_data,
                    },
                    "timestamp": None,
                },
            }))

            # Send all past events so far (event replay)
            for past_event in game_state.event_log:
                await websocket.send_text(_json.dumps({
                    "type": "game_event",
                    "data": past_event,
                }))

        # Keep connection alive, wait for disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect_spectator(websocket, room_id)


@router.websocket("/{game_id}/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """
    WebSocket endpoint for human players.

    Connect to: /api/v1/games/{game_id}/ws/{player_id}

    Sends: game events, state updates, speaking turns
    Receives: decisions, speech, votes, chat
    """
    game_state = game_service.get_game(game_id)
    if not game_state:
        await websocket.close(code=4004, reason="Game not found")
        return

    room = room_service.get_room(game_state.room_id)
    if not room or player_id not in room.player_ids:
        await websocket.close(code=4003, reason="Player not in room")
        return

    try:
        await handle_websocket(websocket, game_state.room_id, player_id)
    except WebSocketDisconnect:
        pass

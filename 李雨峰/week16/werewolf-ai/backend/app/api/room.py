"""Room API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.room import Room, RoomStatus
from app.services.room_service import room_service

router = APIRouter()


class CreateRoomRequest(BaseModel):
    host_id: str
    max_players: Optional[int] = None


class JoinRoomRequest(BaseModel):
    player_id: str
    room_code: Optional[str] = None
    room_id: Optional[str] = None


class RoomResponse(BaseModel):
    room_id: str
    room_code: str
    host_id: str
    status: RoomStatus
    player_ids: list[str]
    player_count: int
    max_players: int


@router.post("/", response_model=RoomResponse, summary="Create a new room")
async def create_room(req: CreateRoomRequest):
    """Create a new game room. The creator becomes the host."""
    room = room_service.create_room(host_id=req.host_id, max_players=req.max_players)
    return RoomResponse(
        room_id=room.room_id,
        room_code=room.room_code,
        host_id=room.host_id,
        status=room.status,
        player_ids=room.player_ids,
        player_count=room.player_count,
        max_players=room.max_players,
    )


@router.post("/{room_id}/join", response_model=RoomResponse, summary="Join a room")
async def join_room(room_id: str, req: JoinRoomRequest):
    """Join an existing room by room_id or room_code."""
    # Resolve room_id if code provided
    target_room_id = room_id
    if req.room_code:
        room = room_service.get_room_by_code(req.room_code)
        if not room:
            raise HTTPException(status_code=404, detail="Room code not found")
        target_room_id = room.room_id

    success, error = room_service.join_room(target_room_id, req.player_id)
    if not success:
        raise HTTPException(status_code=400, detail=error)

    room = room_service.get_room(target_room_id)
    return RoomResponse(
        room_id=room.room_id,
        room_code=room.room_code,
        host_id=room.host_id,
        status=room.status,
        player_ids=room.player_ids,
        player_count=room.player_count,
        max_players=room.max_players,
    )


@router.post("/{room_id}/leave", summary="Leave a room")
async def leave_room(room_id: str, player_id: str):
    """Leave a room. If the host leaves, the host role is reassigned."""
    success, error = room_service.leave_room(room_id, player_id)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Left room successfully"}


@router.post("/{room_id}/start", response_model=RoomResponse, summary="Start the game")
async def start_room(room_id: str):
    """Start the game in a room. Requires enough players."""
    success, error = room_service.start_room(room_id)
    if not success:
        raise HTTPException(status_code=400, detail=error)

    room = room_service.get_room(room_id)
    return RoomResponse(
        room_id=room.room_id,
        room_code=room.room_code,
        host_id=room.host_id,
        status=room.status,
        player_ids=room.player_ids,
        player_count=room.player_count,
        max_players=room.max_players,
    )


@router.get("/{room_id}", response_model=RoomResponse, summary="Get room details")
async def get_room(room_id: str):
    """Get details about a room."""
    room = room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse(
        room_id=room.room_id,
        room_code=room.room_code,
        host_id=room.host_id,
        status=room.status,
        player_ids=room.player_ids,
        player_count=room.player_count,
        max_players=room.max_players,
    )


@router.get("/", response_model=list[RoomResponse], summary="List waiting rooms")
async def list_rooms():
    """List all rooms that are in waiting status."""
    rooms = room_service.list_rooms()
    return [
        RoomResponse(
            room_id=r.room_id,
            room_code=r.room_code,
            host_id=r.host_id,
            status=r.status,
            player_ids=r.player_ids,
            player_count=r.player_count,
            max_players=r.max_players,
        )
        for r in rooms
    ]

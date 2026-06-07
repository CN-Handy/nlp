"""Router: aggregates all API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.room import router as room_router
from app.api.game import router as game_router
from app.api.quick_start import router as quick_start_router

router = APIRouter(prefix="/api/v1")

router.include_router(room_router, prefix="/rooms", tags=["rooms"])
router.include_router(game_router, prefix="/games", tags=["games"])
router.include_router(quick_start_router, prefix="/quick", tags=["quick"])

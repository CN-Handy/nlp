"""FastAPI：创建对局、控制进度、查询状态与结果。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from configs.game_configs import PRESET_CONFIGS, get_config
from engine.game_engine import GameEngine
from game_logging.game_logger import GameLogger
from schema.game import GameConfig, GameState

app = FastAPI(title="AI 狼人杀 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_games: dict[str, GameEngine] = {}
_logger = GameLogger()


class CreateGameRequest(BaseModel):
    config_name: str = "standard_6"
    auto_run: bool = False


class CreateGameResponse(BaseModel):
    game_id: str
    state: GameState


class StepResponse(BaseModel):
    game_id: str
    state: GameState
    continued: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/configs")
def list_configs() -> dict[str, Any]:
    return {
        name: {"player_count": c.player_count, "roles": c.roles}
        for name, c in PRESET_CONFIGS.items()
    }


@app.post("/games", response_model=CreateGameResponse)
def create_game(req: CreateGameRequest) -> CreateGameResponse:
    if req.config_name not in PRESET_CONFIGS:
        raise HTTPException(400, f"未知配置: {req.config_name}")
    config = get_config(req.config_name)
    config.auto_run = req.auto_run
    game_id = f"game_{uuid.uuid4().hex[:12]}"
    engine = GameEngine(config=config)
    engine.setup(game_id=game_id)
    engine.is_paused = True
    _games[game_id] = engine
    return CreateGameResponse(game_id=game_id, state=engine.get_state())


@app.get("/games/{game_id}")
def get_game(game_id: str) -> dict[str, Any]:
    engine = _get_engine(game_id)
    state = engine.get_state()
    return {
        "state": state.model_dump(mode="json"),
        "dialogues": [d.model_dump(mode="json") for d in engine.dialogues],
        "summaries": engine.record.summaries if engine.record else {},
    }


@app.post("/games/{game_id}/step", response_model=StepResponse)
def step_game(game_id: str) -> StepResponse:
    engine = _get_engine(game_id)
    if engine.is_finished:
        return StepResponse(game_id=game_id, state=engine.get_state(), continued=False)
    continued = engine.step()
    return StepResponse(game_id=game_id, state=engine.get_state(), continued=continued)


@app.post("/games/{game_id}/run")
def run_game(game_id: str) -> dict[str, Any]:
    engine = _get_engine(game_id)
    engine.run_to_end()
    record = engine.finalize()
    path = _logger.save(record)
    return {
        "state": engine.get_state().model_dump(mode="json"),
        "record": record.model_dump(mode="json"),
        "log_path": str(path),
    }


@app.post("/games/{game_id}/pause")
def pause_game(game_id: str) -> GameState:
    engine = _get_engine(game_id)
    engine.pause()
    return engine.get_state()


@app.post("/games/{game_id}/resume")
def resume_game(game_id: str) -> GameState:
    engine = _get_engine(game_id)
    engine.resume()
    return engine.get_state()


@app.post("/games/{game_id}/finalize")
def finalize_game(game_id: str) -> dict[str, Any]:
    engine = _get_engine(game_id)
    if not engine.is_finished:
        raise HTTPException(400, "游戏尚未结束")
    record = engine.finalize()
    path = _logger.save(record)
    return {"record": record.model_dump(mode="json"), "log_path": str(path)}


@app.get("/experiences/{role}")
def get_experiences(role: str, limit: int = 5) -> dict[str, Any]:
    from memory.experience import ExperienceStore

    store = ExperienceStore()
    entries = store.get_for_role(role, limit)
    return {"role": role, "experiences": [e.model_dump() for e in entries]}


def _get_engine(game_id: str) -> GameEngine:
    if game_id not in _games:
        raise HTTPException(404, "对局不存在")
    return _games[game_id]

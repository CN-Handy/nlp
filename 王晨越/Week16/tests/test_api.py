"""FastAPI 接口测试"""

import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_step_game() -> None:
    r = client.post("/games", json={"config_name": "mini_4", "auto_run": False})
    assert r.status_code == 200
    game_id = r.json()["game_id"]
    state = r.json()["state"]
    assert state["is_paused"] is True

    r2 = client.post(f"/games/{game_id}/step")
    assert r2.status_code == 200
    assert r2.json()["state"]["day"] >= 1


def test_run_game() -> None:
    r = client.post("/games", json={"config_name": "mini_4"})
    game_id = r.json()["game_id"]
    r2 = client.post(f"/games/{game_id}/run")
    assert r2.status_code == 200
    assert r2.json()["state"]["is_finished"] is True

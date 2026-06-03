"""对局结构化日志：JSON 持久化与控制台输出。"""

import json
from datetime import datetime
from pathlib import Path

from schema.game import GameRecord


class GameLogger:
    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: GameRecord) -> Path:
        path = self.log_dir / f"{record.game_id}.json"
        payload = record.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

    @staticmethod
    def new_game_id() -> str:
        return f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

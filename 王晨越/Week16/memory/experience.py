"""跨局经验存储：按角色类型持久化赛后总结，供后续对局检索。"""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    """单条经验"""

    game_id: str
    role: str
    player_id: int
    summary: str
    winner: str
    timestamp: str = ""


class ExperienceStore:
    """基于 JSON 文件的经验库（真实读写，非占位）"""

    def __init__(self, path: str | Path = "memory/data/experiences.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[ExperienceEntry] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = [ExperienceEntry.model_validate(e) for e in raw]
        else:
            self._entries = []

    def _save(self) -> None:
        data = [e.model_dump() for e in self._entries]
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, entry: ExperienceEntry) -> None:
        self._entries.append(entry)
        self._save()

    def get_for_role(self, role: str, limit: int = 5) -> list[ExperienceEntry]:
        matched = [e for e in reversed(self._entries) if e.role == role]
        return matched[:limit]

    def format_for_prompt(self, role: str, limit: int = 3) -> str:
        entries = self.get_for_role(role, limit)
        if not entries:
            return "（暂无历史对局经验）"
        lines = []
        for i, e in enumerate(entries, 1):
            result = "胜" if e.winner in ("good", "evil") else "未知"
            lines.append(f"{i}. [{e.game_id}] {result}：{e.summary[:200]}")
        return "历史经验参考：\n" + "\n".join(lines)

    def clear(self) -> None:
        self._entries = []
        self._save()

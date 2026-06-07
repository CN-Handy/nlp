"""赛后总结 Agent：为每名存活/出局玩家生成可沉淀的经验。"""

import json
import re
from datetime import datetime

from agent.base import BaseAgent, LLMClient
from agent.player_agent import player_display_name
from memory.experience import ExperienceEntry, ExperienceStore
from schema.dialogue import DialogueRecord
from schema.game import GameRecord


class SummaryAgent(BaseAgent):
    def __init__(self, llm: LLMClient | None = None, store: ExperienceStore | None = None) -> None:
        super().__init__(llm)
        self.store = store or ExperienceStore()

    def run(self, record: GameRecord) -> dict[int, str]:
        return self.summarize_all(record)

    def _parse_json(self, text: str) -> dict:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"summary": text[:300]}

    def summarize_player(
        self,
        player_id: int,
        role: str,
        record: GameRecord,
    ) -> str:
        dialogues = [d.format_line() for d in record.dialogues if d.speaker_id == player_id]
        history = "\n".join(dialogues[-20:]) or "（本局几乎未发言）"
        system = "你是狼人杀复盘教练。根据本局表现给出简短经验总结（80字内）。JSON：{\"summary\": \"...\"}"
        user = (
            f"玩家：{player_display_name(player_id, role)}\n"
            f"胜负：{record.winner}\n"
            f"本局发言摘录：\n{history}"
        )
        raw = self.llm.chat(system, user, "balanced")
        data = self._parse_json(raw)
        return str(data.get("summary", "需改进发言逻辑与投票判断。"))

    def summarize_all(self, record: GameRecord) -> dict[int, str]:
        summaries: dict[int, str] = {}
        for pid, role in record.role_assignment.items():
            text = self.summarize_player(pid, role, record)
            summaries[pid] = text
            self.store.add(
                ExperienceEntry(
                    game_id=record.game_id,
                    role=role,
                    player_id=pid,
                    summary=text,
                    winner=record.winner or "",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
        return summaries

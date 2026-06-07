"""对话与阶段事件的结构化记录。"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PhaseType(str, Enum):
    """游戏阶段（中文标识，便于日志与前端展示）"""

    NIGHT_WEREWOLF = "夜晚-狼人"
    NIGHT_SEER = "夜晚-预言家"
    NIGHT_WITCH = "夜晚-女巫"
    DAY_DISCUSS = "白天-讨论"
    DAY_VOTE = "白天-投票"
    HUNTER_SHOOT = "猎人-开枪"
    SYSTEM = "系统公告"
    SUMMARY = "赛后总结"


class DialogueRecord(BaseModel):
    """单条对话/事件记录"""

    game_id: str
    day: int
    phase: PhaseType
    speaker_id: int | None = None  # None 表示系统
    speaker_name: str = ""
    content: str
    visible_to: list[int] | None = None  # None 表示全员可见
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: str | None = None  # speak / vote / kill / check / save / poison 等
    target_id: int | None = None

    def format_line(self) -> str:
        """格式化为可读的一行日志"""
        prefix = f"[第{self.day}天·{self.phase.value}]"
        if self.speaker_name:
            return f"{prefix} {self.speaker_name}：{self.content}"
        return f"{prefix} {self.content}"

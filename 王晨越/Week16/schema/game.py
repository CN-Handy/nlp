"""对局配置、状态与完整记录。"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from schema.dialogue import DialogueRecord


class PlayerStyle(str, Enum):
    """决策风格"""

    CAUTIOUS = "cautious"  # 谨慎
    BOLD = "bold"  # 大胆
    BALANCED = "balanced"  # 平衡
    RANDOM = "random"  # 随机


STYLE_CN: dict[str, str] = {
    PlayerStyle.CAUTIOUS: "谨慎型",
    PlayerStyle.BOLD: "大胆型",
    PlayerStyle.BALANCED: "平衡型",
    PlayerStyle.RANDOM: "随机型",
}


class GameConfig(BaseModel):
    """单局配置"""

    name: str = "standard_6"
    player_count: int = 6
    roles: list[str] = Field(
        default_factory=lambda: ["werewolf", "werewolf", "seer", "witch", "hunter", "villager"]
    )
    player_styles: dict[int, PlayerStyle] = Field(default_factory=dict)
    auto_run: bool = True  # False 时需手动 step


class DeathRecord(BaseModel):
    """死亡记录"""

    player_id: int
    role: str
    day: int
    cause: str  # night_kill / vote / poison / hunter_shoot


class GameState(BaseModel):
    """运行时状态快照（供 API 返回）"""

    game_id: str
    day: int = 0
    phase: str = "未开始"
    alive_players: list[int] = Field(default_factory=list)
    dead_players: list[int] = Field(default_factory=list)
    role_assignment: dict[int, str] = Field(default_factory=dict)
    winner: str | None = None
    is_paused: bool = False
    is_finished: bool = False
    recent_dialogues: list[DialogueRecord] = Field(default_factory=list)


class GameRecord(BaseModel):
    """完整对局记录（持久化）"""

    game_id: str
    start_time: str
    end_time: str | None = None
    config_name: str
    role_assignment: dict[int, str]
    player_styles: dict[int, str]
    dialogues: list[DialogueRecord] = Field(default_factory=list)
    winner: str | None = None  # good / evil
    death_order: list[DeathRecord] = Field(default_factory=list)
    summaries: dict[str, str] = Field(default_factory=dict)  # player_id -> 赛后总结

    def to_summary_text(self) -> str:
        lines = [
            "=" * 60,
            "游戏摘要",
            "=" * 60,
            f"游戏ID: {self.game_id}",
            f"开始时间: {self.start_time}",
            f"结束时间: {self.end_time or '进行中'}",
            f"胜利方: {CAMP_DISPLAY.get(self.winner or '', '未知')}",
            f"总对话数: {len(self.dialogues)}",
            "",
            "玩家配置:",
        ]
        from roles.base import ROLE_CN

        for pid, role in sorted(self.role_assignment.items()):
            style = self.player_styles.get(pid, "balanced")
            style_cn = STYLE_CN.get(style, style)
            lines.append(f"  玩家{pid}（{ROLE_CN.get(role, role)}）: {style_cn}")
        if self.death_order:
            lines.append("\n死亡顺序:")
            for d in self.death_order:
                role_cn = ROLE_CN.get(d.role, d.role)
                cause_cn = CAUSE_CN.get(d.cause, d.cause)
                lines.append(f"  第{d.day}天: 玩家{d.player_id}（{role_cn}）- {cause_cn}")
        return "\n".join(lines)


CAMP_DISPLAY = {"good": "好人阵营", "evil": "狼人阵营"}
CAUSE_CN = {
    "night_kill": "狼人击杀",
    "vote": "投票出局",
    "poison": "女巫毒杀",
    "hunter_shoot": "猎人开枪",
}

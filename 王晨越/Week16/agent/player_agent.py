"""玩家 Agent：根据角色、风格与可见历史进行发言与决策。"""

import json
import re

from agent.base import BaseAgent, LLMClient
from roles import ROLE_REGISTRY
from roles.base import ROLE_CN, BaseRole
from schema.dialogue import DialogueRecord, PhaseType
from schema.game import PlayerStyle, STYLE_CN


def player_display_name(player_id: int, role_type: str) -> str:
    role_cn = ROLE_CN.get(role_type, role_type)
    return f"玩家{player_id}（{role_cn}）"


class PlayerAgent(BaseAgent):
    """单名玩家的 LLM 决策器"""

    def __init__(
        self,
        player_id: int,
        role_type: str,
        style: PlayerStyle = PlayerStyle.BALANCED,
        llm: LLMClient | None = None,
    ) -> None:
        super().__init__(llm)
        self.player_id = player_id
        self.role_type = role_type
        self.style = style
        role_cls = ROLE_REGISTRY.get(role_type)
        if not role_cls:
            raise ValueError(f"未知角色: {role_type}")
        self.role: BaseRole = role_cls()

    @property
    def display_name(self) -> str:
        return player_display_name(self.player_id, self.role_type)

    def _filter_dialogues(
        self,
        dialogues: list[DialogueRecord],
        visible_to_player: bool = True,
    ) -> str:
        """按信息隔离过滤历史，构建 Agent 可见的完整对话记忆"""
        lines: list[str] = []
        for d in dialogues:
            if d.visible_to is not None and self.player_id not in d.visible_to:
                continue
            lines.append(d.format_line())
        return "\n".join(lines) if lines else "（暂无公开对话）"

    def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """BaseAgent 接口占位；实际使用 decide_* 方法"""
        raise NotImplementedError("请调用 decide_speech / decide_vote / decide_night_action")

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}

    def decide_speech(
        self,
        day: int,
        dialogues: list[DialogueRecord],
        alive: list[int],
        private_state: dict,
        experience_text: str = "",
    ) -> str:
        history = self._filter_dialogues(dialogues)
        system = (
            f"你是狼人杀游戏中的{self.display_name}。"
            f"决策风格：{STYLE_CN.get(self.style.value, self.style.value)}。"
            f"{self.role.get_goal_description()}\n"
            f"{self.role.get_private_info(self.player_id, private_state)}\n"
            f"{experience_text}\n"
            "请用 JSON 回复：{{\"speech\": \"你的发言内容\"}}"
        )
        user = (
            f"第{day}天白天讨论。存活玩家：[{', '.join(map(str, alive))}]\n"
            f"历史对话：\n{history}\n"
            "请发言（30-80字，符合角色与风格）。"
        )
        raw = self.llm.chat(system, user, self.style.value)
        data = self._parse_json(raw)
        return str(data.get("speech", raw[:120]))

    def decide_vote(
        self,
        day: int,
        dialogues: list[DialogueRecord],
        alive: list[int],
        private_state: dict,
        experience_text: str = "",
    ) -> int | None:
        others = [p for p in alive if p != self.player_id]
        if not others:
            return None
        history = self._filter_dialogues(dialogues)
        system = (
            f"你是{self.display_name}。{self.role.get_goal_description()}\n"
            f"{experience_text}\n"
            '请 JSON 回复：{"vote": 玩家编号}'
        )
        user = f"第{day}天投票。存活玩家：[{', '.join(map(str, alive))}]\n历史：\n{history}"
        raw = self.llm.chat(system, user, self.style.value)
        data = self._parse_json(raw)
        target = data.get("vote", data.get("target"))
        if isinstance(target, int) and target in others:
            return target
        return others[0]

    def decide_night_action(
        self,
        day: int,
        action: str,
        dialogues: list[DialogueRecord],
        alive: list[int],
        private_state: dict,
        extra: str = "",
        experience_text: str = "",
    ) -> dict:
        history = self._filter_dialogues(dialogues)
        action_hints = {
            "kill": '{"kill": 玩家编号}',
            "check": '{"check": 玩家编号}',
            "witch": '{"use_save": true/false, "use_poison": true/false, "poison_target": 编号或null}',
            "shoot": '{"shoot": 玩家编号}',
        }
        system = (
            f"你是{self.display_name}。夜晚行动：{action}。\n"
            f"{self.role.get_private_info(self.player_id, private_state)}\n"
            f"{experience_text}\n"
            f"JSON 格式：{action_hints.get(action, '{}')}"
        )
        user = (
            f"第{day}天夜晚。存活玩家：[{', '.join(map(str, alive))}]\n"
            f"{extra}\n历史：\n{history}"
        )
        raw = self.llm.chat(system, user, self.style.value)
        return self._parse_json(raw)

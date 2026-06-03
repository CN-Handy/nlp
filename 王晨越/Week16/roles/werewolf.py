"""狼人角色：夜晚击杀、白天伪装。"""

from roles.base import BaseRole, Camp, RoleType


class WerewolfRole(BaseRole):
    role_type = RoleType.WEREWOLF
    camp = Camp.EVIL

    def win_condition(self, alive_roles: dict[int, str], evil_count: int, good_count: int) -> bool:
        return evil_count >= good_count and evil_count > 0

    def can_act_at_night(self) -> bool:
        return True

    def night_action_type(self) -> str | None:
        return "kill"

    def get_goal_description(self) -> str:
        return (
            "你是狼人。夜晚与狼队友协商击杀目标；白天伪装成好人，"
            "引导投票淘汰神职或村民，直至狼人数量≥存活好人数量。"
        )

    def get_private_info(self, player_id: int, game_state: dict) -> str:
        teammates = game_state.get("werewolf_teammates", [])
        ids = [p for p in teammates if p != player_id]
        if ids:
            return f"你的狼队友编号：{ids}"
        return "你是唯一的狼人（或队友已出局）。"

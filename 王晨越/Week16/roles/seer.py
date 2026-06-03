"""预言家角色：夜晚查验一名玩家阵营。"""

from roles.base import BaseRole, Camp, RoleType


class SeerRole(BaseRole):
    role_type = RoleType.SEER
    camp = Camp.GOOD

    def win_condition(self, alive_roles: dict[int, str], evil_count: int, good_count: int) -> bool:
        return evil_count == 0 and good_count > 0

    def can_act_at_night(self) -> bool:
        return True

    def night_action_type(self) -> str | None:
        return "check"

    def get_goal_description(self) -> str:
        return "你是预言家。每夜查验一名玩家是「好人」还是「狼人」，白天合理公布信息引导投票。"

    def get_private_info(self, player_id: int, game_state: dict) -> str:
        checks = game_state.get("seer_checks", {})
        if not checks:
            return "你尚未查验过任何玩家。"
        lines = [f"玩家{p}：{result}" for p, result in checks.items()]
        return "历史查验记录：\n" + "\n".join(lines)

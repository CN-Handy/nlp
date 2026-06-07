"""猎人角色：被投票出局或被狼杀时可开枪带走一人（本实现简化为出局时）。"""

from roles.base import BaseRole, Camp, RoleType


class HunterRole(BaseRole):
    role_type = RoleType.HUNTER
    camp = Camp.GOOD

    def win_condition(self, alive_roles: dict[int, str], evil_count: int, good_count: int) -> bool:
        return evil_count == 0 and good_count > 0

    def can_act_at_day(self) -> bool:
        return True  # 出局时可开枪

    def get_goal_description(self) -> str:
        return "你是猎人。出局时可开枪带走一名玩家（限一次），谨慎选择目标。"

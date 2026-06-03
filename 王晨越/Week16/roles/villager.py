"""村民角色：无夜间技能，靠白天发言与投票。"""

from roles.base import BaseRole, Camp, RoleType


class VillagerRole(BaseRole):
    role_type = RoleType.VILLAGER
    camp = Camp.GOOD

    def win_condition(self, alive_roles: dict[int, str], evil_count: int, good_count: int) -> bool:
        return evil_count == 0 and good_count > 0

    def get_goal_description(self) -> str:
        return "你是村民。无特殊技能，通过观察发言与投票逻辑，协助找出狼人。"

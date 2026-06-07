"""角色基类：定义阵营、目标、夜间/白天行动空间与信息可见性。"""

from abc import ABC, abstractmethod
from enum import Enum


class Camp(str, Enum):
    """阵营"""

    GOOD = "good"  # 好人阵营
    EVIL = "evil"  # 狼人阵营


class RoleType(str, Enum):
    """角色类型标识"""

    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"


# 角色中文名映射
ROLE_CN: dict[str, str] = {
    RoleType.WEREWOLF: "狼人",
    RoleType.SEER: "预言家",
    RoleType.WITCH: "女巫",
    RoleType.HUNTER: "猎人",
    RoleType.VILLAGER: "村民",
}

CAMP_CN: dict[str, str] = {
    Camp.GOOD: "好人阵营",
    Camp.EVIL: "狼人阵营",
}


class BaseRole(ABC):
    """所有角色的抽象基类"""

    role_type: RoleType
    camp: Camp

    @property
    def name_cn(self) -> str:
        return ROLE_CN[self.role_type.value]

    @abstractmethod
    def win_condition(self, alive_roles: dict[int, str], evil_count: int, good_count: int) -> bool:
        """
        判断本阵营是否已达成胜利条件。
        alive_roles: {player_id: role_type}
        """

    def can_act_at_night(self) -> bool:
        """是否能在夜晚行动"""
        return False

    def can_act_at_day(self) -> bool:
        """白天是否拥有特殊行动（除发言/投票外）"""
        return False

    def night_action_type(self) -> str | None:
        """夜晚行动类型标识，如 kill / check / poison / save"""
        return None

    def get_private_info(self, player_id: int, game_state: dict) -> str:
        """返回该角色可见的私有信息摘要（供 Agent prompt 使用）"""
        return ""

    def get_goal_description(self) -> str:
        """角色目标描述，写入 Agent 系统提示"""
        if self.camp == Camp.GOOD:
            return "找出并投票淘汰所有狼人，保护好人阵营获胜。"
        return "隐藏身份，与狼队友配合，使狼人数量不少于好人数量。"

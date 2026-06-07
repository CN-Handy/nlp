"""女巫角色：拥有一瓶解药和一瓶毒药（各用一次）。"""

from roles.base import BaseRole, Camp, RoleType


class WitchRole(BaseRole):
    role_type = RoleType.WITCH
    camp = Camp.GOOD

    def win_condition(self, alive_roles: dict[int, str], evil_count: int, good_count: int) -> bool:
        return evil_count == 0 and good_count > 0

    def can_act_at_night(self) -> bool:
        return True

    def night_action_type(self) -> str | None:
        return "witch"

    def get_goal_description(self) -> str:
        return (
            "你是女巫。拥有一瓶解药（救被狼杀者，首夜可自救）和一瓶毒药（毒杀一人），"
            "各限用一次。合理用药帮助好人阵营。"
        )

    def get_private_info(self, player_id: int, game_state: dict) -> str:
        save_used = game_state.get("witch_save_used", False)
        poison_used = game_state.get("witch_poison_used", False)
        return f"解药：{'已用' if save_used else '可用'}；毒药：{'已用' if poison_used else '可用'}"

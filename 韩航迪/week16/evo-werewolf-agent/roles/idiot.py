"""白痴角色实现。

阵营：善良阵营
胜利条件：消灭所有狼人
被动技能：被投票出局时不会死亡，而是翻开身份牌证明自己是好人
         翻开身份后不能参与投票，但仍可发言
"""

from typing import Dict, Any, Optional, List
from roles.base import BaseRole, RoleType, Camp


class Idiot(BaseRole):
    """Idiot role - belongs to good camp.

    Win Condition: Eliminate all wolves.
    Passive Ability: When voted out, reveals identity and stays alive
                     but loses voting rights. Can still speak.
    Cannot be killed by vote.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id)
        self._revealed = False  # 是否已翻开身份
        self._can_vote = True   # 翻牌后失去投票权

    @property
    def role_type(self) -> RoleType:
        return RoleType.VILLAGER  # 白痴算村民阵营

    @property
    def camp(self) -> Camp:
        return Camp.GOOD

    @property
    def name(self) -> str:
        return "白痴"

    @property
    def is_revealed(self) -> bool:
        return self._revealed

    def reveal(self):
        """翻开身份牌"""
        self._revealed = True
        self._can_vote = False

    def is_night_actionable(self) -> bool:
        """白痴没有夜间行动"""
        return False

    def can_vote(self) -> bool:
        """翻牌后失去投票权"""
        return self._is_alive and self._can_vote

    def can_speak(self) -> bool:
        """翻牌后仍可发言"""
        return self._is_alive

    def on_death(self, cause: str, game_state: Dict[str, Any]) -> Optional[List[int]]:
        """白痴被投票出局时翻牌存活"""
        if cause == "vote" and not self._revealed:
            # 翻牌：不死亡，但失去投票权
            self.reveal()
            return []  # 表示翻牌了
        # 夜晚被杀或毒杀则正常死亡
        self._is_alive = False
        return None

    def get_private_context(self) -> Dict[str, Any]:
        ctx = super().get_private_context()
        ctx.update({
            "note": "你是白痴（Idiot）。如果你被投票出局，你将翻开身份牌证明自己是好人，不会死亡，但失去投票权。被狼人杀害或毒杀则正常死亡。",
            "is_revealed": self._revealed,
            "can_vote": self._can_vote,
        })
        return ctx

    def check_win(self, game_state: Dict[str, Any]) -> bool:
        """Good camp wins when all wolves eliminated."""
        players = game_state.get("players", [])
        alive_wolves = [
            p for p in players
            if p.get("role") == RoleType.WEREWOLF.value and p.get("is_alive")
        ]
        return len(alive_wolves) == 0

    def __repr__(self) -> str:
        status = "alive" if self._is_alive else "dead"
        revealed = " (revealed)" if self._revealed else ""
        return f"Idiot(player_id={self.player_id}, {status}{revealed})"

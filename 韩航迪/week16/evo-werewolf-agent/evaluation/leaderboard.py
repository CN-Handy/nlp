"""Leaderboard 排行榜

支持多维排行：
- 按角色排行（狼人榜、预言家榜等）
- 按模型排行
- 全局综合排行
- 按决策风格排行
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


LEADERBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LEADERBOARD_FILE = os.path.join(LEADERBOARD_DIR, "leaderboard.json")


@dataclass
class LeaderboardEntry:
    """排行榜条目"""
    player_name: str
    role_type: str
    model: str = "qwen-flash"
    decision_style: str = "balanced"

    # 统计
    games_played: int = 0
    games_won: int = 0
    total_score: float = 0.0

    # 平均指标
    avg_overall_score: float = 0.0
    avg_vote_accuracy: float = 0.0
    avg_survival: float = 0.0
    avg_speech_length: float = 0.0

    # 特殊成就
    mvp_count: int = 0  # 单局最高分次数
    clutch_count: int = 0  # 关键翻盘次数

    def update_from_metrics(self, metrics: Dict[str, Any]) -> None:
        """从单局指标更新统计"""
        self.games_played += 1
        if metrics.get("is_winner"):
            self.games_won += 1
        self.total_score += metrics.get("overall_score", 0)
        self.avg_overall_score = self.total_score / self.games_played
        self.avg_vote_accuracy = (
            self.avg_vote_accuracy * (self.games_played - 1) +
            metrics.get("vote_accuracy", 0)
        ) / self.games_played
        self.avg_survival = (
            self.avg_survival * (self.games_played - 1) +
            metrics.get("survived_rounds_pct", 0)
        ) / self.games_played
        self.avg_speech_length = (
            self.avg_speech_length * (self.games_played - 1) +
            metrics.get("avg_speech_length", 0)
        ) / self.games_played

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.0
        return self.games_won / self.games_played

    @property
    def composite_score(self) -> float:
        """综合评分（用于排名）"""
        return (
            self.win_rate * 40 +
            self.avg_overall_score * 0.3 +
            self.avg_vote_accuracy * 20 +
            self.avg_survival * 0.1 +
            self.mvp_count * 5 +
            self.clutch_count * 10
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_name": self.player_name,
            "role_type": self.role_type,
            "model": self.model,
            "decision_style": self.decision_style,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "win_rate": round(self.win_rate, 3),
            "avg_overall_score": round(self.avg_overall_score, 1),
            "avg_vote_accuracy": round(self.avg_vote_accuracy, 3),
            "avg_survival": round(self.avg_survival, 1),
            "avg_speech_length": round(self.avg_speech_length, 1),
            "mvp_count": self.mvp_count,
            "clutch_count": self.clutch_count,
            "composite_score": round(self.composite_score, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeaderboardEntry":
        entry = cls(
            player_name=data.get("player_name", ""),
            role_type=data.get("role_type", ""),
            model=data.get("model", "qwen-flash"),
            decision_style=data.get("decision_style", "balanced"),
            games_played=data.get("games_played", 0),
            games_won=data.get("games_won", 0),
            total_score=data.get("avg_overall_score", 0) * data.get("games_played", 1),
            avg_overall_score=data.get("avg_overall_score", 0),
            avg_vote_accuracy=data.get("avg_vote_accuracy", 0),
            avg_survival=data.get("avg_survival", 0),
            avg_speech_length=data.get("avg_speech_length", 0),
            mvp_count=data.get("mvp_count", 0),
            clutch_count=data.get("clutch_count", 0),
        )
        return entry


class Leaderboard:
    """排行榜管理"""

    def __init__(self):
        self.entries: Dict[str, Dict[str, LeaderboardEntry]] = {}  # role_type -> key -> entry
        self._load()

    def _make_key(self, entry_data: Dict[str, Any]) -> str:
        """生成唯一标识"""
        return f"{entry_data.get('model', 'unknown')}:{entry_data.get('decision_style', 'unknown')}"

    def _load(self) -> None:
        """从磁盘加载排行榜"""
        if not os.path.exists(LEADERBOARD_FILE):
            return
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for role_type, entries_dict in data.items():
                self.entries[role_type] = {}
                for key, entry_data in entries_dict.items():
                    self.entries[role_type][key] = LeaderboardEntry.from_dict(entry_data)
        except (json.JSONDecodeError, IOError):
            pass

    def save(self) -> None:
        """保存排行榜到磁盘"""
        os.makedirs(LEADERBOARD_DIR, exist_ok=True)
        data = {}
        for role_type, entries_dict in self.entries.items():
            data[role_type] = {key: entry.to_dict() for key, entry in entries_dict.items()}
        with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_from_game(self, game_metrics: Any) -> None:
        """从一局游戏的评测结果更新排行榜"""
        for pm in game_metrics.player_metrics:
            role = pm.role
            if role not in self.entries:
                self.entries[role] = {}

            entry_key = "qwen-flash:balanced"  # 默认
            if entry_key not in self.entries[role]:
                self.entries[role][entry_key] = LeaderboardEntry(
                    player_name=pm.player_name,
                    role_type=role,
                )

            entry = self.entries[role][entry_key]
            entry.update_from_metrics(pm.to_dict())
            # 更新名称
            entry.player_name = pm.player_name

        # 更新MVP
        if game_metrics.player_metrics:
            mvp = max(game_metrics.player_metrics, key=lambda pm: pm.overall_score)
            role = mvp.role
            key = "qwen-flash:balanced"
            if role in self.entries and key in self.entries[role]:
                self.entries[role][key].mvp_count += 1

        self.save()

    def get_rankings(
        self,
        role_type: Optional[str] = None,
        sort_by: str = "composite_score",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """获取排行榜

        Args:
            role_type: 按角色筛选，None表示全部
            sort_by: 排序字段
            limit: 返回数量

        Returns:
            排行列表
        """
        all_entries = []
        if role_type and role_type in self.entries:
            for key, entry in self.entries[role_type].items():
                all_entries.append(entry.to_dict())
        elif not role_type:
            for rt, entries_dict in self.entries.items():
                for key, entry in entries_dict.items():
                    d = entry.to_dict()
                    d["role_type"] = rt
                    all_entries.append(d)

        all_entries.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        return all_entries[:limit]

    def get_role_comparison(self) -> Dict[str, Any]:
        """获取不同角色之间的对比数据"""
        comparison = {}
        for role_type, entries_dict in self.entries.items():
            if not entries_dict:
                continue
            avg_win_rate = sum(e.win_rate for e in entries_dict.values()) / len(entries_dict)
            avg_score = sum(e.avg_overall_score for e in entries_dict.values()) / len(entries_dict)
            total_games = sum(e.games_played for e in entries_dict.values())
            comparison[role_type] = {
                "avg_win_rate": round(avg_win_rate, 3),
                "avg_score": round(avg_score, 1),
                "total_games": total_games,
                "entries": len(entries_dict),
            }
        return comparison

    def get_trend(self, role_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取趋势数据（简化版，返回排行变化）"""
        return self.get_rankings(role_type=role_type, limit=10)


# 全局单例
_leaderboard: Optional[Leaderboard] = None


def get_leaderboard() -> Leaderboard:
    """获取排行榜单例"""
    global _leaderboard
    if _leaderboard is None:
        _leaderboard = Leaderboard()
    return _leaderboard

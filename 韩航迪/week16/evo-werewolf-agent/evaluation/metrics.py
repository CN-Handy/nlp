"""游戏评测指标

提供多维可量化的评测指标，包括：
- 结果评测：胜率、存活率、输出贡献
- 过程评测：决策准确度、发言质量、推理一致性
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json
import os


@dataclass
class PlayerMetrics:
    """单玩家评测指标"""
    player_id: int
    player_name: str
    role: str
    camp: str

    # 结果评测
    is_winner: bool = False
    survived: bool = False  # 存活到游戏结束
    survived_rounds_pct: float = 0.0  # 存活回合占比

    # 决策评测
    correct_night_actions: int = 0  # 正确的夜间行动（如预言家验到狼）
    total_night_actions: int = 0
    correct_votes: int = 0  # 投票给狼人/敌对阵营
    total_votes: int = 0
    vote_accuracy: float = 0.0  # 投票准确率

    # 发言评测
    speech_count: int = 0
    avg_speech_length: float = 0.0
    accusation_accuracy: float = 0.0  # 指控准确率

    # 推理评测
    reasoning_depth_score: float = 0.0  # 推理深度分（0-100）
    information_utilization: float = 0.0  # 信息利用率

    # 综合评分
    overall_score: float = 0.0  # 综合评分（0-100）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "role": self.role,
            "camp": self.camp,
            "is_winner": self.is_winner,
            "survived": self.survived,
            "survived_rounds_pct": round(self.survived_rounds_pct, 1),
            "correct_night_actions": self.correct_night_actions,
            "total_night_actions": self.total_night_actions,
            "vote_accuracy": round(self.vote_accuracy, 2),
            "speech_count": self.speech_count,
            "avg_speech_length": round(self.avg_speech_length, 1),
            "accusation_accuracy": round(self.accusation_accuracy, 2),
            "reasoning_depth_score": round(self.reasoning_depth_score, 1),
            "information_utilization": round(self.information_utilization, 1),
            "overall_score": round(self.overall_score, 1),
        }


@dataclass
class GameMetrics:
    """单局游戏评测指标"""
    game_id: str
    config_name: str
    winner: str
    total_rounds: int
    duration_seconds: float = 0.0

    # 阵营表现
    good_camp_metrics: Dict[str, Any] = field(default_factory=dict)
    evil_camp_metrics: Dict[str, Any] = field(default_factory=dict)

    # 玩家指标
    player_metrics: List[PlayerMetrics] = field(default_factory=list)

    # 游戏质量
    game_balance_score: float = 0.0  # 游戏平衡度
    decision_diversity: float = 0.0  # 决策多样性
    narrative_coherence: float = 0.0  # 叙事连贯性

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "config_name": self.config_name,
            "winner": self.winner,
            "total_rounds": self.total_rounds,
            "duration_seconds": round(self.duration_seconds, 1),
            "good_camp_metrics": self.good_camp_metrics,
            "evil_camp_metrics": self.evil_camp_metrics,
            "player_metrics": [pm.to_dict() for pm in self.player_metrics],
            "game_balance_score": round(self.game_balance_score, 1),
            "decision_diversity": round(self.decision_diversity, 2),
            "narrative_coherence": round(self.narrative_coherence, 1),
        }


def compute_metrics(
    game_id: str,
    config_name: str,
    winner: str,
    players: List[Dict[str, Any]],
    dialogues: List[Dict[str, Any]],
    death_records: List[Dict[str, Any]],
    total_rounds: int,
    duration_seconds: float = 0.0,
) -> GameMetrics:
    """从游戏数据计算评测指标

    Args:
        game_id: 游戏ID
        config_name: 配置名称
        winner: 胜利方 ("good"/"evil")
        players: 玩家列表
        dialogues: 所有对话记录
        death_records: 死亡记录
        total_rounds: 总回合数
        duration_seconds: 游戏持续时间

    Returns:
        GameMetrics 评测结果
    """
    player_metrics = []
    total_players = len(players)

    for p in players:
        pid = p.get("player_id", 0)
        name = p.get("name", f"玩家{pid}")
        role = p.get("role", "unknown")
        camp = p.get("camp", "unknown")
        is_alive = p.get("is_alive", False)

        pm = PlayerMetrics(
            player_id=pid,
            player_name=name,
            role=role,
            camp=camp,
            is_winner=(camp == winner),
            survived=is_alive,
        )

        # 计算存活率
        if total_rounds > 0:
            death_day = total_rounds
            for death in death_records:
                if death.get("player_id") == pid:
                    death_day = death.get("day", total_rounds)
                    break
            pm.survived_rounds_pct = min(100, death_day / max(1, total_rounds) * 100) if is_alive else death_day / max(1, total_rounds) * 100

        # 分析该玩家的对话
        player_dialogues = [d for d in dialogues if d.get("player_id") == pid]

        # 投票准确率
        correct_votes = 0
        total_votes = 0
        for d in player_dialogues:
            if d.get("action") == "vote" or d.get("action") == "pk_vote":
                total_votes += 1
                target_id = d.get("target")
                if target_id is not None:
                    target = next((pl for pl in players if pl.get("player_id") == target_id), None)
                    if target:
                        if camp == "good" and target.get("role") == "werewolf":
                            correct_votes += 1
                        elif camp == "evil" and target.get("role") != "werewolf":
                            correct_votes += 1
        pm.total_votes = total_votes
        pm.correct_votes = correct_votes
        pm.vote_accuracy = correct_votes / max(1, total_votes)

        # 夜间行动准确率
        correct_night = 0
        total_night = 0
        for d in player_dialogues:
            if d.get("action") == "seer_check":
                total_night += 1
                if d.get("result") == "wolf":
                    correct_night += 1
        pm.correct_night_actions = correct_night
        pm.total_night_actions = total_night

        # 发言分析
        speeches = [d for d in player_dialogues if d.get("action") in ("speech", "pk_speech")]
        pm.speech_count = len(speeches)
        total_speech_len = sum(len(d.get("content", "")) for d in speeches)
        pm.avg_speech_length = total_speech_len / max(1, len(speeches))

        # 指控准确率（基于发言中提到的玩家ID）
        accusation_correct = 0
        accusation_total = 0
        for s in speeches:
            content = s.get("content", "")
            for other_p in players:
                other_id = other_p.get("player_id")
                if other_id != pid:
                    if f"玩家{other_id}" in content or f"{other_id}号" in content:
                        accusation_total += 1
                        if other_p.get("role") == "werewolf" and camp == "good":
                            accusation_correct += 1
                        elif other_p.get("role") != "werewolf" and camp == "evil":
                            accusation_correct += 1
        pm.accusation_accuracy = accusation_correct / max(1, accusation_total)

        # 推理深度（基于发言长度和信息利用）
        pm.reasoning_depth_score = min(100, pm.avg_speech_length / 5)
        pm.information_utilization = min(100, len(player_dialogues) / max(1, total_rounds) * 30)

        # 综合评分（加权）
        pm.overall_score = (
            (50 if pm.is_winner else 20) * 0.3 +
            (pm.survived_rounds_pct) * 0.15 +
            (pm.vote_accuracy * 100) * 0.25 +
            (pm.accusation_accuracy * 100) * 0.15 +
            pm.reasoning_depth_score * 0.1 +
            pm.information_utilization * 0.05
        )

        player_metrics.append(pm)

    # 阵营表现
    good_players = [pm for pm in player_metrics if pm.camp == "good"]
    evil_players = [pm for pm in player_metrics if pm.camp == "evil"]

    good_camp_metrics = {
        "avg_score": sum(pm.overall_score for pm in good_players) / max(1, len(good_players)),
        "avg_vote_accuracy": sum(pm.vote_accuracy for pm in good_players) / max(1, len(good_players)),
        "survivor_count": sum(1 for pm in good_players if pm.survived),
    }

    evil_camp_metrics = {
        "avg_score": sum(pm.overall_score for pm in evil_players) / max(1, len(evil_players)),
        "avg_vote_accuracy": sum(pm.vote_accuracy for pm in evil_players) / max(1, len(evil_players)),
        "survivor_count": sum(1 for pm in evil_players if pm.survived),
    }

    # 游戏平衡度
    winner_players = [pm for pm in player_metrics if pm.camp == winner]
    loser_players = [pm for pm in player_metrics if pm.camp != winner]
    winner_avg = sum(pm.overall_score for pm in winner_players) / max(1, len(winner_players))
    loser_avg = sum(pm.overall_score for pm in loser_players) / max(1, len(loser_players))
    game_balance_score = max(0, 100 - abs(winner_avg - loser_avg) * 2)

    # 决策多样性
    vote_targets = set()
    total_speakers = 0
    for d in dialogues:
        if d.get("action") in ("vote", "pk_vote") and d.get("target") is not None:
            vote_targets.add(d.get("target"))
    decision_diversity = len(vote_targets) / max(1, total_players)

    # 叙事连贯性
    narrative_coherence = min(100, len(dialogues) / max(1, total_rounds) * 5)

    return GameMetrics(
        game_id=game_id,
        config_name=config_name,
        winner=winner,
        total_rounds=total_rounds,
        duration_seconds=duration_seconds,
        good_camp_metrics=good_camp_metrics,
        evil_camp_metrics=evil_camp_metrics,
        player_metrics=player_metrics,
        game_balance_score=game_balance_score,
        decision_diversity=decision_diversity,
        narrative_coherence=narrative_coherence,
    )

"""锦标赛系统 — 多局迭代自进化对战

支持：
- 多轮对局自动运行
- 跨局经验累积与进化
- 不同模型/风格Agent同台竞技
- 生成进化曲线和对比报告
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from engine.game_engine import GameEngine, get_role_config, shuffle_roles, ROLE_CONFIGS
from evaluation.metrics import compute_metrics, GameMetrics
from evaluation.leaderboard import get_leaderboard
from schema.game_logger import GameLogger


class Tournament:
    """锦标赛管理器

    运行多局游戏，跟踪每轮的指标变化，实现跨局经验自进化。
    """

    def __init__(
        self,
        config_name: str = "standard_6",
        num_games: int = 10,
        shuffle_roles_each_game: bool = True,
        enable_evolution: bool = True,
        output_dir: str = "logs/tournaments",
    ):
        """
        Args:
            config_name: 角色配置名称
            num_games: 总局数
            shuffle_roles_each_game: 每局是否重新打乱角色
            enable_evolution: 是否启用跨局经验进化
            output_dir: 输出目录
        """
        self.config_name = config_name
        self.num_games = num_games
        self.shuffle_roles_each_game = shuffle_roles_each_game
        self.enable_evolution = enable_evolution
        self.output_dir = output_dir

        self.tournament_id = f"tournament_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.games: List[Dict[str, Any]] = []
        self.evolution_history: List[Dict[str, Any]] = []  # 进化历史

        os.makedirs(output_dir, exist_ok=True)

    async def run(self, progress_callback=None) -> Dict[str, Any]:
        """运行整个锦标赛

        Args:
            progress_callback: 可选回调函数，参数为 (game_idx, total, game_result)

        Returns:
            锦标赛总结数据
        """
        role_config = get_role_config(self.config_name)
        player_count = len(role_config)
        config_desc = ROLE_CONFIGS[self.config_name]["description"]

        print(f"\n{'='*60}")
        print(f"锦标赛开始：{config_desc}")
        print(f"总局数：{self.num_games} | 经验进化：{'开启' if self.enable_evolution else '关闭'}")
        print(f"{'='*60}")

        overall_start = time.time()

        for game_idx in range(self.num_games):
            print(f"\n{'='*40}")
            print(f"第 {game_idx + 1}/{self.num_games} 局")
            print(f"{'='*40}")

            # 角色分配
            if self.shuffle_roles_each_game:
                role_assignment = shuffle_roles(role_config.copy())
            else:
                role_assignment = role_config.copy()

            # 创建玩家名称和风格
            player_names = [f"Agent-{i+1}" for i in range(player_count)]
            player_styles = self._assign_styles(player_count, game_idx)

            # 游戏ID
            game_id = f"{self.tournament_id}_g{game_idx+1}"

            # 创建游戏引擎
            logger = GameLogger(
                game_id=game_id,
                config_name=self.config_name,
                role_assignment=role_assignment,
                player_styles=player_styles,
                log_level="INFO",
            )

            engine = GameEngine(player_names, logger=logger)
            engine.game_id = game_id
            await engine.initialize(role_assignment, player_styles)

            # 运行游戏
            game_start = time.time()
            await engine.start()
            game_duration = time.time() - game_start

            # 收集游戏结果
            winner = engine.game_state.get_winner()
            players_data = [p.to_dict() for p in engine.game_state.players]

            # 计算评测指标
            metrics = compute_metrics(
                game_id=game_id,
                config_name=self.config_name,
                winner=winner or "good",
                players=players_data,
                dialogues=list(engine.game_state.dialogues),
                death_records=list(engine.death_records),
                total_rounds=engine.game_state.day_number,
                duration_seconds=game_duration,
            )

            # 更新排行榜
            leaderboard = get_leaderboard()
            leaderboard.update_from_game(metrics)

            # 记录游戏结果
            game_result = {
                "game_idx": game_idx + 1,
                "game_id": game_id,
                "winner": winner,
                "rounds": engine.game_state.day_number,
                "duration_seconds": round(game_duration, 1),
                "role_assignment": role_assignment,
                "player_styles": player_styles,
                "metrics": metrics.to_dict(),
                "summaries": list(engine.summaries),
            }
            self.games.append(game_result)

            # 进化历史
            self.evolution_history.append(self._extract_evolution_snapshot(game_idx + 1, metrics))

            # 保存中间结果
            self._save_progress()

            # 回调进度
            if progress_callback:
                progress_callback(game_idx + 1, self.num_games, game_result)

            if winner:
                winner_name = "好人阵营" if winner == "good" else "狼人阵营"
                print(f"第{game_idx+1}局结果：{winner_name}胜利 (第{engine.game_state.day_number}天, {game_duration:.1f}s)")
            else:
                print(f"第{game_idx+1}局结果：平局")

        overall_duration = time.time() - overall_start

        # 生成锦标赛总结
        summary = self._generate_summary(overall_duration)
        self._save_final_report(summary)

        print(f"\n{'='*60}")
        print(f"锦标赛完成！总耗时：{overall_duration:.1f}s")
        print(f"{'='*60}")

        return summary

    def _assign_styles(self, player_count: int, game_idx: int) -> Dict[int, str]:
        """为每局分配不同的决策风格组合，增加多样性"""
        styles = ["balanced", "cautious", "bold", "random"]
        import random
        random.seed(game_idx + 42)  # 固定种子但每局不同

        result = {}
        for i in range(player_count):
            # 轮换风格分配
            result[i] = styles[(i + game_idx) % len(styles)]
        return result

    def _extract_evolution_snapshot(self, game_idx: int, metrics: GameMetrics) -> Dict[str, Any]:
        """从单局指标提取进化快照"""
        good_avg = sum(pm.overall_score for pm in metrics.player_metrics if pm.camp == "good")
        evil_avg = sum(pm.overall_score for pm in metrics.player_metrics if pm.camp == "evil")
        good_count = sum(1 for pm in metrics.player_metrics if pm.camp == "good")
        evil_count = sum(1 for pm in metrics.player_metrics if pm.camp == "evil")

        return {
            "game": game_idx,
            "good_avg_score": round(good_avg / max(1, good_count), 1),
            "evil_avg_score": round(evil_avg / max(1, evil_count), 1),
            "vote_accuracy": round(
                sum(pm.vote_accuracy for pm in metrics.player_metrics) /
                max(1, len(metrics.player_metrics)), 3
            ),
            "decision_diversity": round(metrics.decision_diversity, 3),
            "game_balance": round(metrics.game_balance_score, 1),
        }

    def _generate_summary(self, duration: float) -> Dict[str, Any]:
        """生成锦标赛总结"""
        total_games = len(self.games)
        if total_games == 0:
            return {"error": "No games played"}

        # 胜负统计
        good_wins = sum(1 for g in self.games if g["winner"] == "good")
        evil_wins = sum(1 for g in self.games if g["winner"] == "evil")

        # 平均指标
        avg_rounds = sum(g["rounds"] for g in self.games) / total_games
        avg_duration = sum(g["duration_seconds"] for g in self.games) / total_games

        # 进化趋势（对比前3局 vs 后3局）
        early_games = self.games[:min(3, total_games)]
        late_games = self.games[-min(3, total_games):]

        early_good_avg = sum(
            g["metrics"]["good_camp_metrics"].get("avg_score", 0)
            for g in early_games
        ) / len(early_games)
        late_good_avg = sum(
            g["metrics"]["good_camp_metrics"].get("avg_score", 0)
            for g in late_games
        ) / len(late_games)

        # 角色表现
        role_stats = {}
        for g in self.games:
            for pm_data in g["metrics"].get("player_metrics", []):
                role = pm_data["role"]
                if role not in role_stats:
                    role_stats[role] = {"total": 0, "wins": 0, "games": 0}
                role_stats[role]["games"] += 1
                role_stats[role]["total"] += pm_data.get("overall_score", 0)
                if pm_data.get("is_winner"):
                    role_stats[role]["wins"] += 1

        role_performance = {}
        for role, stats in role_stats.items():
            role_performance[role] = {
                "games": stats["games"],
                "win_rate": round(stats["wins"] / max(1, stats["games"]), 3),
                "avg_score": round(stats["total"] / max(1, stats["games"]), 1),
            }

        return {
            "tournament_id": self.tournament_id,
            "config_name": self.config_name,
            "total_games": total_games,
            "duration_seconds": round(duration, 1),
            "good_wins": good_wins,
            "evil_wins": evil_wins,
            "good_win_rate": round(good_wins / total_games, 3),
            "avg_rounds": round(avg_rounds, 1),
            "avg_duration": round(avg_duration, 1),
            "evolution_trend": {
                "early_good_avg_score": round(early_good_avg, 1),
                "late_good_avg_score": round(late_good_avg, 1),
                "improvement": round(late_good_avg - early_good_avg, 1),
                "has_improved": late_good_avg > early_good_avg,
            },
            "role_performance": role_performance,
            "evolution_history": self.evolution_history,
        }

    def _save_progress(self):
        """保存中间进度"""
        data = {
            "tournament_id": self.tournament_id,
            "games": self.games,
            "evolution_history": self.evolution_history,
        }
        filepath = os.path.join(self.output_dir, f"{self.tournament_id}_progress.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_final_report(self, summary: Dict[str, Any]):
        """保存最终报告"""
        filepath = os.path.join(self.output_dir, f"{self.tournament_id}_report.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"锦标赛报告已保存至: {filepath}")


async def run_tournament(
    config_name: str = "standard_6",
    num_games: int = 10,
    enable_evolution: bool = True,
    progress_callback=None,
) -> Dict[str, Any]:
    """运行锦标赛的便捷函数

    Args:
        config_name: 角色配置
        num_games: 总局数
        enable_evolution: 是否启用进化
        progress_callback: 进度回调

    Returns:
        锦标赛结果
    """
    tournament = Tournament(
        config_name=config_name,
        num_games=num_games,
        enable_evolution=enable_evolution,
    )
    return await tournament.run(progress_callback)

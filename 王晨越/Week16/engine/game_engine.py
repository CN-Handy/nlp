"""对局引擎：主持人逻辑，驱动回合流转、信息隔离与胜负裁决。"""

from __future__ import annotations

import random
from collections import Counter
from datetime import datetime
from typing import Callable

from agent.player_agent import PlayerAgent, player_display_name
from agent.summary_agent import SummaryAgent
from configs.game_configs import get_config
from memory.experience import ExperienceStore
from roles import ROLE_REGISTRY
from roles.base import Camp, ROLE_CN
from schema.dialogue import DialogueRecord, PhaseType
from schema.game import DeathRecord, GameConfig, GameRecord, GameState, PlayerStyle

ProgressCallback = Callable[[DialogueRecord], None] | None


class GameEngine:
    """狼人杀对局引擎；支持自动推进与逐步手动推进。"""

    def __init__(
        self,
        config: GameConfig | None = None,
        config_name: str = "standard_6",
        experience_store: ExperienceStore | None = None,
        on_dialogue: ProgressCallback = None,
    ) -> None:
        self.config = config or get_config(config_name)
        self.experience = experience_store or ExperienceStore()
        self.on_dialogue = on_dialogue
        self.game_id = ""
        self.day = 0
        self.phase = "未开始"
        self.alive: list[int] = []
        self.dead: list[int] = []
        self.role_assignment: dict[int, str] = {}
        self.agents: dict[int, PlayerAgent] = {}
        self.dialogues: list[DialogueRecord] = []
        self.death_order: list[DeathRecord] = []
        self.winner: str | None = None
        self.is_paused = False
        self.is_finished = False
        self._pending_step: str | None = None  # 手动模式下的待执行步骤
        self.record: GameRecord | None = None

        # 运行时私有状态
        self._werewolf_teammates: list[int] = []
        self._seer_checks: dict[int, str] = {}
        self._witch_save_used = False
        self._witch_poison_used = False
        self._hunter_can_shoot: dict[int, bool] = {}
        self._night_kill_target: int | None = None
        self._witch_saved = False

    def setup(self, game_id: str | None = None) -> GameRecord:
        """初始化一局：洗牌分配角色与风格"""
        self.game_id = game_id or f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        roles = list(self.config.roles)
        random.shuffle(roles)
        n = self.config.player_count
        self.role_assignment = {i: roles[i] for i in range(n)}
        self.alive = list(range(n))
        self.dead = []
        self.dialogues = []
        self.death_order = []
        self.winner = None
        self.is_finished = False
        self.is_paused = not self.config.auto_run
        self.day = 0
        self.phase = "准备中"

        styles: dict[int, PlayerStyle] = {}
        style_pool = list(PlayerStyle)
        for i in range(n):
            styles[i] = self.config.player_styles.get(i, random.choice(style_pool))
        self.config.player_styles = styles

        self.agents = {}
        for pid, role in self.role_assignment.items():
            self.agents[pid] = PlayerAgent(pid, role, styles[pid])

        self._werewolf_teammates = [p for p, r in self.role_assignment.items() if r == "werewolf"]
        self._seer_checks = {}
        self._witch_save_used = False
        self._witch_poison_used = False
        self._hunter_can_shoot = {p: True for p, r in self.role_assignment.items() if r == "hunter"}

        self.record = GameRecord(
            game_id=self.game_id,
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            end_time=None,
            config_name=self.config.name,
            role_assignment=dict(self.role_assignment),
            player_styles={k: v.value for k, v in styles.items()},
        )

        self._emit_system("游戏开始！角色已秘密分配。")
        for pid, role in self.role_assignment.items():
            vis = self._werewolf_teammates if role == "werewolf" else [pid]
            self._add_dialogue(
                PhaseType.SYSTEM,
                0,
                f"{player_display_name(pid, role)} 已就位。",
                visible_to=vis if role == "werewolf" else [pid],
                speaker_id=None,
                speaker_name="系统",
            )
        return self.record

    def get_state(self) -> GameState:
        return GameState(
            game_id=self.game_id,
            day=self.day,
            phase=self.phase,
            alive_players=list(self.alive),
            dead_players=list(self.dead),
            role_assignment={k: v for k, v in self.role_assignment.items()},
            winner=self.winner,
            is_paused=self.is_paused,
            is_finished=self.is_finished,
            recent_dialogues=self.dialogues[-30:],
        )

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def run_to_end(self) -> GameRecord:
        """自动跑完全局"""
        self.is_paused = False
        while not self.is_finished:
            self.step()
        return self.finalize()

    def step(self) -> bool:
        """推进一步（一夜+一日）；返回 False 表示已结束"""
        if self.is_finished:
            return False
        if self.day == 0:
            self.day = 1
        else:
            self.day += 1
        self._run_night()
        if self.is_finished:
            return False
        self._check_win()
        if self.is_finished:
            return False
        self._run_day()
        self._check_win()
        return not self.is_finished

    def finalize(self) -> GameRecord:
        if not self.record:
            raise RuntimeError("请先 setup()")
        if self.record.end_time:
            return self.record
        self.record.dialogues = list(self.dialogues)
        self.record.winner = self.winner
        self.record.death_order = list(self.death_order)
        self.record.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary_agent = SummaryAgent(store=self.experience)
        summaries = summary_agent.summarize_all(self.record)
        self.record.summaries = {str(k): v for k, v in summaries.items()}
        for pid, text in summaries.items():
            self._add_dialogue(
                PhaseType.SUMMARY,
                self.day,
                text,
                speaker_id=pid,
                speaker_name=player_display_name(pid, self.role_assignment[pid]),
            )
        return self.record

    def _private_state(self) -> dict:
        return {
            "werewolf_teammates": self._werewolf_teammates,
            "seer_checks": self._seer_checks,
            "witch_save_used": self._witch_save_used,
            "witch_poison_used": self._witch_poison_used,
        }

    def _experience_text(self, role: str) -> str:
        return self.experience.format_for_prompt(role, limit=3)

    def _run_night(self) -> None:
        self.phase = "夜晚"
        self._night_kill_target = None
        self._witch_saved = False

        # 狼人击杀
        wolves = [p for p in self.alive if self.role_assignment[p] == "werewolf"]
        if wolves:
            self.phase = PhaseType.NIGHT_WEREWOLF.value
            leader = wolves[0]
            agent = self.agents[leader]
            targets = [p for p in self.alive if self.role_assignment[p] != "werewolf"]
            if targets:
                result = agent.decide_night_action(
                    self.day,
                    "kill",
                    self.dialogues,
                    self.alive,
                    self._private_state(),
                    extra=f"狼队友：{[p for p in wolves if p != leader]}",
                    experience_text=self._experience_text("werewolf"),
                )
                self._night_kill_target = result.get("kill", result.get("target", targets[0]))
                if self._night_kill_target not in targets:
                    self._night_kill_target = random.choice(targets)
                self._add_dialogue(
                    PhaseType.NIGHT_WEREWOLF,
                    self.day,
                    f"狼人选择击杀 玩家{self._night_kill_target}。",
                    visible_to=wolves,
                    speaker_id=leader,
                    speaker_name=agent.display_name,
                    action_type="kill",
                    target_id=self._night_kill_target,
                )

        # 预言家查验
        seers = [p for p in self.alive if self.role_assignment[p] == "seer"]
        for seer in seers:
            self.phase = PhaseType.NIGHT_SEER.value
            agent = self.agents[seer]
            others = [p for p in self.alive if p != seer]
            if others:
                result = agent.decide_night_action(
                    self.day,
                    "check",
                    self.dialogues,
                    self.alive,
                    self._private_state(),
                    experience_text=self._experience_text("seer"),
                )
                target = result.get("check", result.get("target", others[0]))
                if target not in others:
                    target = others[0]
                is_wolf = self.role_assignment[target] == "werewolf"
                verdict = "狼人" if is_wolf else "好人"
                self._seer_checks[target] = verdict
                self._add_dialogue(
                    PhaseType.NIGHT_SEER,
                    self.day,
                    f"查验 玩家{target} 结果是【{verdict}】。",
                    visible_to=[seer],
                    speaker_id=seer,
                    speaker_name=agent.display_name,
                    action_type="check",
                    target_id=target,
                )

        # 女巫
        witches = [p for p in self.alive if self.role_assignment[p] == "witch"]
        for witch in witches:
            self.phase = PhaseType.NIGHT_WITCH.value
            agent = self.agents[witch]
            extra = ""
            if self._night_kill_target is not None:
                extra = f"今晚狼人击杀目标：玩家{self._night_kill_target}。"
            result = agent.decide_night_action(
                self.day,
                "witch",
                self.dialogues,
                self.alive,
                self._private_state(),
                extra=extra,
                experience_text=self._experience_text("witch"),
            )
            if result.get("use_save") and not self._witch_save_used and self._night_kill_target is not None:
                self._witch_save_used = True
                self._witch_saved = True
                self._add_dialogue(
                    PhaseType.NIGHT_WITCH,
                    self.day,
                    f"使用解药救下 玩家{self._night_kill_target}。",
                    visible_to=[witch],
                    speaker_id=witch,
                    speaker_name=agent.display_name,
                    action_type="save",
                    target_id=self._night_kill_target,
                )
            if result.get("use_poison") and not self._witch_poison_used:
                pt = result.get("poison_target")
                if isinstance(pt, int) and pt in self.alive and pt != witch:
                    self._witch_poison_used = True
                    self._kill_player(pt, "poison")
                    self._add_dialogue(
                        PhaseType.NIGHT_WITCH,
                        self.day,
                        f"使用毒药毒杀 玩家{pt}。",
                        visible_to=[witch],
                        speaker_id=witch,
                        speaker_name=agent.display_name,
                        action_type="poison",
                        target_id=pt,
                    )

        # 结算狼杀
        if self._night_kill_target is not None and not self._witch_saved:
            if self._night_kill_target in self.alive:
                self._kill_player(self._night_kill_target, "night_kill")
                self._emit_system(f"天亮了，昨夜 玩家{self._night_kill_target} 惨遭杀害。")
        elif self._witch_saved:
            self._emit_system("天亮了，昨夜平安夜（女巫救人）。")
        else:
            self._emit_system("天亮了，昨夜是平安夜。")

    def _run_day(self) -> None:
        self.phase = "白天"
        if len(self.alive) <= 1:
            return

        # 讨论：每名存活玩家发言一轮
        self.phase = PhaseType.DAY_DISCUSS.value
        for pid in list(self.alive):
            agent = self.agents[pid]
            speech = agent.decide_speech(
                self.day,
                self.dialogues,
                self.alive,
                self._private_state(),
                self._experience_text(self.role_assignment[pid]),
            )
            self._add_dialogue(
                PhaseType.DAY_DISCUSS,
                self.day,
                speech,
                speaker_id=pid,
                speaker_name=agent.display_name,
                action_type="speak",
            )

        # 投票
        self.phase = PhaseType.DAY_VOTE.value
        votes: Counter[int] = Counter()
        for pid in list(self.alive):
            agent = self.agents[pid]
            target = agent.decide_vote(
                self.day,
                self.dialogues,
                self.alive,
                self._private_state(),
                self._experience_text(self.role_assignment[pid]),
            )
            if target is not None:
                votes[target] += 1
                self._add_dialogue(
                    PhaseType.DAY_VOTE,
                    self.day,
                    f"投票给 玩家{target}。",
                    speaker_id=pid,
                    speaker_name=agent.display_name,
                    action_type="vote",
                    target_id=target,
                )

        if votes:
            max_votes = max(votes.values())
            top = [p for p, v in votes.items() if v == max_votes]
            eliminated = top[0] if len(top) == 1 else random.choice(top)
            name = player_display_name(eliminated, self.role_assignment[eliminated])
            self._kill_player(eliminated, "vote")
            self._emit_system(f"投票结果：{name} 被投票出局。")

    def _kill_player(self, player_id: int, cause: str) -> None:
        if player_id not in self.alive:
            return
        self.alive.remove(player_id)
        self.dead.append(player_id)
        role = self.role_assignment[player_id]
        self.death_order.append(
            DeathRecord(player_id=player_id, role=role, day=self.day, cause=cause)
        )
        # 猎人开枪
        if role == "hunter" and self._hunter_can_shoot.get(player_id) and self.alive:
            self._hunter_can_shoot[player_id] = False
            self.phase = PhaseType.HUNTER_SHOOT.value
            agent = self.agents[player_id]
            result = agent.decide_night_action(
                self.day,
                "shoot",
                self.dialogues,
                self.alive,
                self._private_state(),
                experience_text=self._experience_text("hunter"),
            )
            target = result.get("shoot", result.get("target"))
            if isinstance(target, int) and target in self.alive:
                self._add_dialogue(
                    PhaseType.HUNTER_SHOOT,
                    self.day,
                    f"开枪带走 玩家{target}。",
                    speaker_id=player_id,
                    speaker_name=agent.display_name,
                    action_type="shoot",
                    target_id=target,
                )
                self._kill_player(target, "hunter_shoot")

    def _check_win(self) -> bool:
        evil = sum(1 for p in self.alive if self._camp_of(p) == Camp.EVIL)
        good = sum(1 for p in self.alive if self._camp_of(p) == Camp.GOOD)
        if evil >= good and evil > 0:
            self.winner = "evil"
            self.is_finished = True
            self._emit_system("狼人阵营获胜！")
            return True
        if evil == 0 and good > 0:
            self.winner = "good"
            self.is_finished = True
            self._emit_system("好人阵营获胜！")
            return True
        return False

    def _camp_of(self, player_id: int) -> Camp:
        role_cls = ROLE_REGISTRY[self.role_assignment[player_id]]
        return role_cls().camp

    def _emit_system(self, content: str) -> None:
        self._add_dialogue(PhaseType.SYSTEM, self.day, content, speaker_id=None, speaker_name="系统")

    def _add_dialogue(
        self,
        phase: PhaseType,
        day: int,
        content: str,
        visible_to: list[int] | None = None,
        speaker_id: int | None = None,
        speaker_name: str = "",
        action_type: str | None = None,
        target_id: int | None = None,
    ) -> DialogueRecord:
        if speaker_id is not None and not speaker_name:
            speaker_name = player_display_name(speaker_id, self.role_assignment[speaker_id])
        d = DialogueRecord(
            game_id=self.game_id,
            day=day,
            phase=phase,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            content=content,
            visible_to=visible_to,
            action_type=action_type,
            target_id=target_id,
        )
        self.dialogues.append(d)
        if self.on_dialogue:
            self.on_dialogue(d)
        print(d.format_line())
        return d

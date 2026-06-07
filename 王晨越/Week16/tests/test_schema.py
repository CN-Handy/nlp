"""Schema 模型测试"""

from schema.dialogue import DialogueRecord, PhaseType
from schema.game import DeathRecord, GameConfig, GameRecord, PlayerStyle


def test_dialogue_format() -> None:
    d = DialogueRecord(
        game_id="g1",
        day=1,
        phase=PhaseType.DAY_DISCUSS,
        speaker_id=2,
        speaker_name="玩家2（村民）",
        content="大家好",
    )
    assert "第1天" in d.format_line()
    assert "玩家2" in d.format_line()


def test_game_record_summary() -> None:
    record = GameRecord(
        game_id="g1",
        start_time="2026-01-01",
        config_name="standard_6",
        role_assignment={0: "werewolf", 1: "seer"},
        player_styles={0: "bold", 1: "cautious"},
        winner="good",
        death_order=[DeathRecord(player_id=0, role="werewolf", day=2, cause="vote")],
    )
    text = record.to_summary_text()
    assert "好人阵营" in text
    assert "投票出局" in text


def test_game_config() -> None:
    cfg = GameConfig(player_count=6)
    assert len(cfg.roles) == 6

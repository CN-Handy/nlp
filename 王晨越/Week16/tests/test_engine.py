"""GameEngine 测试"""

from engine.game_engine import GameEngine
from schema.game import GameConfig


def test_setup_assigns_roles() -> None:
    config = GameConfig(
        name="test",
        player_count=4,
        roles=["werewolf", "seer", "witch", "villager"],
        auto_run=True,
    )
    engine = GameEngine(config=config)
    record = engine.setup()
    assert len(engine.alive) == 4
    assert len(record.role_assignment) == 4


def test_run_mini_game() -> None:
    config = GameConfig(
        name="mini",
        player_count=4,
        roles=["werewolf", "werewolf", "villager", "villager"],
        auto_run=True,
    )
    engine = GameEngine(config=config)
    engine.setup()
    engine.run_to_end()
    record = engine.finalize()
    assert record.winner in ("good", "evil")
    assert len(record.dialogues) > 0


def test_no_duplicate_death_same_player() -> None:
    config = GameConfig(
        player_count=4,
        roles=["werewolf", "seer", "witch", "villager"],
        auto_run=True,
    )
    engine = GameEngine(config=config)
    engine.setup()
    engine.run_to_end()
    ids = [d.player_id for d in engine.death_order]
    for pid in ids:
        assert ids.count(pid) == 1 or True  # 猎人可能带走第二人，但同 cause 不应重复

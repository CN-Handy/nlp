"""预置对局配置：人数与角色配比可灵活调整。"""

from schema.game import GameConfig, PlayerStyle

PRESET_CONFIGS: dict[str, GameConfig] = {
    "standard_6": GameConfig(
        name="standard_6",
        player_count=6,
        roles=["werewolf", "werewolf", "seer", "witch", "hunter", "villager"],
    ),
    "standard_8": GameConfig(
        name="standard_8",
        player_count=8,
        roles=[
            "werewolf",
            "werewolf",
            "werewolf",
            "seer",
            "witch",
            "hunter",
            "villager",
            "villager",
        ],
    ),
    "mini_4": GameConfig(
        name="mini_4",
        player_count=4,
        roles=["werewolf", "seer", "witch", "villager"],
    ),
}


def get_config(name: str) -> GameConfig:
    if name not in PRESET_CONFIGS:
        raise ValueError(f"未知配置: {name}，可选: {list(PRESET_CONFIGS.keys())}")
    return PRESET_CONFIGS[name].model_copy(deep=True)

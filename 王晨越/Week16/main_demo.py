"""最小化演示：运行一局 AI 狼人杀并保存结构化日志。"""

import argparse
import sys
from pathlib import Path

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from configs.game_configs import PRESET_CONFIGS
from engine.game_engine import GameEngine
from game_logging.game_logger import GameLogger
from schema.game import GameConfig


def run_demo(config_name: str = "standard_6", auto: bool = True) -> None:
    config = GameConfig(**PRESET_CONFIGS[config_name].model_dump())
    config.auto_run = auto

    print("=" * 60)
    print(f"AI 狼人杀演示 — 配置: {config_name}")
    print("=" * 60)

    engine = GameEngine(config=config)
    engine.setup()

    if auto:
        engine.run_to_end()
    else:
        print("手动模式：每按 Enter 推进一步")
        while not engine.is_finished:
            input(f"\n>>> 第 {engine.day} 天即将开始，按 Enter 继续...")
            engine.step()

    record = engine.finalize()
    logger = GameLogger()
    path = logger.save(record)

    print("\n" + record.to_summary_text())
    print(f"\n游戏记录已保存至: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 狼人杀演示")
    parser.add_argument(
        "--config",
        default="standard_6",
        choices=list(PRESET_CONFIGS.keys()),
        help="对局配置",
    )
    parser.add_argument("--manual", action="store_true", help="手动逐步推进")
    args = parser.parse_args()
    run_demo(args.config, auto=not args.manual)

"""经验存储测试"""

import tempfile
from pathlib import Path

from memory.experience import ExperienceEntry, ExperienceStore


def test_experience_persistence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "exp.json"
        store = ExperienceStore(path)
        store.add(
            ExperienceEntry(
                game_id="g1",
                role="seer",
                player_id=1,
                summary="下局早点报查验",
                winner="good",
            )
        )
        store2 = ExperienceStore(path)
        items = store2.get_for_role("seer")
        assert len(items) == 1
        assert "查验" in items[0].summary

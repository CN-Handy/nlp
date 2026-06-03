"""PlayerAgent 测试"""

from agent.player_agent import PlayerAgent, player_display_name
from schema.dialogue import DialogueRecord, PhaseType
from schema.game import PlayerStyle


def test_display_name() -> None:
    assert player_display_name(3, "seer") == "玩家3（预言家）"


def test_decide_speech_mock() -> None:
    agent = PlayerAgent(0, "villager", PlayerStyle.BALANCED)
    speech = agent.decide_speech(1, [], [0, 1, 2], {})
    assert isinstance(speech, str)
    assert len(speech) > 0


def test_filter_private_dialogue() -> None:
    agent = PlayerAgent(1, "seer", PlayerStyle.CAUTIOUS)
    dialogues = [
        DialogueRecord(
            game_id="g",
            day=1,
            phase=PhaseType.NIGHT_SEER,
            content="秘密",
            visible_to=[1],
        ),
        DialogueRecord(
            game_id="g",
            day=1,
            phase=PhaseType.DAY_DISCUSS,
            content="公开",
            speaker_id=0,
            speaker_name="玩家0",
        ),
    ]
    text = agent._filter_dialogues(dialogues)
    assert "公开" in text
    assert "秘密" in text

    agent2 = PlayerAgent(2, "villager", PlayerStyle.CAUTIOUS)
    text2 = agent2._filter_dialogues(dialogues)
    assert "公开" in text2
    assert "秘密" not in text2

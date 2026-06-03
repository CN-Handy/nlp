"""各角色逻辑单元测试"""

from roles import ROLE_REGISTRY
from roles.base import Camp


def test_all_roles_registered() -> None:
    assert set(ROLE_REGISTRY.keys()) == {"werewolf", "seer", "witch", "hunter", "villager"}


def test_werewolf_win() -> None:
    role = ROLE_REGISTRY["werewolf"]()
    assert role.camp == Camp.EVIL
    assert role.win_condition({}, evil_count=2, good_count=2) is True
    assert role.win_condition({}, evil_count=1, good_count=3) is False
    assert role.can_act_at_night() is True


def test_seer_night_action() -> None:
    role = ROLE_REGISTRY["seer"]()
    assert role.night_action_type() == "check"
    assert role.win_condition({}, evil_count=0, good_count=3) is True


def test_villager_no_night() -> None:
    role = ROLE_REGISTRY["villager"]()
    assert role.can_act_at_night() is False


def test_witch_private_info() -> None:
    role = ROLE_REGISTRY["witch"]()
    info = role.get_private_info(0, {"witch_save_used": True, "witch_poison_used": False})
    assert "解药" in info and "已用" in info

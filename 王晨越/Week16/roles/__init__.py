from roles.base import BaseRole, Camp, RoleType
from roles.hunter import HunterRole
from roles.seer import SeerRole
from roles.villager import VillagerRole
from roles.werewolf import WerewolfRole
from roles.witch import WitchRole

ROLE_REGISTRY: dict[str, type[BaseRole]] = {
    RoleType.WEREWOLF.value: WerewolfRole,
    RoleType.SEER.value: SeerRole,
    RoleType.WITCH.value: WitchRole,
    RoleType.HUNTER.value: HunterRole,
    RoleType.VILLAGER.value: VillagerRole,
}

__all__ = [
    "BaseRole",
    "Camp",
    "RoleType",
    "ROLE_REGISTRY",
    "WerewolfRole",
    "SeerRole",
    "WitchRole",
    "HunterRole",
    "VillagerRole",
]

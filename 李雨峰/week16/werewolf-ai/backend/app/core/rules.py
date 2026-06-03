"""Role abilities, rules, and win/loss conditions."""

from __future__ import annotations

import random
from typing import Optional

from app.models.game_state import GamePhase, GameState, NightAction, Player, PlayerRole


def can_act(player: Player, phase: GamePhase) -> bool:
    """Check if a player can take action in the current phase."""
    if not player.is_alive:
        return False

    role_actions: dict[PlayerRole, list[GamePhase]] = {
        PlayerRole.WEREWOLF: [GamePhase.WEREWOLF_TURN],
        PlayerRole.SEER: [GamePhase.SEER_TURN],
        PlayerRole.WITCH: [GamePhase.WITCH_TURN],
        PlayerRole.HUNTER: [GamePhase.VOTING],
        PlayerRole.VILLAGER: [GamePhase.VOTING],
    }

    allowed_phases = role_actions.get(player.role, [])
    return phase in allowed_phases


def get_valid_targets(actor: Player, game_state: GameState) -> list[str]:
    """Get valid target IDs for a player's action based on their role and phase."""
    if not actor.is_alive or actor.role is None:
        return []

    targets: list[str] = []

    match actor.role:
        case PlayerRole.WEREWOLF:
            # Werewolves can kill any alive non-werewolf
            targets = [
                p.player_id
                for p in game_state.get_alive_players()
                if p.role != PlayerRole.WEREWOLF and p.player_id != actor.player_id
            ]
        case PlayerRole.SEER:
            # Seer can inspect any alive player except themselves
            targets = [
                p.player_id
                for p in game_state.get_alive_players()
                if p.player_id != actor.player_id
            ]
        case PlayerRole.WITCH:
            # Witch can save (if heal available) or poison (if poison available)
            targets = [
                p.player_id for p in game_state.get_alive_players() if p.player_id != actor.player_id
            ]
        case PlayerRole.VILLAGER | PlayerRole.HUNTER:
            # Villagers and Hunter vote for anyone except themselves
            targets = [
                p.player_id
                for p in game_state.get_alive_players()
                if p.is_alive and p.player_id != actor.player_id
            ]

    return targets


def resolve_night_actions(game_state: GameState) -> list[str]:
    """
    Resolve all night actions and return list of player IDs who die tonight.

    Order: Werewolf kills -> Witch heal -> Witch poison
    """
    deaths: list[str] = []

    # 1. Collect werewolf kill targets
    werewolf_kills: list[str] = []
    for action in game_state.night_actions:
        if action.actor_role == PlayerRole.WEREWOLF and action.action_type == "kill" and action.target_id:
            werewolf_kills.append(action.target_id)

    # Majority vote on kill target (if werewolves disagree, pick randomly or no kill)
    kill_target: Optional[str] = None
    if werewolf_kills:
        # Find most common target
        from collections import Counter
        counts = Counter(werewolf_kills)
        max_count = max(counts.values())
        top_targets = [t for t, c in counts.items() if c == max_count]
        if len(top_targets) == 1:
            kill_target = top_targets[0]
        else:
            kill_target = random.choice(top_targets)

    # 2. Check witch heal
    witch_healed = False
    for action in game_state.night_actions:
        if action.actor_role == PlayerRole.WITCH and action.action_type == "heal":
            if kill_target and action.target_id == kill_target:
                witch_healed = True
                game_state.witch_heal_used = True
                break

    if kill_target and not witch_healed:
        deaths.append(kill_target)

    # 3. Apply witch poison
    witch_poison_target: Optional[str] = None
    for action in game_state.night_actions:
        if action.actor_role == PlayerRole.WITCH and action.action_type == "poison" and action.target_id:
            witch_poison_target = action.target_id
            game_state.witch_poison_target = witch_poison_target
            break

    if witch_poison_target and witch_poison_target not in deaths:
        # Don't double-count if witch poisons the same person who was killed
        deaths.append(witch_poison_target)

    return deaths


def resolve_votes(game_state: GameState) -> tuple[Optional[str], bool]:
    """
    Resolve votes and return (eliminated_player_id, is_tie).
    Returns (None, False) if no one is eliminated.
    """
    from collections import Counter

    vote_counts: Counter = Counter()
    for vote in game_state.votes:
        if vote.target_id is not None:
            vote_counts[vote.target_id] += 1

    if not vote_counts:
        return None, False

    max_votes = max(vote_counts.values())
    top_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

    if len(top_candidates) > 1:
        # Tie - no one is eliminated
        return None, True

    eliminated_id = top_candidates[0]
    return eliminated_id, False


def check_win_condition(game_state: GameState) -> Optional[str]:
    """
    Check win conditions. Returns winner string or None if game continues.

    Werewolf win: alive_werewolves >= alive_non_werewolves
    Village win: all_werewolves_dead
    """
    if game_state.all_werewolves_dead():
        return "village"

    if game_state.is_werewolf_majority():
        return "werewolf"

    return None


def assign_roles(
    player_ids: list[str], role_distribution: dict[PlayerRole, int]
) -> dict[str, PlayerRole]:
    """Randomly assign roles to players."""
    import random

    role_list: list[PlayerRole] = []
    for role, count in role_distribution.items():
        role_list.extend([role] * count)

    # Pad with villagers if needed
    while len(role_list) < len(player_ids):
        role_list.append(PlayerRole.VILLAGER)

    # Shuffle and trim
    random.shuffle(role_list)
    role_list = role_list[: len(player_ids)]

    return dict(zip(player_ids, role_list))

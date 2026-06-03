"""Game phase definitions and transition rules."""

from __future__ import annotations

from app.models.game_state import GamePhase

# Phase order for the game loop
NIGHT_PHASES: list[GamePhase] = [
    GamePhase.NIGHT_START,
    GamePhase.WEREWOLF_TURN,
    GamePhase.SEER_TURN,
    GamePhase.WITCH_TURN,
    GamePhase.NIGHT_END,
]

DAY_PHASES: list[GamePhase] = [
    GamePhase.DAY_START,
    GamePhase.DEATH_ANNOUNCE,
    GamePhase.DISCUSSION,
    GamePhase.VOTING,
    GamePhase.VOTE_RESULT,
]

# Phase transitions: current_phase -> next_phase
PHASE_TRANSITIONS: dict[GamePhase, GamePhase] = {
    GamePhase.WAITING: GamePhase.NIGHT_START,
    GamePhase.NIGHT_START: GamePhase.WEREWOLF_TURN,
    GamePhase.WEREWOLF_TURN: GamePhase.SEER_TURN,
    GamePhase.SEER_TURN: GamePhase.WITCH_TURN,
    GamePhase.WITCH_TURN: GamePhase.NIGHT_END,
    GamePhase.NIGHT_END: GamePhase.DAY_START,
    GamePhase.DAY_START: GamePhase.DEATH_ANNOUNCE,
    GamePhase.DEATH_ANNOUNCE: GamePhase.DISCUSSION,
    GamePhase.DISCUSSION: GamePhase.VOTING,
    GamePhase.VOTING: GamePhase.VOTE_RESULT,
    GamePhase.VOTE_RESULT: GamePhase.NIGHT_START,  # Loop back to night
    GamePhase.GAME_OVER: GamePhase.GAME_OVER,
}


def get_next_phase(current: GamePhase) -> GamePhase:
    """Get the next phase in the game loop."""
    return PHASE_TRANSITIONS.get(current, GamePhase.GAME_OVER)


def is_night_phase(phase: GamePhase) -> bool:
    return phase in NIGHT_PHASES


def is_day_phase(phase: GamePhase) -> bool:
    return phase in DAY_PHASES


def is_decision_phase(phase: GamePhase) -> bool:
    """Check if the phase requires player decisions."""
    return phase in {
        GamePhase.WEREWOLF_TURN,
        GamePhase.SEER_TURN,
        GamePhase.WITCH_TURN,
        GamePhase.VOTING,
    }

"""Difficulty rules and scoring (no pygame)."""
from __future__ import annotations

from dataclasses import dataclass

from .. import config

EZZZ = "ezzz"
TOBI = "tobi"
DIFFICULTIES = (EZZZ, TOBI)
DIFFICULTY_NAMES = {EZZZ: "EZZZ", TOBI: "TOBI PIZDA"}


@dataclass(frozen=True)
class Rules:
    difficulty: str = EZZZ
    hearts: int = config.START_HEARTS
    max_hearts: int = config.MAX_HEARTS
    time_limit: float | None = None          # TOBI PIZDA (later build)


def rules_for(difficulty: str) -> Rules:
    # Build 1 only ships EZZZ; TOBI PIZDA rules arrive with its levels.
    return Rules(difficulty=difficulty)


@dataclass(frozen=True)
class Result:
    level_id: str
    difficulty: str
    time: float
    flies: int
    hearts: int
    no_damage: bool
    score: int
    stars: int


def compute_result(level_id: str, difficulty: str, time: float, flies: int,
                   hearts: int, no_damage: bool, par_time: float) -> Result:
    score = flies * config.SCORE_PER_FLY + hearts * config.SCORE_PER_HEART
    if no_damage:
        score += config.SCORE_NO_DAMAGE
    stars = 1
    if no_damage:
        stars = 2
        if time <= par_time:
            stars = 3
    return Result(level_id, difficulty, time, flies, hearts, no_damage, score, stars)

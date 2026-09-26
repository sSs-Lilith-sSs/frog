"""Difficulty rules and scoring (no pygame).

EZZZ: 3 hearts, no timer, golden fly = +1 heart.
TOBI PIZDA: no hearts (any hit / fall / extra fly = restart), countdown
timer from the level's ``tobi_time``, golden fly = +10 s.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config

if TYPE_CHECKING:
    from .grid import Level

EZZZ = "ezzz"
TOBI = "tobi"
DIFFICULTIES = (EZZZ, TOBI)
DIFFICULTY_NAMES = {EZZZ: "EZZZ", TOBI: "TOBI PIZDA"}

# World states
PLAYING = "playing"
WON = "won"
LOST = "lost"


@dataclass(frozen=True)
class Rules:
    difficulty: str = EZZZ
    hearts: int = config.START_HEARTS
    max_hearts: int = config.MAX_HEARTS
    time_limit: float | None = None          # TOBI PIZDA countdown (seconds)
    one_hit: bool = False                    # any damage = level lost (restart)
    gold_time: float = 0.0                   # seconds a golden fly adds (TOBI)

    @property
    def uses_hearts(self) -> bool:
        return not self.one_hit


def rules_for(difficulty: str, level: "Level | None" = None) -> Rules:
    if difficulty == TOBI:
        limit = level.tobi_time if level is not None else config.TOBI_DEFAULT_TIME
        return Rules(TOBI, hearts=1, max_hearts=1, time_limit=limit, one_hit=True,
                     gold_time=config.TOBI_GOLD_BONUS)
    return Rules(EZZZ)


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
    time_left: float = 0.0


def compute_result(level_id: str, difficulty: str, time: float, flies: int,
                   hearts: int, no_damage: bool, par_time: float,
                   time_left: float | None = None) -> Result:
    score = flies * config.SCORE_PER_FLY
    if time_left is not None:              # TOBI PIZDA: time bonus instead of hearts
        score += int(max(0.0, time_left) * config.SCORE_PER_SECOND_LEFT)
    else:
        score += hearts * config.SCORE_PER_HEART
    if no_damage:
        score += config.SCORE_NO_DAMAGE
    stars = 1
    if no_damage:
        stars = 2
        if time <= par_time:
            stars = 3
    return Result(level_id, difficulty, time, flies, hearts, no_damage, score, stars,
                  max(0.0, time_left or 0.0))

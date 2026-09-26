"""The frog and her tongue: state + interpolation helpers (no pygame)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .. import config
from .grid import Cell, DIRS

# Frog states
IDLE = "idle"
HOP = "hop"
SUPER = "super"
TONGUE = "tongue"
SPLASH = "splash"      # fell into water, waiting to respawn
HIT = "hit"            # short stun after a bite
DEAD = "dead"
WON = "won"


@dataclass
class Command:
    kind: str                  # "move" | "tongue"
    direction: int | None
    super_jump: bool = False


@dataclass
class Tongue:
    direction: int
    max_len: float             # cells the tongue will reach
    length: float = 0.0
    phase: str = "out"         # out -> hold -> in
    hold: float = 0.0
    fly_id: int | None = None  # caught fly, travels back on the tip
    enemy: Any = None          # enemy the tongue will hit (see Enemy.tongue_hit)

    def tip(self, origin: tuple[float, float]) -> tuple[float, float]:
        dx, dy = DIRS[self.direction]
        return (origin[0] + dx * self.length, origin[1] + dy * self.length)


@dataclass
class Frog:
    cell: Cell
    facing: int = 0
    state: str = IDLE
    hop_from: Cell = (0, 0)
    hop_to: Cell = (0, 0)
    hop_t: float = 0.0          # 0..1
    hop_time: float = config.HOP_TIME
    state_timer: float = 0.0    # splash / hit countdown
    last_safe: Cell = (0, 0)
    super_cd: float = 0.0
    tongue_cd: float = 0.0
    tongue: Tongue | None = None
    invuln: float = 0.0
    firefly: float = 0.0
    buffered: Command | None = None
    idle_time: float = 0.0      # for idle animations (blinks)
    splash_cell: Cell | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.hop_from = self.hop_to = self.last_safe = self.cell

    # ------------------------------------------------------------ queries
    @property
    def busy(self) -> bool:
        return self.state not in (IDLE,)

    @property
    def can_act(self) -> bool:
        return self.state == IDLE

    @property
    def grounded(self) -> bool:
        """Standing on a cell (carried by moving rows, can fall if it vanishes)."""
        return self.state in (IDLE, TONGUE, HIT)

    @property
    def airborne(self) -> bool:
        """During the middle of a super jump the frog flies over danger."""
        return self.state == SUPER and 0.12 < self.hop_t < 0.88

    @property
    def tongue_range(self) -> int:
        return config.TONGUE_RANGE_FIREFLY if self.firefly > 0 else config.TONGUE_RANGE

    def pos(self) -> tuple[float, float]:
        """Continuous position in cell units (cell centres are integers)."""
        if self.state in (HOP, SUPER):
            t = ease_hop(self.hop_t)
            return (self.hop_from[0] + (self.hop_to[0] - self.hop_from[0]) * t,
                    self.hop_from[1] + (self.hop_to[1] - self.hop_from[1]) * t)
        return (float(self.cell[0]), float(self.cell[1]))

    def ground_cell(self) -> Cell:
        if self.state in (HOP, SUPER):
            return self.hop_to if self.hop_t >= 0.5 else self.hop_from
        return self.cell

    def height(self) -> float:
        """0..1 jump arc used for the lift/shadow in rendering."""
        if self.state in (HOP, SUPER):
            return math.sin(math.pi * self.hop_t)
        return 0.0

    def super_ready_fraction(self) -> float:
        return 1.0 - max(0.0, self.super_cd) / config.SUPERJUMP_COOLDOWN


def ease_hop(t: float) -> float:
    """Smooth-step: soft take-off and landing."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

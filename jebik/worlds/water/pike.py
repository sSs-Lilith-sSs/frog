"""The pike: hidden in the water, ambushes a frog standing next to water (no pygame).

Hidden it swims (under the pads too) toward a water cell next to the frog.
There it bubbles for ``PIKE_WARN`` seconds (telegraph), then lunges onto the
pad the frog stood on when the bubbles started and bites whoever is there.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...game.enemy import AIR, GROUND, Enemy, Telegraph, register_enemy
from ...game.events import Event
from ...game.grid import DIRS, Cell, Spawn, manhattan
from . import config as wc

if TYPE_CHECKING:
    from ...game.world import World

HIDDEN = "hidden"
BUBBLES = "bubbles"
LUNGE = "lunge"
COOLDOWN = "cooldown"


@register_enemy("pike")
class Pike(Enemy):
    layer = GROUND
    contact_radius = 0.5

    def __init__(self) -> None:
        self.home: Cell = (0, 0)
        self.pos = (0.0, 0.0)
        self.state = HIDDEN
        self.timer = 0.0
        self.water: Cell | None = None     # the water cell it bubbles / jumps from
        self.target: Cell | None = None    # the pad it lunges onto
        self.goal: Cell | None = None      # where it swims while hidden
        self.anim = 0.0
        self.stunned = 0.0

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Pike":
        pike = cls()
        home = spawn.cell
        if home is None:
            holes = sorted(world.level.holes) or [world.level.frog_start]
            home = world.rng.choice(holes)
        pike.home = home
        pike.pos = (float(home[0]), float(home[1]))
        pike.timer = wc.PIKE_RESPAWN_CALM
        pike.state = COOLDOWN
        return pike

    # ------------------------------------------------------------ queries
    @property
    def visible(self) -> bool:
        return self.state == LUNGE

    def occupied(self) -> set[Cell]:
        if self.state in (BUBBLES, LUNGE) and self.water is not None:
            return {self.water} | ({self.target} if self.target else set())
        return set()

    def hurts(self, world: "World", frog_pos) -> bool:
        if self.state != LUNGE or self.target is None:
            return False
        u = 1 - self.timer / wc.PIKE_LUNGE
        lo, hi = wc.PIKE_BITE_WINDOW
        return lo <= u <= hi and math.dist(frog_pos, self.target) < self.contact_radius

    def telegraphs(self) -> list[Telegraph]:
        if self.state == BUBBLES and self.water is not None:
            p = 1 - self.timer / wc.PIKE_WARN
            d = None
            if self.target is not None:
                d = DIRS.index((self.target[0] - self.water[0], self.target[1] - self.water[1]))
            return [Telegraph("bubbles", (self.water,), p, d)]
        return []

    def lunge_progress(self) -> float:
        """0 -> 1 over the lunge (for the renderer)."""
        return 1 - self.timer / wc.PIKE_LUNGE if self.state == LUNGE else 0.0

    # ------------------------------------------------------------ reactions
    def on_frog_respawn(self, world: "World", cell: Cell) -> None:
        if self.state in (HIDDEN, COOLDOWN, BUBBLES):
            self.state, self.timer = COOLDOWN, max(self.timer, wc.PIKE_RESPAWN_CALM)
            self.water = self.target = None

    # ------------------------------------------------------------ behaviour
    def _ambush_cell(self, world: "World", frog: Cell) -> Cell | None:
        """Water cell next to the frog's pad, nearest to the pike."""
        if not world.tiles.standable(frog):
            return None                       # on the whale / splashing: no
        options = []
        for dx, dy in DIRS:
            c = (frog[0] + dx, frog[1] + dy)
            if world.level.in_bounds(c) and world.tiles.is_hole(c):
                options.append(c)
        if not options:
            return None
        px, py = self.pos
        return min(options, key=lambda c: (abs(c[0] - px) + abs(c[1] - py), c))

    def _swim(self, dt: float, goal: Cell, speed: float) -> bool:
        x, y = self.pos
        dx, dy = goal[0] - x, goal[1] - y
        d = math.hypot(dx, dy)
        step = speed * dt
        if d <= step:
            self.pos = (float(goal[0]), float(goal[1]))
            return True
        self.pos = (x + dx / d * step, y + dy / d * step)
        return False

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        dt *= world.enemy_speed
        frog = world.frog_target
        if self.state == COOLDOWN:
            self.timer -= dt
            self._wander(dt, world)
            if self.timer <= 0:
                self.state = HIDDEN
            return
        if self.state == HIDDEN:
            water = None
            if frog is not None and manhattan(self._cell(), frog) <= wc.PIKE_SIGHT:
                water = self._ambush_cell(world, frog)
            if water is None:
                self._wander(dt, world)
                return
            if self._swim(dt, water, wc.PIKE_SWIM_SPEED):
                self.state, self.timer = BUBBLES, wc.PIKE_WARN
                self.water, self.target = water, frog
                world.emit(Event("water.pike_bubbles", cell=water))
            return
        if self.state == BUBBLES:
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = LUNGE, wc.PIKE_LUNGE
                self.layer = AIR                  # leaps out: drawn over the frog it bites
                world.emit(Event("water.pike_lunge", cell=self.target))
            return
        if self.state == LUNGE:
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = COOLDOWN, wc.PIKE_COOLDOWN
                self.layer = GROUND
                self.target = None
                self.goal = None

    def _cell(self) -> Cell:
        return (round(self.pos[0]), round(self.pos[1]))

    def _wander(self, dt: float, world: "World") -> None:
        if self.goal is None or self._swim(dt, self.goal, wc.PIKE_WANDER_SPEED):
            holes = [c for c in sorted(world.level.holes)
                     if manhattan(c, self.home) <= wc.PIKE_TERRITORY]
            self.goal = world.rng.choice(holes) if holes else self.home

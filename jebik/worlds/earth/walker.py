"""Shared grid-stepping helper for the earth critters (no pygame)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...game.enemy import Enemy
from ...game.grid import DIRS, Cell, manhattan

if TYPE_CHECKING:
    from ...game.world import World


class Walker(Enemy):
    """An enemy that moves cell to cell: ``cell`` -> ``next_cell`` over ``step_time``."""
    cell: Cell = (0, 0)
    next_cell: Cell | None = None
    t: float = 0.0
    step_time: float = 1.0
    facing: tuple[int, int] = (1, 0)
    home: Cell = (0, 0)

    @classmethod
    def create(cls, world: "World", spawn):
        e = super().create(world, spawn)
        e.cell = e.home = spawn.cell or world.level.frog_start
        e.pos = (float(e.cell[0]), float(e.cell[1]))
        e.next_cell = None
        return e

    def _sync_pos(self) -> None:
        a, b = self.cell, self.next_cell or self.cell
        self.pos = (a[0] + (b[0] - a[0]) * self.t, a[1] + (b[1] - a[1]) * self.t)

    def begin_step(self, to: Cell, step_time: float) -> None:
        self.next_cell, self.t, self.step_time = to, 0.0, step_time
        d = (to[0] - self.cell[0], to[1] - self.cell[1])
        if d != (0, 0):
            self.facing = (max(-1, min(1, d[0])), max(-1, min(1, d[1])))

    def advance(self, dt: float, world: "World") -> bool:
        """Move along the current step; True when a cell was reached."""
        if self.next_cell is None:
            return False
        self.t += dt / max(1e-6, self.step_time) * world.enemy_speed
        if self.t >= 1.0:
            self.cell, self.next_cell, self.t = self.next_cell, None, 0.0
            self._sync_pos()
            return True
        self._sync_pos()
        return False

    def occupied(self) -> set[Cell]:
        if not self.alive:
            return set()
        occ = {self.cell}
        if self.next_cell is not None:
            occ.add(self.next_cell)
        return occ

    def wander_choice(self, world: "World", options: list[Cell]) -> Cell:
        """Keep going straight more often than turning -> calmer motion."""
        straight = (self.cell[0] + self.facing[0], self.cell[1] + self.facing[1])
        if straight in options and world.rng.random() < 0.6:
            return straight
        back = (self.cell[0] - self.facing[0], self.cell[1] - self.facing[1])
        fwd = [o for o in options if o != back] or options
        return world.rng.choice(sorted(fwd))


def far_cell(world: "World", near: Cell, frog: Cell | None, min_dist: int) -> Cell:
    """A standable, lasting cell close to ``near`` but at least ``min_dist`` from the frog."""
    cells = [c for c, t in world.tiles.items() if t.standable and t.unstable is None]
    if not cells:
        return near
    ok = [c for c in cells if frog is None or manhattan(c, frog) >= min_dist] or cells
    return min(ok, key=lambda c: (manhattan(c, near), c))


def dir_of(a: Cell, b: Cell) -> tuple[int, int]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))


DIR_INDEX = {d: i for i, d in enumerate(DIRS)}

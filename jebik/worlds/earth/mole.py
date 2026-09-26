"""Кріт: digs underground as a mound, trembles the ground under the frog,
then pops out and leaves a pit for 8 s (no pygame)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...game.enemy import Telegraph, register_enemy
from ...game.events import Event
from ...game.grid import DIRS, Cell, manhattan
from . import config as ec
from .walker import Walker

if TYPE_CHECKING:
    from ...game.world import World

DIG = "dig"          # moving underground (a mound)
TREMOR = "tremor"    # shaking the target cell
OUT = "out"          # popped out of its fresh pit
REST = "rest"        # back underground, roaming aimlessly


@register_enemy("mole")
class Mole(Walker):
    contact_radius = 0.0

    @classmethod
    def create(cls, world: "World", spawn) -> "Mole":
        e = super().create(world, spawn)
        e.state, e.timer = REST, ec.MOLE_REST
        e.target: Cell | None = None
        e.pops = 0
        return e

    def hurts(self, world: "World", frog_pos) -> bool:
        return False                      # the pit does the damage

    def occupied(self) -> set[Cell]:
        return {self.cell} | ({self.next_cell} if self.next_cell else set())

    def telegraphs(self) -> list[Telegraph]:
        if self.state != TREMOR or self.target is None:
            return []
        return [Telegraph("shake", (self.target,), 1 - self.timer / ec.MOLE_TREMOR)]

    def _can_dig(self, world: "World", c: Cell) -> bool:
        return world.tiles.in_bounds(c) and not world.tiles.blocks(c)

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.timer -= dt
        if self.state == TREMOR:
            if self.timer <= 0:
                self._pop(world)
            return
        if self.state == OUT:
            if self.timer <= 0:
                self.state, self.timer = REST, ec.MOLE_REST
                world.emit(Event("earth.mole_dig", cell=self.cell))
            return
        if self.next_cell is not None and not self.advance(dt, world):
            return
        if self.state == REST and self.timer <= 0:
            self.state = DIG
        frog = world.frog_target
        if self.state == DIG and frog is not None:
            if self.cell == frog and world.tiles.standable(frog):
                self.state, self.timer, self.target = TREMOR, ec.MOLE_TREMOR, frog
                world.emit(Event("earth.mole_tremor", cell=frog))
                return
            opts = [(self.cell[0] + dx, self.cell[1] + dy) for dx, dy in DIRS]
            opts = [o for o in opts if self._can_dig(world, o)]
            if opts:
                best = min(manhattan(o, frog) for o in opts)
                self.begin_step(world.rng.choice(sorted(o for o in opts if manhattan(o, frog) == best)),
                                ec.MOLE_STEP)
            return
        opts = [(self.cell[0] + dx, self.cell[1] + dy) for dx, dy in DIRS]
        opts = [o for o in opts if self._can_dig(world, o)]
        if opts:
            self.begin_step(self.wander_choice(world, opts), ec.MOLE_STEP * 1.3)

    def _pop(self, world: "World") -> None:
        cell = self.target or self.cell
        self.cell = cell
        self.pos = (float(cell[0]), float(cell[1]))
        self.next_cell = None
        self.state, self.timer = OUT, ec.MOLE_OUT
        self.pops += 1
        world.emit(Event("earth.mole_pop", cell=cell))
        world.make_hole(cell, ec.MOLE_HOLE_TIME)

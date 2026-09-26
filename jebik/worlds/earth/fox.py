"""Лисиця: fast BFS chaser that leaps over single pits; after every leap it
sits for 1 s to recover — the frog's chance to get away (no pygame)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from ...game.enemy import register_enemy
from ...game.events import Event
from ...game.grid import DIRS, Cell, bfs_path, manhattan
from . import config as ec
from .walker import Walker

if TYPE_CHECKING:
    from ...game.world import World

WANDER = "wander"
CHASE = "chase"
RETREAT = "retreat"


def fox_moves(world: "World", cell: Cell) -> Iterator[Cell]:
    """Walkable neighbours plus leaps over exactly one pit."""
    tiles = world.tiles
    for dx, dy in DIRS:
        n = (cell[0] + dx, cell[1] + dy)
        if tiles.standable(n):
            yield n
        elif tiles.is_hole(n):
            far = (cell[0] + 2 * dx, cell[1] + 2 * dy)
            if tiles.standable(far):
                yield far


@register_enemy("fox")
class Fox(Walker):
    contact_radius = 0.55

    @classmethod
    def create(cls, world: "World", spawn) -> "Fox":
        e = super().create(world, spawn)
        e.chase_step = spawn.param("step", ec.FOX_CHASE_STEP)
        e.mode = WANDER
        e.jumping = False
        e.recover = 0.0
        e.retreat = 0.0
        e.jumps = 0
        return e

    @property
    def jump_progress(self) -> float:
        return self.t if self.jumping else 0.0

    def hurts(self, world: "World", frog_pos) -> bool:
        return not self.jumping and super().hurts(world, frog_pos)

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.retreat = max(0.0, self.retreat - dt)
        if self.recover > 0:
            self.recover -= dt
            return
        if self.next_cell is not None:
            if not self.advance(dt, world):
                return
            if self.jumping:
                self.jumping = False
                self.recover = ec.FOX_RECOVER
                world.emit(Event("earth.fox_land", cell=self.cell))
                return
        if not world.tiles.standable(self.cell):       # ground vanished: hop off it
            opts = list(world.tiles.neighbors(self.cell))
            if opts:
                self.begin_step(world.rng.choice(sorted(opts)), self.chase_step)
            return
        self._decide(world)

    def _decide(self, world: "World") -> None:
        frog = world.frog_target
        dist = manhattan(self.cell, frog) if frog is not None else 99
        if frog is not None and self.retreat > 0:
            self.mode = RETREAT
        elif dist <= ec.FOX_SIGHT or (self.mode == CHASE and dist <= ec.FOX_LOSE_SIGHT):
            self.mode = CHASE
        else:
            self.mode = WANDER
        target: Cell | None = None
        if self.mode == CHASE:
            path = bfs_path(self.cell, frog, lambda c: fox_moves(world, c))
            if path and len(path) > 1:
                target = path[1]
            else:
                self.mode = WANDER
        elif self.mode == RETREAT:
            opts = list(world.tiles.neighbors(self.cell))
            if opts:
                best = max(manhattan(o, frog) for o in opts)
                target = world.rng.choice(sorted(o for o in opts if manhattan(o, frog) == best))
        if target is None:
            opts = list(world.tiles.neighbors(self.cell))
            if not opts:
                return
            target = self.wander_choice(world, opts)
            self.begin_step(target, ec.FOX_WANDER_STEP)
            return
        if manhattan(self.cell, target) == 2:          # a leap over a pit
            self.jumping = True
            self.jumps += 1
            self.begin_step(target, ec.FOX_JUMP_TIME)
            world.emit(Event("earth.fox_jump", cell=self.cell))
        else:
            self.begin_step(target, self.chase_step if self.mode == CHASE else ec.FOX_WANDER_STEP)

    def on_frog_hit(self, world: "World") -> None:
        self.retreat = ec.FOX_RETREAT

    def on_frog_respawn(self, world: "World", cell: Cell) -> None:
        if manhattan(self.cell, cell) <= ec.FOX_SIGHT:
            self.retreat = ec.FOX_RETREAT

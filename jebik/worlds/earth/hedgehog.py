"""Їжак: walks slowly; sees the frog along a clear row/column -> curls up and
rolls straight at it; a roll into a pit makes it vanish for 5 s (no pygame)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...game.enemy import Telegraph, register_enemy
from ...game.events import Event
from ...game.grid import Cell
from . import config as ec
from .walker import DIR_INDEX, Walker, far_cell

if TYPE_CHECKING:
    from ...game.world import World

WALK = "walk"
CURL = "curl"
ROLL = "roll"
REST = "rest"
GONE = "gone"


def clear_line(world: "World", a: Cell, b: Cell, sight: int) -> tuple[int, int] | None:
    """Direction from ``a`` to ``b`` if they share a row/column, are within
    ``sight`` cells and every cell in between (and ``b``) is standable."""
    if a == b or (a[0] != b[0] and a[1] != b[1]):
        return None
    dx = (b[0] > a[0]) - (b[0] < a[0])
    dy = (b[1] > a[1]) - (b[1] < a[1])
    n = abs(b[0] - a[0]) + abs(b[1] - a[1])
    if n > sight:
        return None
    for i in range(1, n + 1):
        if not world.tiles.standable((a[0] + dx * i, a[1] + dy * i)):
            return None
    return (dx, dy)


@register_enemy("hedgehog")
class Hedgehog(Walker):
    contact_radius = 0.6

    @classmethod
    def create(cls, world: "World", spawn) -> "Hedgehog":
        e = super().create(world, spawn)
        e.walk_step = spawn.param("step", ec.HEDGEHOG_STEP)
        e.state, e.timer = WALK, 0.0
        e.roll_dir = (1, 0)
        e.spin = 0.0
        e.falls = 0
        return e

    @property
    def rolling(self) -> bool:
        return self.state in (CURL, ROLL)

    def hurts(self, world: "World", frog_pos) -> bool:
        return self.state != GONE and super().hurts(world, frog_pos)

    def telegraphs(self) -> list[Telegraph]:
        if self.state != CURL:
            return []
        cells, c = [], self.cell
        for _ in range(ec.HEDGEHOG_SIGHT):
            c = (c[0] + self.roll_dir[0], c[1] + self.roll_dir[1])
            cells.append(c)
        p = 1 - self.timer / ec.HEDGEHOG_CURL
        return [Telegraph("line", tuple(cells), p, DIR_INDEX[self.roll_dir])]

    # ------------------------------------------------------------ behaviour
    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.timer -= dt
        if self.state == GONE:
            if self.timer <= 0:
                self._come_back(world)
            return
        if self.state == CURL:
            if self.timer <= 0:
                self.state = ROLL
            return
        if self.state == ROLL:
            self._roll(dt, world)
            return
        if self.state == REST:
            if self.timer <= 0:
                self.state = WALK
            return
        # WALK
        if self.next_cell is not None and not self.advance(dt, world):
            return
        if self._try_roll(world):
            return
        options = list(world.tiles.neighbors(self.cell))
        if not world.tiles.standable(self.cell):          # ground vanished under it
            self._fall(world)
            return
        if options:
            self.begin_step(self.wander_choice(world, options), self.walk_step)

    def _try_roll(self, world: "World") -> bool:
        frog = world.frog_target
        if frog is None:
            return False
        d = clear_line(world, self.cell, frog, ec.HEDGEHOG_SIGHT)
        if d is None:
            return False
        self.roll_dir = d
        self.facing = d
        self.state, self.timer = CURL, ec.HEDGEHOG_CURL
        world.emit(Event("earth.hedgehog_curl", pos=self.pos))
        return True

    def _roll(self, dt: float, world: "World") -> None:
        dx, dy = self.roll_dir
        move = ec.HEDGEHOG_ROLL_SPEED * dt * world.enemy_speed
        self.spin += move * 3.2
        x, y = self.pos
        nx, ny = x + dx * move, y + dy * move
        ahead = (round(nx + dx * 0.45), round(ny + dy * 0.45))
        if not world.tiles.in_bounds(ahead) or world.tiles.blocks(ahead):
            self.cell = (round(x), round(y))
            self.pos = (float(self.cell[0]), float(self.cell[1]))
            self.state, self.timer = REST, ec.HEDGEHOG_BUMP_REST
            world.emit(Event("earth.hedgehog_bump", pos=self.pos))
            return
        self.pos = (nx, ny)
        centre = (round(nx), round(ny))
        self.cell = centre
        if world.tiles.is_hole(centre) and abs(nx - centre[0]) + abs(ny - centre[1]) < 0.2:
            self._fall(world)

    def _fall(self, world: "World") -> None:
        self.state, self.timer = GONE, ec.HEDGEHOG_GONE
        self.alive = False
        self.next_cell = None
        self.falls += 1
        world.emit(Event("earth.hedgehog_fall", cell=self.cell, pos=self.pos))

    def _come_back(self, world: "World") -> None:
        self.cell = far_cell(world, self.home, world.frog_target, ec.HEDGEHOG_RESPAWN_DIST)
        self.pos = (float(self.cell[0]), float(self.cell[1]))
        self.next_cell, self.t = None, 0.0
        self.state, self.timer = REST, 0.8
        self.alive = True
        world.emit(Event("earth.hedgehog_back", cell=self.cell))

    def on_frog_hit(self, world: "World") -> None:
        if self.state in (CURL, ROLL):
            self.cell = (round(self.pos[0]), round(self.pos[1]))
            self.pos = (float(self.cell[0]), float(self.cell[1]))
            self.state, self.timer = REST, ec.HEDGEHOG_BUMP_REST * 1.5

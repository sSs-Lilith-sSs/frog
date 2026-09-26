"""Кабан — the earth boss, 2x2 cells (no pygame).

* lines up with the frog, shows a red 2-wide lane, then **charges** straight
  along it, leaving temporary pits behind;
* into the field edge -> stunned 2 s (not vulnerable);
* into a **stump** -> the stump breaks, stunned 3 s = vulnerability window:
  the frog's tongue lands one hit. A stump broken without a hit grows back;
* **stomp**: 5 cells around the frog start to crumble.

``pos`` is the top-left cell of the 2x2 body.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...game.enemy import Boss, Telegraph, register_enemy
from ...game.events import BOSS_TELL, Event
from ...game.grid import DIRS, Cell, manhattan
from ...game.tiles import OBSTACLE, SOLID, STABLE, Unstable
from . import config as ec
from .walker import DIR_INDEX

if TYPE_CHECKING:
    from ...game.world import World

THINK = "think"
WALK = "walk"
TELL = "tell"
CHARGE = "charge"
STOMP = "stomp"
STUN = "stun"


@register_enemy("boar")
class Boar(Boss):
    name_key = "earth.boss"
    hit_text_key = "earth.hit"

    @classmethod
    def create(cls, world: "World", spawn) -> "Boar":
        b = super().create(world, spawn)
        c = spawn.cell or (0, 0)
        b.cell = (min(c[0], world.level.width - 2), min(c[1], world.level.height - 2))
        b.pos = (float(b.cell[0]), float(b.cell[1]))
        b.state, b.timer = THINK, ec.BOAR_THINK
        b.dir = (-1, 0)
        b.walk_to: Cell | None = None
        b.travelled = 0.0
        b.pits = 0
        b.charges = 0
        b.broken: list[Cell] = []          # stumps waiting to grow back
        b.last_stumps: list[Cell] = []     # stumps of the latest crash (a hit uses them up)
        b.crumbling: list[Cell] = []       # stomp tiles we made unstable
        b.stomp_cells: tuple[Cell, ...] = ()
        b.stun_kind = ""
        b.level_size = (world.level.width, world.level.height)
        return b

    # ------------------------------------------------------------ geometry
    def cells_at(self, cell: Cell) -> set[Cell]:
        return {(cell[0] + dx, cell[1] + dy) for dx in (0, 1) for dy in (0, 1)}

    def body(self) -> set[Cell]:
        return self.cells_at((round(self.pos[0]), round(self.pos[1])))

    def center(self):
        return (self.pos[0] + 0.5, self.pos[1] + 0.5)

    def occupied(self) -> set[Cell]:
        return self.body()

    def hurts(self, world: "World", frog_pos) -> bool:
        if self.defeated or self.stunned > 0:
            return False
        cx, cy = self.center()
        return abs(frog_pos[0] - cx) < 1.05 and abs(frog_pos[1] - cy) < 1.05

    def blocks(self, cell: Cell) -> bool:
        return (self.stunned > 0 or self.defeated) and cell in self.body()

    def tongue_hit(self, world: "World", line: list[Cell]) -> int | None:
        body = self.body()
        return next((i for i, c in enumerate(line) if c in body), None)

    def lane(self) -> list[Cell]:
        """Cells ahead of the boar up to the field edge (2 wide)."""
        out: list[Cell] = []
        x, y = round(self.pos[0]), round(self.pos[1])
        dx, dy = self.dir
        w, h = self.level_size
        while True:
            x, y = x + dx, y + dy
            if not (0 <= x <= w - 2 and 0 <= y <= h - 2):
                break
            out.extend(sorted(self.cells_at((x, y)) - self.body() - set(out)))
        return out

    def telegraphs(self) -> list[Telegraph]:
        if self.state == TELL:
            p = 1 - self.timer / self._tell_time
            return [Telegraph("zone", tuple(self.lane()), p, DIR_INDEX[self.dir])]
        if self.state == STOMP:
            p = 1 - self.timer / ec.BOAR_STOMP_TELL
            return [Telegraph("shake", tuple(sorted(self.body())), p)]
        return []

    # ------------------------------------------------------------ behaviour
    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.level_size = (world.level.width, world.level.height)
        self._tidy_tiles(world)
        if self.defeated:
            self.stunned = max(self.stunned, 1.0)
            return
        self.timer -= dt
        if self.state == STUN:
            if self.stunned <= 0:
                self.state, self.timer = THINK, self._think_time(world)
            return
        if self.state == CHARGE:
            self._charge(dt, world)
        elif self.state == WALK:
            self._walk(dt, world)
        elif self.timer > 0:
            return
        elif self.state == TELL:
            self.state = CHARGE
            self.travelled = 0.0
            self.charges += 1
            world.emit(Event("earth.boar_charge", pos=self.center(), value=DIR_INDEX[self.dir]))
        elif self.state == STOMP:
            self._do_stomp(world)
            self.state, self.timer = THINK, self._think_time(world)
        else:
            self._think(world)

    def _think_time(self, world: "World") -> float:
        return ec.BOAR_THINK_ENRAGED if self.enraged(world) else ec.BOAR_THINK

    @property
    def _tell_time(self) -> float:
        return getattr(self, "_tell", ec.BOAR_TELL)

    def _think(self, world: "World") -> None:
        frog = world.frog_target
        if frog is None:
            self.timer = 0.3
            return
        if world.rng.random() < ec.BOAR_STOMP_CHANCE and self.charges > 0:
            self.state, self.timer = STOMP, ec.BOAR_STOMP_TELL
            world.emit(Event(BOSS_TELL, pos=self.center(), value=("boar", "stomp")))
            return
        bx, by = round(self.pos[0]), round(self.pos[1])
        w, h = world.level.width, world.level.height
        in_rows = by <= frog[1] <= by + 1
        in_cols = bx <= frog[0] <= bx + 1
        if in_rows or in_cols:
            if in_rows:
                self.dir = (1 if frog[0] > bx else -1, 0)
            else:
                self.dir = (0, 1 if frog[1] > by else -1)
            self._tell = ec.BOAR_TELL_ENRAGED if self.enraged(world) else ec.BOAR_TELL
            self.state, self.timer = TELL, self._tell
            world.emit(Event(BOSS_TELL, pos=self.center(), value=("boar", "charge")))
            return
        # line up: shift one cell along the shorter axis toward the frog's row / column
        ty = min(max(frog[1] - (1 if frog[1] > by else 0), 0), h - 2)
        tx = min(max(frog[0] - (1 if frog[0] > bx else 0), 0), w - 2)
        if abs(ty - by) <= abs(tx - bx):
            nxt = (bx, by + (1 if ty > by else -1))
        else:
            nxt = (bx + (1 if tx > bx else -1), by)
        if any(world.tiles.blocks(c) or not world.tiles.in_bounds(c) for c in self.cells_at(nxt)):
            self.timer = 0.4
            return
        self.walk_to = nxt
        self.dir = (nxt[0] - bx, nxt[1] - by)
        self.state, self.timer = WALK, ec.BOAR_WALK_STEP

    def _walk(self, dt: float, world: "World") -> None:
        bx, by = round(self.pos[0]), round(self.pos[1])
        tx, ty = self.walk_to or (bx, by)
        p = 1 - max(0.0, self.timer) / ec.BOAR_WALK_STEP
        sx, sy = tx - self.dir[0], ty - self.dir[1]
        self.pos = (sx + (tx - sx) * p, sy + (ty - sy) * p)
        if self.timer <= 0:
            self.pos = (float(tx), float(ty))
            self.state, self.timer = THINK, 0.25

    def _charge(self, dt: float, world: "World") -> None:
        dx, dy = self.dir
        move = ec.BOAR_CHARGE_SPEED * dt * world.enemy_speed
        x, y = self.pos
        nx, ny = x + dx * move, y + dy * move
        w, h = world.level.width, world.level.height
        # the next whole cell the body is entering
        lead = (math.ceil(nx) if dx > 0 else math.floor(nx) if dx < 0 else round(x),
                math.ceil(ny) if dy > 0 else math.floor(ny) if dy < 0 else round(y))
        stop = (lead[0] - dx, lead[1] - dy)
        if not (0 <= lead[0] <= w - 2 and 0 <= lead[1] <= h - 2):
            self._stop(world, stop, None)
            return
        stumps = sorted(c for c in self.cells_at(lead) if world.tiles.blocks(c))
        if stumps:
            self._stop(world, stop, stumps)
            return
        before = self.travelled
        self.travelled += move
        self.pos = (nx, ny)
        if int(self.travelled) != int(before) and int(self.travelled) % ec.BOAR_PIT_EVERY == 0:
            self._drop_pit(world)

    def _drop_pit(self, world: "World") -> None:
        """A pit in one of the two cells the boar just left."""
        dx, dy = self.dir
        bx, by = round(self.pos[0]), round(self.pos[1])
        behind = self.cells_at((bx - dx, by - dy)) - self.body()
        opts = sorted(behind)
        if not opts:
            return
        cell = opts[self.pits % len(opts)]
        frog = world.frog.ground_cell()
        tile = world.tiles.tile(cell)
        if cell == frog or tile is None or tile.kind != SOLID or tile.unstable is not None \
                or not tile.standable:
            return
        self.pits += 1
        world.make_hole(cell, ec.BOAR_PIT_TIME)

    def _stop(self, world: "World", cell: Cell, stumps: list[Cell] | None) -> None:
        self.pos = (float(cell[0]), float(cell[1]))
        self.state = STUN
        if stumps:
            self.last_stumps = list(stumps)
            for s in stumps:
                world.tiles.set_kind(s, SOLID)
                self.broken.append(s)
                world.emit(Event("earth.stump_break", cell=s))
            self.stun_kind = "stump"
            self.stun(ec.BOAR_STUMP_STUN)
            self.open_window(ec.BOAR_STUMP_STUN)
        else:
            self.stun_kind = "edge"
            self.stun(ec.BOAR_EDGE_STUN)
        world.emit(Event("earth.boar_crash", pos=self.center(), value=self.stun_kind))

    def take_hit(self, world: "World") -> bool:
        if not super().take_hit(world):
            return False
        # this crash's stump did its job; older broken ones still grow back
        self.broken = [c for c in self.broken if c not in self.last_stumps]
        if not self.defeated:
            self.stunned = min(self.stunned, 0.8)
        return True

    def _do_stomp(self, world: "World") -> None:
        frog = world.frog_target or world.frog.cell
        body = self.body()
        cand = [c for c, t in world.tiles.items()
                if t.standable and t.unstable is None and t.kind == SOLID and c not in body]
        near = [c for c in cand if 1 <= manhattan(c, frog) <= ec.BOAR_STOMP_RADIUS]
        world.rng.shuffle(near)
        rest = [c for c in cand if c not in near]
        world.rng.shuffle(rest)
        pick = (near + rest)[:ec.BOAR_STOMP_CELLS]
        spec = world.level.unstable_spec
        for c in pick:
            t = world.tiles.tile(c)
            t.unstable = Unstable(spec.warn, spec.gone, "step")
            t.unstable.start_warning()
            self.crumbling.append(c)
            world.emit(Event("tile_warn", cell=c))
        self.stomp_cells = tuple(pick)
        world.emit(Event("earth.stomp", pos=self.center(), value=len(pick)))

    def _tidy_tiles(self, world: "World") -> None:
        for c in list(self.crumbling):          # stomp tiles: plain grass again once back
            t = world.tiles.tile(c)
            if t is None or t.unstable is None or (t.unstable.state == STABLE and t.unstable.back_t > 0.5):
                if t is not None:
                    t.unstable = None
                self.crumbling.remove(c)
        if self.broken and self.window <= 0 and self.stunned <= 0 and not self.defeated:
            frog = world.frog.ground_cell()
            for c in list(self.broken):          # missed the chance: the stump grows back
                t = world.tiles.tile(c)
                if c != frog and c not in self.body() and t is not None and t.standable:
                    world.tiles.set_kind(c, OBSTACLE)
                    self.broken.remove(c)
                    world.emit(Event("earth.stump_grow", cell=c))

    @property
    def stumps_left(self) -> int:
        return len(self.broken)


def stump_cells(world: "World") -> list[Cell]:
    return sorted(c for c, t in world.tiles.items() if t.kind == OBSTACLE)


__all__ = ["Boar", "stump_cells", "DIRS"]

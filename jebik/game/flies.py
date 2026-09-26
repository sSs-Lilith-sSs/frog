"""Flies, dragonflies, golden flies and fireflies (no pygame).

Positions are floats in cell units; a fly "is on" the cell nearest to it.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable

from .. import config
from .grid import Cell, Level

COUNTED_KINDS = ("fly", "dragon")
SPECIAL_KINDS = ("gold", "firefly")

# Fly states
FLYING = "flying"
RESTING = "resting"      # sitting on a cell (wings still)
HOVER = "hover"          # short pause in the air
LEAVING = "leaving"      # flying off the field, removed at the end


def nearest_cell(pos: tuple[float, float]) -> Cell:
    return (math.floor(pos[0] + 0.5), math.floor(pos[1] + 0.5))


@dataclass
class Fly:
    id: int
    kind: str
    pos: tuple[float, float]
    state: str = HOVER
    start: tuple[float, float] = (0.0, 0.0)
    ctrl: tuple[float, float] = (0.0, 0.0)
    target: tuple[float, float] = (0.0, 0.0)
    t: float = 0.0
    duration: float = 1.0
    wait: float = 0.3
    age: float = 0.0
    caught: bool = False
    heading: float = 0.0          # radians, for dragonfly rotation
    phase: float = field(default_factory=lambda: random.random() * 6.28)

    @property
    def cell(self) -> Cell:
        return nearest_cell(self.pos)

    @property
    def counted(self) -> bool:
        return self.kind in COUNTED_KINDS

    @property
    def value(self) -> int:
        return config.FLY_VALUE[self.kind]

    @property
    def airborne(self) -> bool:
        return self.state != RESTING


class FlyManager:
    """Owns all flies, their flight and the spawn schedule."""

    def __init__(self, level: Level, rng: random.Random, auto_spawn: bool = True,
                 can_rest: Callable[[Cell], bool] | None = None):
        self.level = level
        self.can_rest = can_rest or level.is_pad      # live tiles (World passes TileMap)
        self.rng = rng
        self.auto_spawn = auto_spawn
        self.flies: list[Fly] = []
        self._next_id = 1
        self.target_count = rng.randint(config.FLY_MIN, config.FLY_MAX)
        self.respawn_timers: list[float] = []
        self.gold_timer = rng.uniform(*config.GOLD_INTERVAL)
        self.firefly_timer = rng.uniform(*config.FIREFLY_INTERVAL)
        self.spawned: list[Fly] = []      # new flies since last drain (for events)

    # ------------------------------------------------------------ spawning
    def populate(self, avoid: Cell) -> None:
        """Initial flies, already inside the field."""
        for _ in range(self.target_count):
            cell = self._random_cell(avoid, radius=2)
            self.spawn_at(self._roll_counted_kind(), cell)

    def spawn_at(self, kind: str, cell: Cell, rest: float | None = None) -> Fly:
        fly = Fly(self._next_id, kind, (float(cell[0]), float(cell[1])))
        self._next_id += 1
        if rest is not None:
            fly.state, fly.wait = RESTING, rest
        else:
            fly.state, fly.wait = HOVER, self.rng.uniform(0.2, 1.2)
        self.flies.append(fly)
        self.spawned.append(fly)
        return fly

    def spawn_from_edge(self, kind: str, avoid: Cell) -> Fly:
        lv = self.level
        side = self.rng.randrange(4)
        if side == 0:
            start = (self.rng.uniform(0, lv.width - 1), -1.2)
        elif side == 1:
            start = (lv.width + 0.2, self.rng.uniform(0, lv.height - 1))
        elif side == 2:
            start = (self.rng.uniform(0, lv.width - 1), lv.height + 0.2)
        else:
            start = (-1.2, self.rng.uniform(0, lv.height - 1))
        fly = Fly(self._next_id, kind, start)
        self._next_id += 1
        self.flies.append(fly)
        self.spawned.append(fly)
        target = self._random_cell(avoid, radius=1)
        self._fly_to(fly, (float(target[0]), float(target[1])))
        return fly

    def _roll_counted_kind(self) -> str:
        return "dragon" if self.rng.random() < config.DRAGON_CHANCE else "fly"

    def _random_cell(self, avoid: Cell, radius: int) -> Cell:
        lv = self.level
        cells = [c for c in lv.cells()
                 if abs(c[0] - avoid[0]) + abs(c[1] - avoid[1]) > radius]
        pads = [c for c in cells if self.can_rest(c)]
        pool = pads if pads and self.rng.random() > config.FLY_WATER_CHANCE else cells
        return self.rng.choice(pool or list(lv.cells()))

    # ------------------------------------------------------------ queries
    def get(self, fly_id: int | None) -> Fly | None:
        for f in self.flies:
            if f.id == fly_id:
                return f
        return None

    def counted_alive(self) -> int:
        return sum(1 for f in self.flies if f.counted and f.state != LEAVING)

    def at_cell(self, cell: Cell) -> list[Fly]:
        return [f for f in self.flies if not f.caught and f.cell == cell
                and self.level.in_bounds(f.cell)]

    def remove(self, fly: Fly) -> None:
        if fly in self.flies:
            self.flies.remove(fly)
            if fly.counted and self.auto_spawn:
                self.respawn_timers.append(self.rng.uniform(*config.FLY_RESPAWN_DELAY))

    def carry_row(self, row: int, direction: int, width: int) -> None:
        """A moving row shifted: resting flies ride along (wrapping around)."""
        for fly in self.flies:
            if fly.state == RESTING and not fly.caught and fly.cell[1] == row:
                x = (fly.cell[0] + direction) % width
                fly.pos = (float(x), fly.pos[1])

    def unrest_where(self, gone: Callable[[Cell], bool]) -> None:
        """Flies sitting on a vanished tile take off."""
        for fly in self.flies:
            if fly.state == RESTING and not fly.caught and gone(fly.cell):
                fly.state, fly.wait = HOVER, self.rng.uniform(*config.FLY_SHORT_PAUSE)

    def drain_spawned(self) -> list[Fly]:
        out, self.spawned = self.spawned, []
        return out

    # ------------------------------------------------------------ update
    def update(self, dt: float, frog_cell: Cell) -> None:
        for fly in list(self.flies):
            if fly.caught:
                continue
            fly.age += dt
            if fly.kind in SPECIAL_KINDS and fly.state != LEAVING \
                    and fly.age > config.SPECIAL_LIFETIME and self.auto_spawn:
                self._leave(fly)
            if fly.state == FLYING or fly.state == LEAVING:
                self._advance(fly, dt)
            else:
                fly.wait -= dt
                if fly.wait <= 0:
                    self._pick_next(fly, frog_cell)
        if self.auto_spawn:
            self._update_spawns(dt, frog_cell)

    def _update_spawns(self, dt: float, frog_cell: Cell) -> None:
        for i in range(len(self.respawn_timers)):
            self.respawn_timers[i] -= dt
        due = [t for t in self.respawn_timers if t <= 0]
        self.respawn_timers = [t for t in self.respawn_timers if t > 0]
        for _ in due:
            self.target_count = self.rng.randint(config.FLY_MIN, config.FLY_MAX)
        pending = len(self.respawn_timers)
        while self.counted_alive() + pending < self.target_count:
            self.spawn_from_edge(self._roll_counted_kind(), frog_cell)
        for kind, attr, interval in (("gold", "gold_timer", config.GOLD_INTERVAL),
                                     ("firefly", "firefly_timer", config.FIREFLY_INTERVAL)):
            if any(f.kind == kind for f in self.flies):
                continue
            left = getattr(self, attr) - dt
            if left <= 0:
                self.spawn_from_edge(kind, frog_cell)
                left = self.rng.uniform(*interval)
            setattr(self, attr, left)

    def _pick_next(self, fly: Fly, frog_cell: Cell) -> None:
        lo, hi = config.DRAGON_HOP_RANGE if fly.kind == "dragon" else config.FLY_HOP_RANGE
        lv = self.level
        taken = {f.cell for f in self.flies if f is not fly and f.state == RESTING}
        taken |= {nearest_cell(f.target) for f in self.flies if f is not fly and f.state == FLYING}
        cx, cy = fly.cell
        options = []
        for c in lv.cells():
            d = abs(c[0] - cx) + abs(c[1] - cy)
            if lo <= d <= hi and c != frog_cell and c not in taken:
                options.append(c)
        if not options:
            fly.state, fly.wait = HOVER, 0.4
            return
        pads = [c for c in options if self.can_rest(c)]
        water = [c for c in options if not self.can_rest(c)]
        if water and (not pads or self.rng.random() < config.FLY_WATER_CHANCE):
            pool = water
        else:
            pool = pads
        target = self.rng.choice(pool)
        self._fly_to(fly, (float(target[0]), float(target[1])))

    def _fly_to(self, fly: Fly, target: tuple[float, float], leaving: bool = False) -> None:
        speed = config.DRAGON_SPEED if fly.kind == "dragon" else config.FLY_SPEED
        sx, sy = fly.pos
        tx, ty = target
        dist = math.hypot(tx - sx, ty - sy)
        # curved flight: control point pushed sideways from the midpoint
        bend = self.rng.uniform(-0.6, 0.6) * min(1.0, dist)
        nx, ny = (-(ty - sy) / dist, (tx - sx) / dist) if dist > 1e-6 else (0.0, 0.0)
        fly.start = fly.pos
        fly.ctrl = ((sx + tx) / 2 + nx * bend, (sy + ty) / 2 + ny * bend)
        fly.target = target
        fly.t = 0.0
        fly.duration = max(0.25, dist * 1.1 / speed)
        fly.state = LEAVING if leaving else FLYING

    def _advance(self, fly: Fly, dt: float) -> None:
        fly.t = min(1.0, fly.t + dt / fly.duration)
        t = fly.t
        u = 1 - t
        (sx, sy), (cx, cy), (tx, ty) = fly.start, fly.ctrl, fly.target
        nx = u * u * sx + 2 * u * t * cx + t * t * tx
        ny = u * u * sy + 2 * u * t * cy + t * t * ty
        if (nx, ny) != fly.pos:
            fly.heading = math.atan2(ny - fly.pos[1], nx - fly.pos[0])
        fly.pos = (nx, ny)
        if fly.t >= 1.0:
            if fly.state == LEAVING:
                self.flies.remove(fly)
                return
            if self.rng.random() < config.FLY_REST_CHANCE and fly.kind != "dragon":
                # sit down on a pad; over water it just hovers for a while
                on_pad = self.can_rest(fly.cell)
                fly.state = RESTING if on_pad else HOVER
                fly.wait = self.rng.uniform(*config.FLY_REST_TIME)
            else:
                fly.state, fly.wait = HOVER, self.rng.uniform(*config.FLY_SHORT_PAUSE)

    def _leave(self, fly: Fly) -> None:
        lv = self.level
        x, y = fly.pos
        exits = [(-1.5, y), (lv.width + 0.5, y), (x, -1.5), (x, lv.height + 0.5)]
        target = min(exits, key=lambda p: math.hypot(p[0] - x, p[1] - y))
        self._fly_to(fly, target, leaving=True)

"""Mutable tile map of a running level: solid / hole / obstacle + hazards.

A :class:`~jebik.game.grid.Level` is the frozen layout from the text file;
:class:`TileMap` is its live copy inside a :class:`~jebik.game.world.World`.
Every cell holds a :class:`Tile` object. Tiles keep a stable ``id`` so the
renderer can cache one sprite per tile even when moving rows carry tiles to
other cells.

Generic hazards (all worlds can use them, tuned per level):

* **unstable** tiles (sinking pad / crumbling ground / melting cloud):
  ``STABLE -> WARNING (flicker, ``warn`` s) -> GONE (``gone`` s) -> STABLE``,
  triggered when the frog lands on them (``trigger=step``) or on a timer
  (``trigger=cycle``);
* **temporary holes** made by enemies (mole, boar, whale), restored after N s;
* **obstacles** (stumps) that nobody can enter;
* **moving rows**: every ``period`` s a row shifts by one cell (tiles wrap
  around), carrying whatever stands on it.

No pygame here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .. import config
from .events import (Event, HOLE_CLOSE, HOLE_OPEN, ROW_SHIFT, TILE_BACK,
                     TILE_GONE, TILE_WARN)
from .grid import DIRS, Cell, Level, UnstableSpec

SOLID = "solid"
HOLE = "hole"
OBSTACLE = "obstacle"

# unstable tile states
STABLE = "stable"
WARNING = "warning"
GONE = "gone"


@dataclass
class Unstable:
    """Timed state machine of one unstable tile."""
    warn: float = config.UNSTABLE_WARN
    gone: float = config.UNSTABLE_GONE
    trigger: str = "step"            # "step" (frog lands) | "cycle" (own timer)
    stable: float = config.UNSTABLE_STABLE   # cycle mode: time spent stable
    state: str = STABLE
    timer: float = 0.0               # time left in the current state (warn/gone/cycle)
    back_t: float = 99.0             # seconds since it came back (pop-in anim)

    @property
    def present(self) -> bool:
        return self.state != GONE

    @property
    def progress(self) -> float:
        """0..1 through the current WARNING / GONE phase."""
        if self.state == WARNING:
            return 1.0 - self.timer / self.warn if self.warn else 1.0
        if self.state == GONE:
            return 1.0 - self.timer / self.gone if self.gone else 1.0
        return 0.0

    def start_warning(self) -> bool:
        if self.state != STABLE:
            return False
        self.state, self.timer = WARNING, self.warn
        return True

    def update(self, dt: float) -> str | None:
        """Advance; returns the new state name on a transition."""
        self.back_t += dt
        if self.state == STABLE:
            if self.trigger != "cycle":
                return None
            self.timer -= dt
            if self.timer <= 0:
                self.start_warning()
                return WARNING
            return None
        self.timer -= dt
        if self.timer > 0:
            return None
        if self.state == WARNING:
            self.state, self.timer = GONE, self.gone
            return GONE
        self.state, self.timer, self.back_t = STABLE, self.stable, 0.0
        return STABLE


@dataclass
class Tile:
    id: int
    kind: str = SOLID
    unstable: Unstable | None = None
    hole_timer: float = 0.0          # > 0: temporarily a hole, restores itself
    hole_time: float = 0.0           # full duration of the current temp hole

    @property
    def standable(self) -> bool:
        return (self.kind == SOLID and self.hole_timer <= 0
                and (self.unstable is None or self.unstable.present))


@dataclass
class MovingRow:
    row: int
    direction: int                   # +1 right, -1 left
    period: float
    timer: float = 0.0
    slide: float = 99.0              # seconds since the last shift (render slide)

    def visual_offset(self) -> float:
        """Render offset in cells: tiles slide into their new cell."""
        k = self.slide / config.ROW_SLIDE_TIME
        return -self.direction * (1.0 - k) if k < 1.0 else 0.0


@dataclass
class TileMap:
    width: int
    height: int
    tiles: dict[Cell, Tile] = field(default_factory=dict)
    rows: dict[int, MovingRow] = field(default_factory=dict)
    version: int = 0                 # bumps on every walkability change

    @classmethod
    def from_level(cls, level: Level) -> "TileMap":
        tm = cls(level.width, level.height)
        spec: UnstableSpec = level.unstable_spec
        for x, y in level.cells():
            cell = (x, y)
            kind = SOLID if cell in level.pads else OBSTACLE if cell in level.obstacles else HOLE
            tile = Tile(id=y * level.width + x, kind=kind)
            if cell in level.unstable:
                # cycle mode: stagger the timers so tiles don't blink in sync
                offset = ((x * 7 + y * 13) % 10) / 10 * spec.stable
                tile.unstable = Unstable(spec.warn, spec.gone, spec.trigger, spec.stable,
                                         timer=spec.stable + offset)
            tm.tiles[cell] = tile
        for mr in level.moving_rows:
            tm.rows[mr.row] = MovingRow(mr.row, mr.direction, mr.period, timer=mr.period)
        return tm

    # ------------------------------------------------------------ queries
    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def tile(self, cell: Cell) -> Tile | None:
        return self.tiles.get(cell)

    def standable(self, cell: Cell) -> bool:
        t = self.tiles.get(cell)
        return t is not None and t.standable

    def is_hole(self, cell: Cell) -> bool:
        """In bounds and nothing to stand on (water, pit, abyss, gone tile)."""
        t = self.tiles.get(cell)
        return t is not None and t.kind != OBSTACLE and not t.standable

    def blocks(self, cell: Cell) -> bool:
        t = self.tiles.get(cell)
        return t is not None and t.kind == OBSTACLE

    def neighbors(self, cell: Cell) -> Iterator[Cell]:
        """4-neighbours one can stand on (the default walking graph)."""
        for dx, dy in DIRS:
            n = (cell[0] + dx, cell[1] + dy)
            if self.standable(n):
                yield n

    def standable_cells(self) -> list[Cell]:
        return [c for c, t in self.tiles.items() if t.standable]

    def items(self) -> Iterator[tuple[Cell, Tile]]:
        return iter(self.tiles.items())

    def row_offset(self, row: int) -> float:
        mr = self.rows.get(row)
        return mr.visual_offset() if mr else 0.0

    # ------------------------------------------------------------ changes
    def on_land(self, cell: Cell) -> list[Event]:
        """Frog landed here: step-triggered unstable tiles start warning."""
        t = self.tiles.get(cell)
        if t and t.unstable and t.unstable.trigger == "step" and t.unstable.start_warning():
            return [Event(TILE_WARN, cell=cell)]
        return []

    def make_hole(self, cell: Cell, duration: float) -> list[Event]:
        """Temporarily turn a solid tile into a hole (restored after ``duration``)."""
        t = self.tiles.get(cell)
        if t is None or t.kind != SOLID:
            return []
        was = t.standable
        t.hole_timer = max(t.hole_timer, duration)
        t.hole_time = max(t.hole_time, t.hole_timer)
        if was:
            self.version += 1
        return [Event(HOLE_OPEN, cell=cell, value=duration)]

    def set_kind(self, cell: Cell, kind: str) -> None:
        """Permanent change (e.g. a boss rebuilding the clouds)."""
        t = self.tiles.get(cell)
        if t is not None and t.kind != kind:
            t.kind = kind
            self.version += 1

    def shift_row(self, row: int, direction: int) -> None:
        """Shift every tile of ``row`` by one cell (wrapping around)."""
        cells = [(x, row) for x in range(self.width)]
        old = [self.tiles[c] for c in cells]
        for x in range(self.width):
            self.tiles[((x + direction) % self.width, row)] = old[x]
        self.version += 1

    def update(self, dt: float) -> list[Event]:
        out: list[Event] = []
        for cell, t in self.tiles.items():
            if t.unstable is not None:
                change = t.unstable.update(dt)
                if change == WARNING:
                    out.append(Event(TILE_WARN, cell=cell))
                elif change == GONE:
                    self.version += 1
                    out.append(Event(TILE_GONE, cell=cell))
                elif change == STABLE:
                    self.version += 1
                    out.append(Event(TILE_BACK, cell=cell))
            if t.hole_timer > 0:
                t.hole_timer -= dt
                if t.hole_timer <= 0:
                    t.hole_timer = t.hole_time = 0.0
                    self.version += 1
                    out.append(Event(HOLE_CLOSE, cell=cell))
        for mr in self.rows.values():
            mr.slide += dt
            mr.timer -= dt
            if mr.timer <= 0:
                mr.timer += mr.period
                mr.slide = 0.0
                self.shift_row(mr.row, mr.direction)
                out.append(Event(ROW_SHIFT, cell=(0, mr.row), value=mr.direction))
        return out

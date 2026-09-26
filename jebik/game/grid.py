"""Level grid: text-map parsing, directions and BFS helpers (no pygame).

Level file format (``jebik/worlds/<world>/levels/<w>-<n>.txt``)::

    # comment
    id: 2-1                    # world index - level index (default: file name)
    world: earth               # world package id
    size: 14x9                 # optional check against the map
    flies_needed: 10
    par_time: 80               # ★★★ time (seconds)
    tobi_time: 115             # TOBI PIZDA countdown (seconds)
    cell: 50                   # optional fixed cell size in px (else adaptive, <= 80)
    top_reserve: 160           # optional px kept free above the field (boss art)
    spawn: S=snake, P=pike:hole   # map letters -> enemy kinds (":hole" = not a tile)
    enemies: swallow; hawk @ 3 4 speed=1.2   # extra enemies (optional "@ x y", key=value)
    boss: whale hp=3           # the level's boss (also counted as an enemy)
    unstable: warn=1.5 gone=4 trigger=step   # parameters of 'U' tiles
    moving: 2 right 3.0; 5 left 2.5          # rows that shift every N seconds
    ---
    OOOO##OO
    OFOUXOSO

Map characters: ``O`` solid tile, ``#`` hole, ``F`` frog start (solid),
``U`` unstable tile (solid), ``X`` obstacle (stump); any letter declared in
``spawn:`` marks an enemy start (``S`` = snake by default).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from .. import config

Cell = tuple[int, int]

# Direction indices: 0 = up, 1 = right, 2 = down, 3 = left (clockwise, like
# the art's ``face`` argument).
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
DIRS: tuple[Cell, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))

SOLID_CHARS = {"O", "F", "U"}
HOLE_CHARS = {"#"}
OBSTACLE_CHARS = {"X"}
DEFAULT_SPAWNS = {"S": ("snake", False)}      # letter -> (kind, stands on a hole)


class LevelError(ValueError):
    """Raised when a level file is malformed."""


def step(cell: Cell, direction: int, dist: int = 1) -> Cell:
    dx, dy = DIRS[direction]
    return (cell[0] + dx * dist, cell[1] + dy * dist)


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def dir_between(a: Cell, b: Cell) -> int | None:
    """Direction of a unit step from ``a`` to ``b`` (None if not adjacent)."""
    d = (b[0] - a[0], b[1] - a[1])
    return DIRS.index(d) if d in DIRS else None


@dataclass(frozen=True)
class Spawn:
    """One enemy of a level: registry ``kind``, optional start cell, params."""
    kind: str
    cell: Cell | None = None
    params: tuple[tuple[str, str], ...] = ()

    def param(self, key: str, default: float) -> float:
        for k, v in self.params:
            if k == key:
                try:
                    return float(v)
                except ValueError:
                    return default
        return default

    def text(self, key: str, default: str = "") -> str:
        return next((v for k, v in self.params if k == key), default)


@dataclass(frozen=True)
class UnstableSpec:
    warn: float = config.UNSTABLE_WARN
    gone: float = config.UNSTABLE_GONE
    trigger: str = "step"
    stable: float = config.UNSTABLE_STABLE


@dataclass(frozen=True)
class MovingRowSpec:
    row: int
    direction: int          # +1 right, -1 left
    period: float


@dataclass(frozen=True)
class Level:
    id: str
    world: str
    width: int
    height: int
    pads: frozenset[Cell]                    # solid tiles at start (incl. unstable)
    frog_start: Cell
    spawns: tuple[Spawn, ...] = ()
    flies_needed: int = 5
    par_time: float = 90.0
    tobi_time: float = 120.0
    seed: int = 0
    obstacles: frozenset[Cell] = frozenset()
    unstable: frozenset[Cell] = frozenset()
    unstable_spec: UnstableSpec = UnstableSpec()
    moving_rows: tuple[MovingRowSpec, ...] = ()
    boss: str | None = None
    cell: int | None = None                  # fixed cell size override (px)
    top_reserve: int = 0                     # px kept free above the field
    meta: dict[str, str] = field(default_factory=dict, compare=False, hash=False)

    @property
    def world_index(self) -> int:
        return int(self.id.split("-")[0])

    @property
    def level_index(self) -> int:
        return int(self.id.split("-")[1])

    @property
    def snake_starts(self) -> tuple[Cell, ...]:
        return tuple(s.cell for s in self.spawns if s.kind == "snake" and s.cell is not None)

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def is_pad(self, cell: Cell) -> bool:
        return cell in self.pads

    def is_water(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.pads and cell not in self.obstacles

    @property
    def holes(self) -> frozenset[Cell]:
        return frozenset(c for c in self.cells() if c not in self.pads and c not in self.obstacles)

    def cells(self) -> Iterator[Cell]:
        for y in range(self.height):
            for x in range(self.width):
                yield (x, y)

    def pad_neighbors(self, cell: Cell) -> Iterator[Cell]:
        for d in range(4):
            n = step(cell, d)
            if n in self.pads:
                yield n


# ---------------------------------------------------------------- parsing
def _split_header(text: str) -> tuple[dict[str, str], list[str]]:
    meta: dict[str, str] = {}
    rows: list[str] = []
    in_map = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if in_map:
            if line.strip():
                rows.append(line.strip())
            continue
        stripped = line.split(" #", 1)[0].strip() if not line.lstrip().startswith("#") else ""
        if not stripped:
            continue
        if stripped == "---":
            in_map = True
            continue
        sep = ":" if ":" in stripped else "=" if "=" in stripped else None
        if sep is None:
            raise LevelError(f"bad header line: {raw!r}")
        key, value = stripped.split(sep, 1)
        meta[key.strip().lower()] = value.strip()
    if not rows:
        raise LevelError("level has no map (missing '---' separator?)")
    return meta, rows


def _num(meta: dict[str, str], key: str, default: float, cast=float):
    try:
        return cast(meta[key]) if key in meta else default
    except ValueError as exc:
        raise LevelError(f"bad number for {key!r}: {meta[key]!r}") from exc


def _params(words: list[str]) -> tuple[tuple[str, str], ...]:
    out = []
    for w in words:
        if "=" not in w:
            raise LevelError(f"expected key=value, got {w!r}")
        k, v = w.split("=", 1)
        out.append((k.strip().lower(), v.strip()))
    return tuple(out)


def parse_spawn_item(item: str) -> Spawn:
    """``"hawk @ 3 4 speed=1.2"`` -> Spawn("hawk", (3, 4), (("speed", "1.2"),))."""
    words = item.replace("@", " @ ").split()
    if not words:
        raise LevelError("empty enemy entry")
    kind, rest, cell = words[0].lower(), words[1:], None
    if rest and rest[0] == "@":
        try:
            cell = (int(rest[1]), int(rest[2]))
        except (IndexError, ValueError) as exc:
            raise LevelError(f"bad enemy cell in {item!r}") from exc
        rest = rest[3:]
    return Spawn(kind, cell, _params(rest))


def _spawn_legend(meta: dict[str, str]) -> dict[str, tuple[str, bool]]:
    legend = dict(DEFAULT_SPAWNS)
    for item in filter(None, (p.strip() for p in meta.get("spawn", "").split(","))):
        if "=" not in item:
            raise LevelError(f"bad spawn legend {item!r} (want X=kind)")
        ch, kind = (s.strip() for s in item.split("=", 1))
        on_hole = kind.endswith(":hole")
        kind = kind.removesuffix(":hole").strip().lower()
        if len(ch) != 1 or ch in SOLID_CHARS | HOLE_CHARS | OBSTACLE_CHARS or not kind:
            raise LevelError(f"bad spawn legend {item!r}")
        legend[ch] = (kind, on_hole)
    return legend


def _moving_rows(meta: dict[str, str], height: int) -> tuple[MovingRowSpec, ...]:
    out = []
    for item in filter(None, (p.strip() for p in meta.get("moving", "").split(";"))):
        words = item.split()
        try:
            row, way, period = int(words[0]), words[1].lower(), float(words[2])
        except (IndexError, ValueError) as exc:
            raise LevelError(f"bad moving row {item!r} (want 'row right|left seconds')") from exc
        if way not in ("left", "right") or not 0 <= row < height or period <= 0:
            raise LevelError(f"bad moving row {item!r}")
        out.append(MovingRowSpec(row, 1 if way == "right" else -1, period))
    return tuple(out)


def _unstable_spec(meta: dict[str, str]) -> UnstableSpec:
    params = dict(_params(meta.get("unstable", "").split()))
    trig = params.get("trigger", "step")
    if trig not in ("step", "cycle"):
        raise LevelError(f"bad unstable trigger {trig!r}")
    return UnstableSpec(warn=_num(params, "warn", config.UNSTABLE_WARN),
                        gone=_num(params, "gone", config.UNSTABLE_GONE), trigger=trig,
                        stable=_num(params, "stable", config.UNSTABLE_STABLE))


def parse_level(text: str, level_id: str | None = None) -> Level:
    """Parse the text format described in the module docstring."""
    meta, rows = _split_header(text)
    width, height = len(rows[0]), len(rows)
    if any(len(r) != width for r in rows):
        raise LevelError("map rows have different lengths")
    if "size" in meta:
        try:
            sw, sh = (int(v) for v in meta["size"].lower().split("x"))
        except ValueError as exc:
            raise LevelError(f"bad size {meta['size']!r}") from exc
        if (sw, sh) != (width, height):
            raise LevelError(f"size says {sw}x{sh}, map is {width}x{height}")

    legend = _spawn_legend(meta)
    pads: set[Cell] = set()
    obstacles: set[Cell] = set()
    unstable: set[Cell] = set()
    frog: Cell | None = None
    spawns: list[Spawn] = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            cell = (x, y)
            if ch in SOLID_CHARS:
                pads.add(cell)
            elif ch in OBSTACLE_CHARS:
                obstacles.add(cell)
            elif ch in legend:
                kind, on_hole = legend[ch]
                if not on_hole:
                    pads.add(cell)
                spawns.append(Spawn(kind, cell))
            elif ch not in HOLE_CHARS:
                raise LevelError(f"unknown map char {ch!r} at {x},{y}")
            if ch == "U":
                unstable.add(cell)
            elif ch == "F":
                if frog is not None:
                    raise LevelError("more than one frog start 'F'")
                frog = cell
    if frog is None:
        raise LevelError("no frog start 'F'")

    for item in filter(None, (p.strip() for p in meta.get("enemies", "").split(";"))):
        spawns.append(parse_spawn_item(item))
    boss = None
    if meta.get("boss"):
        b = parse_spawn_item(meta["boss"])
        boss = b.kind
        spawns.append(b)
    for s in spawns:
        if s.cell is not None and not (0 <= s.cell[0] < width and 0 <= s.cell[1] < height):
            raise LevelError(f"enemy {s.kind} starts outside the map: {s.cell}")

    lid = meta.get("id", level_id or "0-0")
    flies = _num(meta, "flies_needed", 5, int)
    if flies < 1:
        raise LevelError("flies_needed must be >= 1")
    cell_px = _num(meta, "cell", 0, int) or None
    return Level(id=lid, world=meta.get("world", "water"), width=width, height=height,
                 pads=frozenset(pads), frog_start=frog, spawns=tuple(spawns),
                 flies_needed=flies, par_time=_num(meta, "par_time", 90.0),
                 tobi_time=_num(meta, "tobi_time", config.TOBI_DEFAULT_TIME),
                 seed=_num(meta, "seed", 0, int), obstacles=frozenset(obstacles),
                 unstable=frozenset(unstable), unstable_spec=_unstable_spec(meta),
                 moving_rows=_moving_rows(meta, height), boss=boss, cell=cell_px,
                 top_reserve=_num(meta, "top_reserve", 0, int), meta=meta)


def load_level(level_id: str) -> Level:
    """Load ``"w-n"`` from its world package (see :mod:`jebik.worlds`)."""
    from ..worlds import catalog
    return catalog.load_level(level_id)


def level_exists(level_id: str) -> bool:
    from ..worlds import catalog
    return catalog.level_path(level_id) is not None


# ---------------------------------------------------------------- search
def bfs_path(start: Cell, goal: Cell,
             neighbors: Callable[[Cell], Iterable[Cell]]) -> list[Cell] | None:
    """Shortest path ``[start, ..., goal]`` or None if unreachable."""
    if start == goal:
        return [start]
    prev: dict[Cell, Cell] = {start: start}
    queue: deque[Cell] = deque([start])
    while queue:
        cur = queue.popleft()
        for n in neighbors(cur):
            if n in prev:
                continue
            prev[n] = cur
            if n == goal:
                path = [n]
                while path[-1] != start:
                    path.append(prev[path[-1]])
                return path[::-1]
            queue.append(n)
    return None


def bfs_distances(start: Cell,
                  neighbors: Callable[[Cell], Iterable[Cell]]) -> dict[Cell, int]:
    dist = {start: 0}
    queue: deque[Cell] = deque([start])
    while queue:
        cur = queue.popleft()
        for n in neighbors(cur):
            if n not in dist:
                dist[n] = dist[cur] + 1
                queue.append(n)
    return dist

"""Level grid: parsing of text maps, directions and BFS helpers (no pygame)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator

from .. import config

Cell = tuple[int, int]

# Direction indices: 0 = up, 1 = right, 2 = down, 3 = left (clockwise, like
# the art's ``face`` argument).
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
DIRS: tuple[Cell, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))

PAD_CHARS = {"O", "F", "S"}
WATER_CHARS = {"#"}


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
class Level:
    id: str
    world: str
    width: int
    height: int
    pads: frozenset[Cell]
    frog_start: Cell
    snake_starts: tuple[Cell, ...] = ()
    flies_needed: int = 5
    par_time: float = 90.0
    seed: int = 0
    meta: dict[str, str] = field(default_factory=dict, compare=False, hash=False)

    @property
    def world_index(self) -> int:
        return int(self.id.split("-")[0])

    @property
    def level_index(self) -> int:
        return int(self.id.split("-")[1])

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def is_pad(self, cell: Cell) -> bool:
        return cell in self.pads

    def is_water(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.pads

    @property
    def holes(self) -> frozenset[Cell]:
        return frozenset(c for c in self.cells() if c not in self.pads)

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
def parse_level(text: str, level_id: str | None = None) -> Level:
    """Parse the text format::

        # comment
        id: 1-1
        world: water
        flies_needed: 5
        par_time: 70
        ---
        OOOO##OO
        OFOO#OSO

    ``O`` pad, ``#`` water, ``F`` frog start (a pad), ``S`` snake start (a pad).
    """
    meta: dict[str, str] = {}
    rows: list[str] = []
    in_map = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not in_map:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped == "---":
                in_map = True
                continue
            sep = ":" if ":" in stripped else "=" if "=" in stripped else None
            if sep is None:
                raise LevelError(f"bad header line: {raw!r}")
            key, value = stripped.split(sep, 1)
            meta[key.strip().lower()] = value.strip()
        else:
            if line.strip():
                rows.append(line.strip())
    if not rows:
        raise LevelError("level has no map (missing '---' separator?)")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise LevelError("map rows have different lengths")
    height = len(rows)
    if "size" in meta:
        try:
            sw, sh = (int(v) for v in meta["size"].lower().split("x"))
        except ValueError as exc:
            raise LevelError(f"bad size {meta['size']!r}") from exc
        if (sw, sh) != (width, height):
            raise LevelError(f"size says {sw}x{sh}, map is {width}x{height}")

    pads: set[Cell] = set()
    frog: Cell | None = None
    snakes: list[Cell] = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in PAD_CHARS:
                pads.add((x, y))
            elif ch not in WATER_CHARS:
                raise LevelError(f"unknown map char {ch!r} at {x},{y}")
            if ch == "F":
                if frog is not None:
                    raise LevelError("more than one frog start 'F'")
                frog = (x, y)
            elif ch == "S":
                snakes.append((x, y))
    if frog is None:
        raise LevelError("no frog start 'F'")

    lid = meta.get("id", level_id or "0-0")
    try:
        flies = int(meta.get("flies_needed", 5))
        par = float(meta.get("par_time", 90))
        seed = int(meta.get("seed", 0))
    except ValueError as exc:
        raise LevelError(f"bad numeric meta: {exc}") from exc
    if flies < 1:
        raise LevelError("flies_needed must be >= 1")
    return Level(id=lid, world=meta.get("world", "water"), width=width,
                 height=height, pads=frozenset(pads), frog_start=frog,
                 snake_starts=tuple(snakes), flies_needed=flies,
                 par_time=par, seed=seed, meta=meta)


def level_path(level_id: str) -> Path:
    return config.LEVELS_DIR / f"{level_id}.txt"


def level_exists(level_id: str) -> bool:
    return level_path(level_id).is_file()


def load_level(level_id: str) -> Level:
    return parse_level(level_path(level_id).read_text(encoding="utf-8"), level_id)


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

"""The snake: BFS chaser that only ever crawls over tiles (no pygame)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from ...game.enemy import Enemy, register_enemy
from ...game.grid import Cell, Level, Spawn, bfs_path, manhattan
from . import config as wc

if TYPE_CHECKING:
    from ...game.world import World

WANDER = "wander"
CHASE = "chase"
RETREAT = "retreat"


@register_enemy("snake")
@dataclass(eq=False)
class Snake(Enemy):
    level: Level
    rng: random.Random
    cells: list[Cell]                  # head first; positions at step start
    next_cell: Cell | None = None      # head is moving into this cell
    t: float = 0.0                     # 0..1 progress of the current step
    step_time: float = wc.SNAKE_WANDER_STEP
    mode: str = WANDER
    retreat: float = 0.0
    visited: set[Cell] = field(default_factory=set)   # for tests / debugging
    anim: float = 0.0                  # free-running clock for wiggle
    world: "World | None" = field(default=None, repr=False)

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Snake":
        snake = cls.spawn(world.level, spawn.cell or world.level.frog_start, world.rng,
                          length=int(spawn.param("length", wc.SNAKE_LENGTH)))
        snake.world = world
        return snake

    @classmethod
    def spawn(cls, level: Level, start: Cell, rng: random.Random,
              length: int = wc.SNAKE_LENGTH) -> "Snake":
        """Lay the body out along tiles behind the head."""
        cells = [start]
        while len(cells) < length:
            tail = cells[-1]
            options = [n for n in level.pad_neighbors(tail) if n not in cells]
            if not options:
                break
            cells.append(rng.choice(sorted(options)))
        while len(cells) < length:          # cramped start: stack on the tail
            cells.append(cells[-1])
        snake = cls(level=level, rng=rng, cells=cells)
        snake.visited.update(cells)
        return snake

    # ------------------------------------------------------------ geometry
    @property
    def head(self) -> Cell:
        return self.cells[0]

    @property
    def pos(self) -> tuple[float, float]:              # type: ignore[override]
        return self.segment_positions()[0]

    def segment_positions(self) -> list[tuple[float, float]]:
        """Continuous positions of head and body segments (cell units)."""
        t = self.t if self.next_cell is not None else 0.0
        out = []
        targets = [self.next_cell or self.cells[0]] + self.cells[:-1]
        for cur, nxt in zip(self.cells, targets):
            out.append((cur[0] + (nxt[0] - cur[0]) * t, cur[1] + (nxt[1] - cur[1]) * t))
        return out

    def head_dir(self) -> tuple[float, float]:
        pos = self.segment_positions()
        a = self.next_cell or self.cells[0]
        b = self.cells[0] if self.next_cell else self.cells[1]
        dx, dy = a[0] - b[0], a[1] - b[1]
        if dx == 0 and dy == 0 and len(pos) > 1:
            dx, dy = pos[0][0] - pos[1][0], pos[0][1] - pos[1][1]
        n = math.hypot(dx, dy) or 1.0
        return (dx / n, dy / n)

    def occupied(self) -> set[Cell]:
        occ = set(self.cells)
        if self.next_cell is not None:
            occ.add(self.next_cell)
        return occ

    def touches(self, pos: tuple[float, float], radius: float = 0.55) -> bool:
        return any(math.hypot(px - pos[0], py - pos[1]) < radius
                   for px, py in self.segment_positions())

    def hurts(self, world: "World", frog_pos: tuple[float, float]) -> bool:
        return self.touches(frog_pos, self.contact_radius)

    def _neighbors(self, cell: Cell) -> Iterator[Cell]:
        if self.world is not None:
            return self.world.tiles.neighbors(cell)
        return self.level.pad_neighbors(cell)

    # ------------------------------------------------------------ reactions
    def start_retreat(self) -> None:
        self.retreat = wc.SNAKE_RETREAT_TIME

    def on_frog_hit(self, world: "World") -> None:
        self.start_retreat()

    def on_frog_respawn(self, world: "World", cell: Cell) -> None:
        if manhattan(self.head, cell) <= wc.SNAKE_SIGHT:   # no spawn camping
            self.start_retreat()

    # ------------------------------------------------------------ behaviour
    def update(self, dt: float, world: "World") -> None:
        self.world = world
        frog_cell = world.frog_target
        self.anim += dt
        if self.retreat > 0:
            self.retreat -= dt
        if self.next_cell is None:
            self._decide(frog_cell)
            return
        self.t += dt / self.step_time * world.enemy_speed
        if self.t >= 1.0:
            self.cells = [self.next_cell] + self.cells[:-1]
            self.visited.add(self.next_cell)
            self.next_cell = None
            leftover = (self.t - 1.0) * self.step_time
            self.t = 0.0
            self._decide(frog_cell)
            if self.next_cell is not None and leftover > 0:
                self.t = min(0.99, leftover / self.step_time)

    def _free_neighbors(self) -> list[Cell]:
        body = set(self.cells[:-1])          # the tail moves away this step
        return [n for n in self._neighbors(self.head) if n not in body]

    def _decide(self, frog_cell: Cell | None) -> None:
        options = self._free_neighbors()
        if not options:
            self.cells.reverse()             # dead end: turn around
            return
        dist = manhattan(self.head, frog_cell) if frog_cell is not None else 99
        if self.retreat > 0 and frog_cell is not None:
            self.mode = RETREAT
        elif self.mode == CHASE and dist <= wc.SNAKE_LOSE_SIGHT:
            self.mode = CHASE
        elif dist <= wc.SNAKE_SIGHT:
            self.mode = CHASE
        else:
            self.mode = WANDER

        choice: Cell | None = None
        if self.mode == RETREAT:
            best = max(manhattan(o, frog_cell) for o in options)
            choice = self.rng.choice([o for o in options if manhattan(o, frog_cell) == best])
            self.step_time = wc.SNAKE_WANDER_STEP * 0.8
        elif self.mode == CHASE and frog_cell is not None:
            path = self.path_to(frog_cell)
            if path and len(path) > 1:
                choice = path[1]
                self.step_time = wc.SNAKE_CHASE_STEP
            else:
                self.mode = WANDER
        if choice is None:
            choice = self._wander_choice(options)
            self.step_time = wc.SNAKE_WANDER_STEP
        self.next_cell = choice
        self.t = 0.0

    def path_to(self, goal: Cell) -> list[Cell] | None:
        """Shortest tile-only path; the body (except the tail) blocks."""
        blocked = set(self.cells[1:-1])

        def nbrs(c: Cell):
            for n in self._neighbors(c):
                if n not in blocked:
                    yield n
        return bfs_path(self.head, goal, nbrs)

    def _wander_choice(self, options: list[Cell]) -> Cell:
        # keep going straight more often than turning -> calmer motion
        if len(self.cells) > 1:
            hx, hy = self.head
            px, py = self.cells[1]
            straight = (2 * hx - px, 2 * hy - py)
            if straight in options and self.rng.random() < 0.55:
                return straight
        return self.rng.choice(sorted(options))

"""QA player bot for ``tools/qa_soak.py`` (invariants live in ``qa_checks``).

The bot only *decides* from the world state; its actions are sent to the
real game as synthesized key events (see ``qa_run.LevelRun``).
"""
from __future__ import annotations

import random
from collections import deque

from jebik.game import flies as fm
from jebik.game.enemy import AIR, UNDER, Boss
from jebik.game.grid import DIRS, step
from jebik.game.rules import PLAYING
from jebik.game.tiles import OBSTACLE, WARNING

# ---------------------------------------------------------------- bot


def _line(world, cell, d, reach):
    out = []
    for k in range(1, reach + 1):
        c = step(cell, d, k)
        if not world.level.in_bounds(c):
            break
        out.append(c)
    return out


def danger_cells(world) -> set:
    """Cells the bot avoids: telegraphs, enemies (+ neighbours), crumbling tiles."""
    lv = world.level
    out: set = set()
    for e in world.enemies:
        for tg in e.telegraphs():
            cells = set(tg.cells)
            if tg.style == "arrow" and tg.direction is not None:
                for c in tg.cells:           # an edge arrow sweeps its whole row / column
                    dx, dy = DIRS[tg.direction]
                    cells |= {(x, c[1]) for x in range(lv.width)} if dx else \
                        {(c[0], y) for y in range(lv.height)}
            out |= cells
        if isinstance(e, Boss) and e.defeated or e.layer == UNDER:
            continue
        if e.layer == AIR and not (-1 <= e.pos[1] <= lv.height):
            continue
        for c in e.occupied():
            if e.supports(c):
                continue                         # a platform (whale back), not a threat
            out.add(c)
            if e.stunned <= 0:
                out |= {step(c, d) for d in range(4)}
    for c, t in world.tiles.items():
        if t.unstable is not None and t.unstable.state == WARNING:
            out.add(c)
    for row, mr in world.tiles.rows.items():         # the edge a row carries you off
        out.add((lv.width - 1 if mr.direction > 0 else 0, row))
    return out


class Bot:
    """Greedy player: tongue a fly when aligned, walk (BFS, super jumps over
    holes) toward the nearest acceptable fly / the exit / a boss opening,
    avoid telegraphed cells. ``noise`` = chance of a random action."""

    def __init__(self, seed: int, noise: float = 0.0):
        self.rng = random.Random(seed)
        self.noise = noise
        self.cooldown = 0.0

    # returns a list of ("move", d, super) / ("tongue", d|None) / ("wait",)
    def decide(self, world, dt: float) -> tuple | None:
        self.cooldown -= dt
        f = world.frog
        if world.state != PLAYING or not f.can_act or f.buffered is not None or self.cooldown > 0:
            return None
        if self.rng.random() < self.noise:
            self.cooldown = self.rng.uniform(0.0, 0.3)
            if self.rng.random() < 0.3:
                return ("tongue", self.rng.randrange(4))
            return ("move", self.rng.randrange(4), self.rng.random() < 0.2)
        danger = danger_cells(world)
        act = self._boss_tongue(world)
        if act:
            return act
        if not world.full:
            act = self._fly_tongue(world)
            if act:
                return act
        goals = self._goals(world, danger)
        here = f.cell
        if here in danger or not goals:
            if here in danger:
                mv = self._path(world, here, None, danger, escape=True)
                if mv:
                    return ("move",) + mv
            self.cooldown = 0.1
            return None
        if here in goals:
            self.cooldown = 0.1
            return None
        mv = self._path(world, here, goals, danger)
        if mv is None:                       # no safe route now: wander a bit
            self.cooldown = 0.25
            if self.rng.random() < 0.3:
                d = self.rng.randrange(4)
                n = step(here, d)
                if world.can_stand(n) and n not in danger:
                    return ("move", d, False)
            return None
        return ("move",) + mv

    # ------------------------------------------------------------ goals
    def _acceptable(self, world, fly) -> bool:
        if fly.caught or fly.state == fm.LEAVING or not world.level.in_bounds(fly.cell):
            return False
        if fly.kind in fm.COUNTED_KINDS:
            return not world.full and world.eaten + fly.value <= world.needed
        if fly.kind == "gold":
            return world.time_left is not None or world.hearts < world.rules.max_hearts
        return True

    def _fly_tongue(self, world):
        f = world.frog
        if f.tongue_cd > 0:
            return None
        for d in range(4):
            for c in _line(world, f.cell, d, f.tongue_range):
                here = world.flies.at_cell(c)
                if here:
                    if all(self._acceptable(world, fl) for fl in here):
                        return ("tongue", d)
                    break
        return None

    def _boss_tongue(self, world):
        boss = world.boss
        f = world.frog
        if boss is None or boss.defeated or f.tongue_cd > 0:
            return None
        if not (boss.vulnerable or getattr(boss, "halo_flying", False)):
            return None
        for d in range(4):
            line = _line(world, f.cell, d, f.tongue_range)
            idx = boss.tongue_hit(world, line)
            if idx is None:
                continue
            fly_before = any(world.flies.at_cell(c) for c in line[:idx + 1])
            if not fly_before:
                return ("tongue", d)
        return None

    def _aligned_cells(self, world, targets, reach) -> set:
        out = set()
        for t in targets:
            for d in range(4):
                for k in range(1, reach + 1):
                    c = step(t, d, k)
                    if world.level.in_bounds(c):
                        out.add(c)
        return out

    def _goals(self, world, danger) -> set:
        f = world.frog
        if world.exit_cell is not None:
            return {world.exit_cell}
        boss = world.boss
        if boss is not None and not boss.defeated:
            g = self._boss_goals(world, boss)
            if g and (world.full or self.rng.random() < 0.7):
                return g
        if world.full:
            return set()
        cells = [fl.cell for fl in world.flies.flies if self._acceptable(world, fl)]
        goals = set(cells) | self._aligned_cells(world, cells, f.tongue_range)
        bad = {fl.cell for fl in world.flies.flies if not self._acceptable(world, fl)}
        return {c for c in goals if c not in bad and world.can_stand(c)}

    def _boss_goals(self, world, boss) -> set:
        kind = boss.kind
        f = world.frog
        if kind == "whale" and boss.surfaced and boss.blowhole:
            return {c for c in boss.back if c != boss.blowhole and c in
                    self._aligned_cells(world, [boss.blowhole], f.tongue_range)}
        if kind == "boar":
            body = boss.body()
            if boss.vulnerable:
                return self._aligned_cells(world, body, f.tongue_range) - body
            cx, cy = boss.center()
            out = set()
            for c, t in world.tiles.items():
                if t.kind != OBSTACLE:
                    continue
                for d in range(4):
                    dx, dy = DIRS[d]
                    if (c[0] - cx) * dx + (c[1] - cy) * dy <= 0.5:
                        continue            # stand on the far side of the stump
                    for k in (1, 2):
                        n = step(c, d, k)
                        if world.tiles.standable(n):
                            out.add(n)
            return out
        return set()

    # ------------------------------------------------------------ path
    def _path(self, world, start, goals, danger, escape=False):
        f = world.frog
        lv = world.level
        can_super = f.super_cd <= 0
        full = world.full
        flies_bad = set()
        for fl in world.flies.flies:
            if not self._acceptable(world, fl):
                flies_bad.add(fl.cell)

        def ok(c, first):
            if not lv.in_bounds(c) or world.blocked(c) or not world.can_stand(c):
                return False
            if c in flies_bad and (full or first):
                return False
            return True

        prev = {start: None}
        q = deque([start])
        while q:
            c = q.popleft()
            first = prev[c] is None
            for d in range(4):
                for k, sup in ((1, False), (2, True)):
                    if sup and not (first and can_super):
                        continue
                    n = step(c, d, k)
                    if n in prev or not ok(n, first):
                        continue
                    if n in danger and not (goals and n in goals and not escape):
                        continue
                    prev[n] = (c, d, sup)
                    if (escape and n not in danger) or (goals and n in goals):
                        while prev[n][0] != start:
                            n = prev[n][0]
                        return (prev[n][1], prev[n][2])
                    q.append(n)
        return None

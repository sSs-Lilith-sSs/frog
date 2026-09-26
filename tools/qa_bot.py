"""QA helpers for ``tools/qa_soak.py``: a white-box player bot and per-frame
invariant checks on a running :class:`~jebik.game.world.World`.

The bot only *decides* from the world state; its actions are sent to the
real game as synthesized key events (see ``qa_soak.Harness``).
"""
from __future__ import annotations

import math
import random
from collections import deque

from jebik import config
from jebik.game import events as ev
from jebik.game import flies as fm
from jebik.game import frog as fs
from jebik.game.enemy import AIR, UNDER, Boss
from jebik.game.grid import DIRS, manhattan, step
from jebik.game.rules import PLAYING
from jebik.game.tiles import OBSTACLE, SOLID, WARNING

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


# ---------------------------------------------------------------- invariants


def _finite(p) -> bool:
    return p is not None and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)


def reachable_solid(world, start) -> set:
    """Cells reachable over permanently solid tiles (hops + super jumps)."""
    tiles = world.tiles
    seen = {start}
    q = deque([start])
    while q:
        c = q.popleft()
        for d in range(4):
            for k in (1, 2):
                n = step(c, d, k)
                t = tiles.tile(n)
                if n in seen or t is None or t.kind != SOLID:
                    continue
                seen.add(n)
                q.append(n)
    return seen


class Checker:
    """Per-frame invariants of one GameScene; ``report(kind, detail)`` records issues."""

    def __init__(self, report, world):
        self.report = report
        self.t = 0.0
        self.stuck_state = 0.0
        self.no_flies = 0.0
        self.exit_bad = 0.0
        self.exit_unreach = 0.0
        self.floating = 0
        self.last_reach = -9.0
        self.fly_seen: dict[int, tuple] = {}
        self._start_checks(world)

    def _start_checks(self, world):
        lv = world.level
        s = lv.frog_start
        if not world.tiles.standable(s):
            self.report("spawn_on_hole", f"frog start {s} not standable")
        for e in world.enemies:
            if not (isinstance(e, Boss)) and e.layer != UNDER and s in e.occupied():
                self.report("spawn_in_enemy", f"{e.kind} at frog start {s}")

    def events(self, world, events):
        for e in events:
            if e.kind == ev.EXIT_SPAWN:
                c = e.cell
                if c is None or not world.tiles.standable(c):
                    self.report("exit_on_hole", f"exit {c} not standable at spawn")
                elif c == world.frog.ground_cell():
                    self.report("exit_under_frog", f"exit {c} spawned under the frog")
            elif e.kind == ev.RESPAWN:
                c = e.cell
                if not world.can_stand(c):
                    self.report("respawn_on_hole", f"respawn {c} not standable")
                for en in world.enemies:
                    if en.hurts(world, c) and not (isinstance(en, Boss) and en.defeated):
                        self.report("respawn_in_enemy", f"respawn {c} inside {en.kind}")

    def frame(self, world, dt):
        self.t += dt
        lv = world.level
        f = world.frog
        if not _finite(f.pos()):
            self.report("nan_frog", f"frog pos {f.pos()}")
        if world.state != PLAYING:
            return
        # frog standing on nothing (should have fallen)
        if f.grounded and not world.can_stand(f.cell):
            self.floating += 1
            if self.floating > 2:
                self.report("frog_floating", f"frog {f.state} at {f.cell} on no ground")
        else:
            self.floating = 0
        if f.state in (fs.IDLE, fs.TONGUE, fs.HIT) and not lv.in_bounds(f.cell):
            self.report("frog_out", f"frog {f.state} out of bounds {f.cell}")
        # stuck in a transient state
        if f.state in (fs.HOP, fs.SUPER, fs.TONGUE, fs.SPLASH, fs.HIT):
            self.stuck_state += dt
            if self.stuck_state > 6:
                self.report("frog_stuck_state", f"frog stuck in {f.state} for 6 s")
                self.stuck_state = -1e9
        else:
            self.stuck_state = 0.0
        # flies
        for fl in world.flies.flies:
            if not _finite(fl.pos):
                self.report("nan_fly", f"{fl.kind} pos {fl.pos}")
                continue
            x, y = fl.pos
            if not (-3 <= x <= lv.width + 2 and -3 <= y <= lv.height + 2):
                self.report("fly_far", f"{fl.kind} {fl.state} at ({x:.1f},{y:.1f})")
            key = self.fly_seen.get(fl.id)
            if key is None or key[0] != fl.pos:
                self.fly_seen[fl.id] = (fl.pos, self.t)
            elif self.t - key[1] > 15 and not fl.caught:
                self.report("fly_frozen", f"{fl.kind} {fl.state} frozen at {fl.pos} 15 s")
                self.fly_seen[fl.id] = (fl.pos, 1e9)
        if not world.full and world.flies.counted_alive() == 0 and not world.flies.respawn_timers:
            self.no_flies += dt
            if self.no_flies > 12:
                self.report("no_flies", "no counted flies and none pending for 12 s")
                self.no_flies = -1e9
        else:
            self.no_flies = max(0.0, self.no_flies) if self.no_flies > -1 else self.no_flies
        # enemies
        for e in world.enemies:
            if not _finite(e.pos):
                self.report("nan_enemy", f"{e.kind} pos {e.pos}")
                continue
            x, y = e.pos
            m = 8 if e.layer == AIR else 1.0
            if not (-m <= x <= lv.width - 1 + m and -m <= y <= lv.height - 1 + m):
                self.report("enemy_out", f"{e.kind} at ({x:.1f},{y:.1f}) layer={e.layer}")
        # exit
        ex = world.exit_cell
        if ex is not None:
            t = world.tiles.tile(ex)
            if t is None or t.kind != SOLID:
                self.report("exit_destroyed", f"exit tile {ex} became {t and t.kind}")
            if not world.tiles.standable(ex):
                self.exit_bad += dt
                if self.exit_bad > 12:
                    self.report("exit_gone_long", f"exit {ex} not standable for 12 s")
                    self.exit_bad = -1e9
            elif self.exit_bad > -1:
                self.exit_bad = 0.0
            if self.t - self.last_reach > 1.0:
                self.last_reach = self.t
                if ex not in reachable_solid(world, f.ground_cell()):
                    self.exit_unreach += 1.0
                    if self.exit_unreach > 5:
                        self.report("exit_unreachable", f"exit {ex} unreachable from {f.ground_cell()}")
                        self.exit_unreach = -1e9
                elif self.exit_unreach > -1:
                    self.exit_unreach = 0.0


def safe_neighbor_to(world, cell):
    """(frog cell, direction) to hop onto ``cell`` (forced wins)."""
    for d in range(4):
        n = step(cell, (d + 2) % 4)
        if world.tiles.standable(n) and not world.blocked(n):
            return n, d
    return None


__all__ = ["Bot", "Checker", "danger_cells", "reachable_solid", "safe_neighbor_to", "manhattan",
           "config"]

"""Per-frame invariants of a running level for ``tools/qa_soak.py``: NaN
positions, the frog floating / stuck / out of the field, frozen or far-away flies,
no flies for long, enemies leaving the field, the exit on a hole or unreachable,
spawn / respawn inside hazards."""
from __future__ import annotations

import math
from collections import deque

from jebik.game import events as ev
from jebik.game import frog as fs
from jebik.game.enemy import AIR, UNDER, Boss
from jebik.game.grid import step
from jebik.game.rules import PLAYING
from jebik.game.tiles import SOLID


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
            if e.kind == "swallow" and e.state == "wait":
                continue                         # parked off the field between passes
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

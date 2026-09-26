"""Кит — the water boss (no pygame).

A 6x3 silhouette swims under the field and attacks:

* **surface** (Виринання): red 3x3 zone, then it surfaces — the frog in the
  zone is hit and the pads there sink for ``WHALE_SINK_TIME``. Its back stays
  up ``WHALE_BACK_TIME`` (vulnerability window): the frog can stand on it and
  tongue the blowhole (zone centre) = 1 hit. Then a ``WHALE_DIVE_WARN``
  warning and it dives (a frog still on a sunk cell falls).
* **fountain** (Фонтан): dashed row / column, then a water jet along it.
* **wave** (Хвиля): arrows on an edge, then a wave front rolls across and
  shoves the grounded frog one cell (a super jump clears it).
* **gulp** (Ковток): mouth at an edge pulls the frog and the flies toward it.

Enraged (half the flies eaten): shorter pauses and warnings, a cross-shaped
fountain, a faster wave and combos (a second attack right away).
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...game import flies as fm
from ...game.enemy import GROUND, UNDER, Boss, Telegraph, register_enemy
from ...game.events import BOSS_TELL, Event
from ...game.grid import DIRS, DOWN, LEFT, RIGHT, UP, Cell, Spawn
from . import config as wc

if TYPE_CHECKING:
    from ...game.world import World

CALM, SWIM = "calm", "swim"
SURF_WARN, BACK, DIVE_WARN = "surface_warn", "back", "dive_warn"
FOUNTAIN_WARN, JET = "fountain_warn", "jet"
WAVE_WARN, WAVE = "wave_warn", "wave"
GULP_WARN, GULP = "gulp_warn", "gulp"
GONE = "gone"
ATTACKS = ("surface", "fountain", "wave", "gulp")


@register_enemy("whale")
class Whale(Boss):
    name_key = "water.boss"
    hit_text_key = "water.whale_hit"
    layer = UNDER

    def __init__(self) -> None:
        self.pos = (0.0, 0.0)
        self.goal = (0.0, 0.0)
        self.facing = -1                  # -1: head left (as drawn), +1: head right
        self.state, self.timer = CALM, wc.WHALE_START_DELAY
        self.anim = self.stunned = self.window = self.hit_flash = 0.0
        self.hp, self.defeated, self.alive = 3, False, True
        self.zone: tuple[Cell, ...] = ()
        self.blowhole: Cell | None = None
        self.back: frozenset[Cell] = frozenset()
        self.lines: list[tuple[tuple[Cell, ...], int]] = []   # (cells, direction)
        self.push_dir = RIGHT
        self.front = 0.0
        self.pushed = False
        self.gulp_step = 0.0
        self.since_surface = 0
        self.combo = False
        self.warn_total = 1.0
        self.mouth: Cell = (0, 0)
        self.level_size = (1, 1)
        self.attacks: list[str] = []      # history (tests / debugging)

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Whale":
        whale: Whale = super().create(world, spawn)          # type: ignore[assignment]
        lv = world.level
        start = spawn.cell or (lv.width // 2, lv.height // 2)
        whale.pos = whale.goal = (float(start[0]), float(start[1]))
        whale.level_size = (lv.width, lv.height)
        return whale

    # ------------------------------------------------------------ queries
    @property
    def surfaced(self) -> bool:
        return self.state in (BACK, DIVE_WARN)

    def supports(self, cell: Cell) -> bool:
        return self.surfaced and cell in self.back

    def blocks(self, cell: Cell) -> bool:
        return self.surfaced and cell == self.blowhole

    def occupied(self) -> set[Cell]:
        return set(self.back) if self.surfaced else set()

    def hurts(self, world: "World", frog_pos) -> bool:
        return False                      # all damage is dealt by attacks

    def center(self):
        return self.pos

    def tongue_hit(self, world: "World", line: list[Cell]) -> int | None:
        if self.surfaced and self.blowhole in line and world.frog.cell in self.back:
            return line.index(self.blowhole)
        return None

    def on_tongued(self, world: "World") -> None:
        if self.take_hit(world):
            self._set(DIVE_WARN, wc.WHALE_DIVE_WARN)

    def telegraphs(self) -> list[Telegraph]:
        p = max(0.0, min(1.0, 1 - self.timer / self.warn_total)) if self.warn_total else 1.0
        if self.state == SURF_WARN:
            return [Telegraph("zone", self.zone, p)]
        if self.state == DIVE_WARN:
            return [Telegraph("dive", tuple(sorted(self.back)), p)]
        if self.state in (FOUNTAIN_WARN, JET):
            style = "line" if self.state == FOUNTAIN_WARN else "jet"
            return [Telegraph(style, cells, p, d) for cells, d in self.lines]
        if self.state == WAVE_WARN:
            return [Telegraph("arrow", (c,), p, self.push_dir) for c in self._edge_cells()[1::3]]
        if self.state == WAVE:
            return [Telegraph("wave", self.front_cells(), p, self.push_dir)]
        if self.state in (GULP_WARN, GULP):
            return [Telegraph("gulp", (self.mouth_cell(),), p, self.push_dir)]
        return []

    # ------------------------------------------------------------ helpers
    def _set(self, state: str, seconds: float) -> None:
        self.state, self.timer, self.warn_total = state, seconds, seconds
        self.layer = GROUND if state in (BACK, DIVE_WARN) else UNDER

    def _warn(self, world: "World", seconds: float) -> float:
        return seconds * (wc.WHALE_ENRAGED_WARN if self.enraged(world) else 1.0)

    def _edge_cells(self) -> list[Cell]:
        """Cells of the edge the wave / gulp comes from (wave) or goes to (gulp)."""
        w, h = self.level_size
        dx, dy = DIRS[self.push_dir]
        if dx:
            x = 0 if dx > 0 else w - 1
            return [(x, y) for y in range(h)]
        y = 0 if dy > 0 else h - 1
        return [(x, y) for x in range(w)]

    def front_cells(self) -> tuple[Cell, ...]:
        w, h = self.level_size
        f = round(self.front)
        if DIRS[self.push_dir][0]:
            return tuple((f, y) for y in range(h)) if 0 <= f < w else ()
        return tuple((x, f) for x in range(w)) if 0 <= f < h else ()

    def mouth_cell(self) -> Cell:
        """Edge cell the gulp pulls toward (``push_dir`` points at it)."""
        w, h = self.level_size
        x, y = self.mouth
        return (min(w - 1, max(0, x)), min(h - 1, max(0, y)))

    def _swim(self, dt: float) -> None:
        x, y = self.pos
        gx, gy = self.goal
        d = math.hypot(gx - x, gy - y)
        if d > 0.05:
            self.facing = -1 if gx < x - 0.05 else (1 if gx > x + 0.05 else self.facing)
        s = wc.WHALE_SWIM_SPEED * dt
        self.pos = (gx, gy) if d <= s else (x + (gx - x) / d * s, y + (gy - y) / d * s)

    # ------------------------------------------------------------ update
    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.level_size = (world.level.width, world.level.height)
        dt *= world.enemy_speed
        self.timer -= dt
        self._swim(dt)
        st = self.state
        if st in (CALM, SWIM):
            if self.timer <= 0 and not self.defeated and world.frog_target is not None:
                self.start_attack(world)
            elif self.defeated or math.dist(self.pos, self.goal) < 0.1:
                lv = world.level
                self.goal = (world.rng.uniform(1, lv.width - 2), world.rng.uniform(1, lv.height - 2))
        elif st == SURF_WARN and self.timer <= 0:
            self._surface(world)
        elif st == BACK and self.timer <= 0:
            self._set(DIVE_WARN, wc.WHALE_DIVE_WARN)
        elif st == DIVE_WARN and self.timer <= 0:
            self._set(SWIM, self._gap(world))
            world._ground_check()          # a frog left on a sunk cell falls
        elif st == FOUNTAIN_WARN and self.timer <= 0:
            self._set(JET, wc.WHALE_JET_TIME)
            world.emit(Event("water.jet", value=[c for cells, _ in self.lines for c in cells]))
        elif st == JET:
            frog = world.frog_target
            if frog is not None and any(frog in cells for cells, _ in self.lines):
                world.hurt_frog(self)
            if self.timer <= 0:
                self._finish(world)
        elif st == WAVE_WARN and self.timer <= 0:
            self._set(WAVE, 99.0)
            w, h = self.level_size
            self.front = {RIGHT: -1.0, DOWN: -1.0, LEFT: float(w), UP: float(h)}[self.push_dir]
            self.pushed = False
            world.emit(Event("water.wave", value=self.push_dir))
        elif st == WAVE:
            self._update_wave(dt, world)
        elif st == GULP_WARN and self.timer <= 0:
            self._set(GULP, wc.WHALE_GULP_TIME)
            self.gulp_step = wc.WHALE_GULP_STEP * 0.5
            world.emit(Event("water.gulp", cell=self.mouth_cell(), value=self.push_dir))
        elif st == GULP:
            self._update_gulp(dt, world)
            if self.timer <= 0:
                self._finish(world)

    def _gap(self, world: "World") -> float:
        lo, hi = wc.WHALE_GAP_ENRAGED if self.enraged(world) else wc.WHALE_GAP
        return world.rng.uniform(lo, hi)

    def _finish(self, world: "World") -> None:
        if self.enraged(world) and not self.combo and world.rng.random() < wc.WHALE_COMBO_CHANCE:
            self.combo = True
            self.start_attack(world, combo=True)
            return
        self.combo = False
        self._set(SWIM, self._gap(world))

    # ------------------------------------------------------------ attacks
    def start_attack(self, world: "World", kind: str | None = None, combo: bool = False) -> None:
        frog = world.frog_target or world.frog.cell
        if kind is None:
            if not combo and (self.since_surface >= wc.WHALE_SURFACE_EVERY or world.rng.random() < 0.35):
                kind = "surface"
            else:
                kind = world.rng.choice(ATTACKS[1:])
        self.attacks.append(kind)
        world.emit(Event(BOSS_TELL, pos=self.pos, value=(self.kind, kind)))
        getattr(self, "_start_" + kind)(world, frog)
        self.since_surface = 0 if kind == "surface" else self.since_surface + 1

    def _start_surface(self, world: "World", frog: Cell) -> None:
        lv = world.level
        zx = min(lv.width - 2, max(1, frog[0]))
        zy = min(lv.height - 2, max(1, frog[1]))
        self.blowhole = (zx, zy)
        self.zone = tuple((x, y) for y in range(zy - 1, zy + 2) for x in range(zx - 1, zx + 2))
        self.facing = -1 if zx + 4 <= lv.width - 1 else 1
        cols = range(zx - 1, zx + 5) if self.facing < 0 else range(zx - 4, zx + 2)
        self.back = frozenset((x, y) for x in cols for y in range(zy - 1, zy + 2) if lv.in_bounds((x, y)))
        self.goal = (zx + 1.5 * -self.facing, float(zy))
        self._set(SURF_WARN, self._warn(world, wc.WHALE_SURFACE_WARN))

    def _surface(self, world: "World") -> None:
        self._set(BACK, wc.WHALE_BACK_TIME)
        self.pos = self.goal
        self.open_window(wc.WHALE_BACK_TIME)
        world.emit(Event("water.whale_surface", cell=self.blowhole, value=self.zone))
        if world.frog_target in self.zone:
            world.hurt_frog(self)
        for c in self.zone:
            world.make_hole(c, wc.WHALE_SINK_TIME)

    def _start_fountain(self, world: "World", frog: Cell) -> None:
        lv = world.level
        row = (tuple((x, frog[1]) for x in range(lv.width)), RIGHT)
        col = (tuple((frog[0], y) for y in range(lv.height)), DOWN)
        if self.enraged(world):
            self.lines = [row, col]
        else:
            self.lines = [world.rng.choice([row, col])]
        self.goal = (float(frog[0]), float(frog[1]))
        self._set(FOUNTAIN_WARN, self._warn(world, wc.WHALE_FOUNTAIN_WARN))

    def _start_wave(self, world: "World", frog: Cell) -> None:
        self.push_dir = world.rng.choice((UP, RIGHT, DOWN, LEFT))
        self._set(WAVE_WARN, self._warn(world, wc.WHALE_WAVE_WARN))

    def _update_wave(self, dt: float, world: "World") -> None:
        dx, dy = DIRS[self.push_dir]
        speed = wc.WHALE_WAVE_SPEED_ENRAGED if self.enraged(world) else wc.WHALE_WAVE_SPEED
        self.front += (dx + dy) * speed * dt
        w, h = self.level_size
        frog = world.frog
        coord = frog.pos()[0] if dx else frog.pos()[1]
        if not self.pushed and abs(self.front - coord) < 0.5:
            self.pushed = True
            if world.frog_target is not None:
                world.push_frog(self.push_dir, 1)
        limit = w if dx else h
        if self.front < -1.5 or self.front > limit + 0.5:
            self._finish(world)

    def _start_gulp(self, world: "World", frog: Cell) -> None:
        lv = world.level
        # the mouth opens at the edge nearest to the frog
        dists = {LEFT: frog[0], RIGHT: lv.width - 1 - frog[0], UP: frog[1], DOWN: lv.height - 1 - frog[1]}
        self.push_dir = min(dists, key=lambda d: (dists[d], d))
        dx, dy = DIRS[self.push_dir]
        mx = -1 if dx < 0 else (lv.width if dx > 0 else frog[0])
        my = -1 if dy < 0 else (lv.height if dy > 0 else frog[1])
        self.mouth = (mx, my)
        self.goal = (min(lv.width - 1.0, max(0.0, mx)), min(lv.height - 1.0, max(0.0, my)))
        self._set(GULP_WARN, self._warn(world, wc.WHALE_GULP_WARN))

    def _edge_distance(self, pos) -> float:
        dx, dy = DIRS[self.push_dir]
        w, h = self.level_size
        if dx:
            return pos[0] if dx < 0 else w - 1 - pos[0]
        return pos[1] if dy < 0 else h - 1 - pos[1]

    def _update_gulp(self, dt: float, world: "World") -> None:
        dx, dy = DIRS[self.push_dir]
        self.gulp_step -= dt
        frog = world.frog_target
        if self.gulp_step <= 0:
            self.gulp_step += wc.WHALE_GULP_STEP
            if frog is not None and self._edge_distance(frog) <= wc.WHALE_GULP_RANGE:
                world.push_frog(self.push_dir, 1)
        mx, my = self.mouth
        s = wc.WHALE_GULP_FLY_SPEED * dt
        for fly in list(world.flies.flies):
            if fly.caught or fly.state == fm.LEAVING or self._edge_distance(fly.pos) > wc.WHALE_GULP_RANGE:
                continue
            if fly.state in (fm.FLYING, fm.RESTING):
                fly.state = fm.HOVER
            fly.wait = max(fly.wait, 0.3)
            x, y = fly.pos
            fly.pos = (x + dx * s, y + dy * s)
            if (dx and abs(fly.pos[0] - mx) < 0.6) or (dy and abs(fly.pos[1] - my) < 0.6):
                world.flies.remove(fly)          # swallowed (it respawns later)

"""Boss «Ісус» (level 3-4): stands on a big cloud above the field (no pygame).

Attacks (one at a time, the halo boomerang every second attack):

* ``beams``    — a row or column glows for 1 s (``"line"`` telegraph), then a
  beam from his palms burns it for 0.5 s (enraged: the frog's row *and* column);
* ``multiply`` — «примноження»: 10–15 extra flies (dangerous for exact N);
* ``halo``     — the halo flies an arc over the field, hovers next to the frog
  and comes back. Catch it with the tongue -> it flies back and bonks him on
  the head: one hit, popup «SASAT!» (``hit_text_key``);
* ``rebuild``  — some clouds vanish (temporary holes) and others appear; both
  are telegraphed and never chosen under the frog.

After 3 hits he gives up with a sad face; the exit then follows the usual
"exactly N flies" rule, and 3-4 leads to the finale.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...game.enemy import AIR, Boss, Telegraph, register_enemy
from ...game.events import BOSS_TELL, Event
from ...game.grid import Cell, Spawn, manhattan, step
from ...game.tiles import SOLID
from . import config as sc

if TYPE_CHECKING:
    from ...game.world import World

Pos = tuple[float, float]


def bezier(p0: Pos, p1: Pos, p2: Pos, t: float) -> Pos:
    a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
    return (a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1])


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 2


@register_enemy("jesus")
class Jesus(Boss):
    layer = AIR
    name_key = "sky.boss"
    hit_text_key = "sky.sasat"

    def __init__(self) -> None:
        self.hp = self.max_hp
        self.state = "idle"             # idle | beams | multiply | halo | rebuild | hit | sad
        self.timer = sc.JESUS_FIRST
        self.attack_n = 0
        self.beam_cells: tuple[Cell, ...] = ()
        self.beam_on = False
        self.lines: list[tuple[str, int]] = []
        # halo boomerang
        self.halo_phase = "home"        # home | out | hover | back | bonk
        self.halo_t = 0.0
        self.halo_pos: Pos = (0.0, 0.0)
        self.halo_from: Pos = (0.0, 0.0)
        self.halo_ctrl: Pos = (0.0, 0.0)
        self.halo_to: Pos = (0.0, 0.0)
        self.halo_hover = sc.JESUS_HALO_HOVER
        # cloud rebuild
        self.vanish: tuple[Cell, ...] = ()
        self.appear: tuple[Cell, ...] = ()
        self.multiplied = 0
        self.defeat_t = 0.0

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Jesus":
        j = cls()
        j.hp = int(spawn.param("hp", cls.max_hp))
        lv = world.level
        cs = lv.cell or 64
        # his head, in cell units above the field (the art draws him around it)
        j.pos = ((lv.width - 1) / 2, -(max(lv.top_reserve, 120) * 0.82) / cs - 0.5)
        j.halo_pos = j.head_halo()
        return j

    # ------------------------------------------------------------ geometry
    def head_halo(self) -> Pos:
        return (self.pos[0], self.pos[1] - 0.62)

    def hurts(self, world: "World", frog_pos: Pos) -> bool:
        return False

    def occupied(self) -> set[Cell]:
        return set(self.beam_cells) if self.state == "beams" else set(self.vanish)

    @property
    def halo_flying(self) -> bool:
        return self.halo_phase in ("out", "hover", "back")

    # ------------------------------------------------------------ behaviour
    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        if self.defeated:
            self.state = "sad"
            self.defeat_t += dt
            self.beam_on = False
            self.beam_cells = self.vanish = self.appear = ()
            if self.halo_phase != "home":
                self._update_halo(dt, world)
            return
        self._update_halo(dt, world)
        sp = world.enemy_speed
        self.timer -= dt * sp
        if self.state == "idle":
            if self.timer <= 0:
                self._start_attack(world)
        elif self.state == "beams":
            if not self.beam_on and self.timer <= 0:
                self.beam_on, self.timer = True, sc.JESUS_BEAM_TIME
                world.emit(Event("sky.beam", value=list(self.lines)))
            if self.beam_on:
                frog = world.frog_target
                if frog is not None and frog in self.beam_cells:
                    world.hurt_frog(self)
                if self.timer <= 0:
                    self.beam_on = False
                    self.beam_cells = ()
                    self._rest(world)
        elif self.state == "multiply":
            if self.timer <= 0:
                self._multiply(world)
                self._rest(world)
        elif self.state == "halo":
            if self.halo_phase == "home":
                self._rest(world)
        elif self.state == "rebuild":
            if self.timer <= 0:
                self._rebuild(world)
                self._rest(world)
        elif self.state == "hit":
            if self.timer <= 0:
                self._rest(world)

    def _rest(self, world: "World") -> None:
        span = sc.JESUS_IDLE_ENRAGED if self.enraged(world) else sc.JESUS_IDLE
        self.state, self.timer = "idle", world.rng.uniform(*span)

    def _start_attack(self, world: "World") -> None:
        self.attack_n += 1
        if self.attack_n % 2 == 1:
            kind = "halo"
        else:
            options = ["beams", "beams", "rebuild"]
            if world.flies.counted_alive() < sc.JESUS_MULTIPLY_CAP and not world.full:
                options.append("multiply")
            kind = world.rng.choice(options)
        world.emit(Event(BOSS_TELL, pos=self.pos, value=(self.kind, kind)))
        getattr(self, "_begin_" + kind)(world)

    # ------------------------------------------------------------ beams
    def _begin_beams(self, world: "World") -> None:
        lv, rng = world.level, world.rng
        frog = world.frog_target or lv.frog_start
        if self.enraged(world):
            self.lines = [("row", frog[1]), ("col", frog[0])]
        else:
            axis = rng.choice(("row", "col"))
            if rng.random() < 0.75:
                idx = frog[1] if axis == "row" else frog[0]
            else:
                idx = rng.randrange(lv.height if axis == "row" else lv.width)
            self.lines = [(axis, idx)]
        cells: list[Cell] = []
        for axis, idx in self.lines:
            cells += [(x, idx) for x in range(lv.width)] if axis == "row" \
                else [(idx, y) for y in range(lv.height)]
        self.beam_cells = tuple(dict.fromkeys(cells))
        self.state, self.timer, self.beam_on = "beams", sc.JESUS_BEAM_WARN, False

    # ------------------------------------------------------------ multiply
    def _begin_multiply(self, world: "World") -> None:
        self.state, self.timer = "multiply", sc.JESUS_MULTIPLY_WARN

    def _multiply(self, world: "World") -> None:
        rng = world.rng
        frog = world.frog_target or world.level.frog_start
        cells = [c for c in world.tiles.standable_cells() if manhattan(c, frog) > 1]
        rng.shuffle(cells)
        n = min(len(cells), rng.randint(*sc.JESUS_MULTIPLY))
        for c in sorted(cells[:n]):
            world.flies.spawn_at("fly", c, rest=rng.uniform(1.0, 2.5))
        self.multiplied += n
        world.emit(Event("sky.multiply", pos=self.pos, value=n))

    # ------------------------------------------------------------ halo boomerang
    def _begin_halo(self, world: "World") -> None:
        lv, rng = world.level, world.rng
        frog = world.frog_target or lv.frog_start
        options = [step(frog, d, 2) for d in range(4)]
        options = [c for c in options if lv.in_bounds(c)] or [frog]
        # prefer spots the frog can face from where it stands
        target = rng.choice(options)
        self.halo_from = self.head_halo()
        self.halo_to = (float(target[0]), float(target[1]))
        side = 1 if self.halo_to[0] >= self.pos[0] else -1
        self.halo_ctrl = (self.halo_to[0] + side * 5.0, min(self.halo_from[1], self.halo_to[1]) + 0.5)
        self.halo_phase, self.halo_t = "out", 0.0
        self.halo_hover = sc.JESUS_HALO_HOVER_ENRAGED if self.enraged(world) else sc.JESUS_HALO_HOVER
        flight = sc.JESUS_HALO_OUT + self.halo_hover + sc.JESUS_HALO_BACK
        self.open_window(flight)            # the pill glows while the halo is out
        self.state, self.timer = "halo", flight + 1.0
        world.emit(Event("sky.halo_throw", pos=self.halo_from))

    def _update_halo(self, dt: float, world: "World") -> None:
        ph = self.halo_phase
        if ph == "home":
            self.halo_pos = self.head_halo()
            return
        self.halo_t += dt
        if ph == "out":
            k = self.halo_t / sc.JESUS_HALO_OUT
            self.halo_pos = bezier(self.halo_from, self.halo_ctrl, self.halo_to, ease(k))
            if k >= 1:
                self.halo_phase, self.halo_t = "hover", 0.0
        elif ph == "hover":
            a = self.halo_t * 5
            self.halo_pos = (self.halo_to[0] + 0.08 * math.cos(a), self.halo_to[1] + 0.06 * math.sin(a))
            if self.halo_t >= self.halo_hover:
                self.halo_phase, self.halo_t = "back", 0.0
                self.halo_from, self.halo_to = self.halo_to, self.head_halo()
                self.halo_ctrl = (self.halo_ctrl[0] * 0.5 + self.pos[0] * 0.5 - 3.0 *
                                  (1 if self.halo_ctrl[0] < self.pos[0] else -1),
                                  self.halo_ctrl[1])
        elif ph == "back":
            k = self.halo_t / sc.JESUS_HALO_BACK
            self.halo_pos = bezier(self.halo_from, self.halo_ctrl, self.halo_to, k * k)
            if k >= 1:
                self.halo_phase = "home"
        elif ph == "bonk":
            k = min(1.0, self.halo_t / sc.JESUS_HALO_BONK)
            head = self.head_halo()
            lift = math.sin(k * math.pi) * 1.5
            self.halo_pos = (self.halo_from[0] + (head[0] - self.halo_from[0]) * k,
                             self.halo_from[1] + (head[1] - self.halo_from[1]) * k - lift)
            if k >= 1:
                self.halo_phase = "home"
                self.open_window(0.5)
                if self.take_hit(world):
                    world.emit(Event("sky.bonk", pos=self.pos))
                    if not self.defeated:
                        self.state, self.timer = "hit", sc.JESUS_HIT_TIME
                        self.beam_on, self.beam_cells = False, ()

    def tongue_hit(self, world: "World", line: list[Cell]) -> int | None:
        if self.defeated or self.halo_phase not in ("out", "hover", "back"):
            return None
        for i, c in enumerate(line):
            if math.dist(c, self.halo_pos) <= sc.JESUS_HALO_CATCH:
                return i
        return None

    def on_tongued(self, world: "World") -> None:
        if not self.halo_flying:
            return
        self.halo_phase, self.halo_t = "bonk", 0.0
        self.halo_from = self.halo_pos
        self.open_window(sc.JESUS_HALO_BONK + 1.0)
        world.emit(Event("sky.halo_caught", pos=self.halo_pos))

    # ------------------------------------------------------------ rebuild
    def _begin_rebuild(self, world: "World") -> None:
        rng, tiles = world.rng, world.tiles
        frog = world.frog_target or world.level.frog_start
        near = {frog} | {step(frog, d) for d in range(4)}
        keep = near | ({world.exit_cell} if world.exit_cell else set())
        solid = [c for c, t in tiles.items()
                 if t.standable and t.unstable is None and c[1] not in tiles.rows and c not in keep]
        holes = [c for c, t in tiles.items()
                 if t.kind != SOLID and t.kind != "obstacle" and c[1] not in tiles.rows]
        n = rng.randint(*sc.JESUS_REBUILD)
        rng.shuffle(solid)
        rng.shuffle(holes)
        self.vanish = tuple(sorted(solid[:n]))
        self.appear = tuple(sorted(holes[:n]))
        self.state, self.timer = "rebuild", sc.JESUS_REBUILD_WARN
        world.emit(Event("sky.rebuild_warn", value=(self.vanish, self.appear)))

    def _rebuild(self, world: "World") -> None:
        for c in self.appear:
            world.tiles.set_kind(c, SOLID)
            world.emit(Event("sky.cloud_new", cell=c))
        for c in self.vanish:
            world.make_hole(c, sc.JESUS_REBUILD_HOLE)      # telegraphed; falls if still there
        self.vanish = self.appear = ()

    # ------------------------------------------------------------ warnings
    def telegraphs(self) -> list[Telegraph]:
        if self.state == "beams" and not self.beam_on:
            p = 1.0 - self.timer / sc.JESUS_BEAM_WARN
            return [Telegraph("line", self._line(ax, i), p, 1 if ax == "row" else 2)
                    for ax, i in self.lines]
        if self.state == "rebuild":
            p = 1.0 - self.timer / sc.JESUS_REBUILD_WARN
            return [Telegraph("zone", self.vanish, p)] if self.vanish else []
        return []

    def _line(self, axis: str, idx: int) -> tuple[Cell, ...]:
        return tuple(c for c in self.beam_cells if (c[1] == idx if axis == "row" else c[0] == idx))

    def center(self) -> Pos:
        """Popups («SASAT!») appear beside his head, below the HUD pill."""
        return (self.pos[0] + 2.6, self.pos[1] + 1.3)

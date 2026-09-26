"""Sky-world predators: swallow, hawk, crow (no pygame). The boss is in ``jesus.py``.

* ``swallow`` — red edge arrow for 1 s (``Telegraph("arrow")`` + ``"line"``),
  then flies fast through the whole row / column; hurts on contact.
* ``hawk`` — soars over clouds and abyss alike, slower than the frog; when
  within 2 cells it winds up (0.4 s, ``"zone"`` telegraph) and dashes 2 cells.
* ``crow`` — flies to flies and eats them (fewer flies around), caws
  (``world.haste`` — other predators 3 s faster), pecks the frog next to it.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...game.enemy import AIR, GROUND, Enemy, Telegraph, register_enemy
from ...game.events import Event
from ...game.grid import DIRS, Cell, Spawn, manhattan
from . import config as sc

if TYPE_CHECKING:
    from ...game.world import World

Pos = tuple[float, float]


def _far_cell(world: "World", avoid: Cell, near: Cell | None = None) -> Cell:
    """A standable cell far from ``avoid`` (spawn without a map position)."""
    cells = sorted(world.tiles.standable_cells()) or [avoid]
    return max(cells, key=lambda c: (manhattan(c, avoid) - (manhattan(c, near) if near else 0), c))


# ---------------------------------------------------------------- swallow
@register_enemy("swallow")
class Swallow(Enemy):
    layer = AIR
    contact_radius = 0.55

    def __init__(self) -> None:
        self.state = "wait"
        self.timer = 0.0
        self.axis = "row"               # "row" | "col"
        self.index = 0
        self.direction = 1              # grid direction of flight (0 up .. 3 left)
        self.start: Pos = (0.0, 0.0)
        self.end: Pos = (0.0, 0.0)
        self.passes = 0

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Swallow":
        s = cls()
        s.timer = world.rng.uniform(*sc.SWALLOW_FIRST) + spawn.param("delay", 0.0)
        s.pos = (-9.0, -9.0)
        return s

    # ------------------------------------------------------------ geometry
    def lane_cells(self, world: "World") -> list[Cell]:
        lv = world.level
        if self.axis == "row":
            return [(x, self.index) for x in range(lv.width)]
        return [(self.index, y) for y in range(lv.height)]

    def edge_cell(self) -> Cell:
        """The cell just outside the field where the arrow is shown."""
        return (round(self.start[0] + DIRS[self.direction][0] * (sc.SWALLOW_MARGIN - 1)),
                round(self.start[1] + DIRS[self.direction][1] * (sc.SWALLOW_MARGIN - 1)))

    def _pick_lane(self, world: "World") -> None:
        lv, rng = world.level, world.rng
        frog = world.frog_target
        self.axis = rng.choice(("row", "col"))
        size = lv.height if self.axis == "row" else lv.width
        if frog is not None and rng.random() < sc.SWALLOW_AIM:
            self.index = frog[1] if self.axis == "row" else frog[0]
        else:
            self.index = rng.randrange(size)
        m = sc.SWALLOW_MARGIN
        forward = rng.random() < 0.5
        if self.axis == "row":
            self.direction = 1 if forward else 3
            a, b = (-m, float(self.index)), (lv.width - 1 + m, float(self.index))
        else:
            self.direction = 2 if forward else 0
            a, b = (float(self.index), -m), (float(self.index), lv.height - 1 + m)
        self.start, self.end = (a, b) if forward else (b, a)
        self._lane = self.lane_cells(world)

    # ------------------------------------------------------------ behaviour
    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        sp = world.enemy_speed
        if self.state == "wait":
            self.timer -= dt * sp
            if self.timer <= 0:
                self._pick_lane(world)
                self.state, self.timer = "warn", sc.SWALLOW_WARN
                self.pos = self.start
                world.emit(Event("sky.swallow_warn", cell=self.edge_cell(), value=self.direction))
        elif self.state == "warn":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "fly"
                world.emit(Event("sky.swallow_go", cell=self.edge_cell(), value=self.direction))
        elif self.state == "fly":
            dx, dy = DIRS[self.direction]
            step = sc.SWALLOW_SPEED * sp * dt
            self.pos = (self.pos[0] + dx * step, self.pos[1] + dy * step)
            done = (self.pos[0] - self.end[0]) * dx + (self.pos[1] - self.end[1]) * dy >= 0
            if done:
                self.passes += 1
                self.state, self.timer = "wait", world.rng.uniform(*sc.SWALLOW_PAUSE)
                self.pos = (-9.0, -9.0)

    @property
    def flying(self) -> bool:
        return self.state == "fly"

    @property
    def warn_progress(self) -> float:
        return 1.0 - self.timer / sc.SWALLOW_WARN if self.state == "warn" else 0.0

    def hurts(self, world: "World", frog_pos: Pos) -> bool:
        return self.state == "fly" and super().hurts(world, frog_pos)

    def occupied(self) -> set[Cell]:
        if self.state == "wait":
            return set()
        return set(getattr(self, "_lane", ()))  # keep the exit / respawn out of its lane

    def telegraphs(self) -> list[Telegraph]:
        if self.state != "warn":
            return []
        p = self.warn_progress
        return [Telegraph("line", tuple(getattr(self, "_lane", ())), p, self.direction),
                Telegraph("arrow", (self.edge_cell(),), p, self.direction)]


# ---------------------------------------------------------------- hawk
@register_enemy("hawk")
class Hawk(Enemy):
    layer = AIR
    contact_radius = sc.HAWK_RADIUS

    def __init__(self) -> None:
        self.state = "soar"
        self.timer = 0.0
        self.heading = -math.pi / 2     # radians, 0 = right, pi/2 = down (screen)
        self.dash_from: Pos = (0.0, 0.0)
        self.dash_to: Pos = (0.0, 0.0)
        self.speed = sc.HAWK_SPEED
        self.orbit = 0.0
        self.last_target: Pos = (0.0, 0.0)
        self.dashes = 0

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Hawk":
        h = cls()
        cell = spawn.cell or _far_cell(world, world.level.frog_start)
        h.pos = (float(cell[0]), float(cell[1]))
        h.last_target = h.pos
        h.speed = spawn.param("speed", sc.HAWK_SPEED)
        return h

    def _clamp(self, world: "World", p: Pos) -> Pos:
        lv = world.level
        return (min(lv.width - 0.5, max(-0.5, p[0])), min(lv.height - 0.5, max(-0.5, p[1])))

    def dash_cells(self) -> tuple[Cell, ...]:
        out: list[Cell] = []
        for k in (0.5, 1.0):
            x = self.dash_from[0] + (self.dash_to[0] - self.dash_from[0]) * k
            y = self.dash_from[1] + (self.dash_to[1] - self.dash_from[1]) * k
            c = (math.floor(x + 0.5), math.floor(y + 0.5))
            if c not in out:
                out.append(c)
        return tuple(out)

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        sp = world.enemy_speed
        frog = world.frog_target
        if self.state == "soar":
            if frog is not None:
                target = world.frog.pos()
                self.last_target = target
            else:
                self.orbit += dt
                target = (self.last_target[0] + 2.5 * math.cos(self.orbit),
                          self.last_target[1] + 1.5 * math.sin(self.orbit))
            dx, dy = target[0] - self.pos[0], target[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if frog is not None and dist <= sc.HAWK_TRIGGER and not world.frog.airborne:
                ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else DIRS[2]
                self.dash_from = self.pos
                self.dash_to = self._clamp(world, (self.pos[0] + ux * sc.HAWK_DASH,
                                                   self.pos[1] + uy * sc.HAWK_DASH))
                self.heading = math.atan2(uy, ux)
                self.state, self.timer = "windup", sc.HAWK_WINDUP
                world.emit(Event("sky.hawk_windup", pos=self.pos))
                return
            if dist > 1e-6:
                ux, uy = dx / dist, dy / dist
                vx, vy = ux - uy * sc.HAWK_SPIRAL, uy + ux * sc.HAWK_SPIRAL
                n = math.hypot(vx, vy)
                step = self.speed * sp * dt
                self.pos = self._clamp(world, (self.pos[0] + vx / n * step, self.pos[1] + vy / n * step))
                self._turn(math.atan2(vy, vx), dt)
        elif self.state == "windup":
            self.timer -= dt * sp
            if self.timer <= 0:
                self.state, self.timer = "dash", sc.HAWK_DASH_TIME
                self.dashes += 1
        elif self.state == "dash":
            self.timer -= dt * sp
            k = 1.0 - max(0.0, self.timer) / sc.HAWK_DASH_TIME
            self.pos = (self.dash_from[0] + (self.dash_to[0] - self.dash_from[0]) * k,
                        self.dash_from[1] + (self.dash_to[1] - self.dash_from[1]) * k)
            if self.timer <= 0:
                self.state, self.timer = "recover", sc.HAWK_RECOVER
        elif self.state == "recover":
            self.timer -= dt
            drift = 0.6 * dt
            self.pos = self._clamp(world, (self.pos[0] + math.cos(self.heading) * drift,
                                           self.pos[1] + math.sin(self.heading) * drift))
            self._turn(self.heading + 1.2 * dt, dt)
            if self.timer <= 0:
                self.state = "soar"

    def _turn(self, want: float, dt: float) -> None:
        d = (want - self.heading + math.pi) % (2 * math.pi) - math.pi
        self.heading += d * min(1.0, dt * 6)

    def hurts(self, world: "World", frog_pos: Pos) -> bool:
        return self.state != "recover" and super().hurts(world, frog_pos)

    def on_frog_hit(self, world: "World") -> None:
        self.state, self.timer = "recover", sc.HAWK_RECOVER

    def on_frog_respawn(self, world: "World", cell: Cell) -> None:
        self.state, self.timer = "recover", sc.HAWK_RECOVER

    def telegraphs(self) -> list[Telegraph]:
        if self.state != "windup":
            return []
        return [Telegraph("zone", self.dash_cells(), 1.0 - self.timer / sc.HAWK_WINDUP)]


# ---------------------------------------------------------------- crow
@register_enemy("crow")
class Crow(Enemy):
    layer = GROUND
    contact_radius = 0.0

    def __init__(self) -> None:
        self.state = "sit"
        self.timer = 1.0
        self.caw_timer = 7.0
        self.peck_cd = 1.0
        self.peck_cell: Cell | None = None
        self.target_fly: int | None = None
        self.dest: Pos | None = None
        self.heading = math.pi / 2
        self.eaten = 0
        self.caws = 0

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Crow":
        c = cls()
        cell = spawn.cell or _far_cell(world, world.level.frog_start)
        c.pos = (float(cell[0]), float(cell[1]))
        c.timer = world.rng.uniform(*sc.CROW_REST)
        c.caw_timer = world.rng.uniform(*sc.CROW_CAW_EVERY)
        return c

    @property
    def cell(self) -> Cell:
        return (math.floor(self.pos[0] + 0.5), math.floor(self.pos[1] + 0.5))

    def _pick_fly(self, world: "World"):
        best, best_d = None, sc.CROW_HUNT_RANGE
        for fly in world.flies.flies:
            if fly.caught or not fly.counted or fly.state == "leaving" \
                    or not world.level.in_bounds(fly.cell):
                continue
            d = math.dist(fly.pos, self.pos)
            if d < best_d:
                best, best_d = fly, d
        return best

    def _land_cell(self, world: "World") -> Pos:
        cells = world.tiles.standable_cells()
        frog = world.frog_target
        cells = [c for c in cells if frog is None or c != frog] or cells
        if not cells:
            return self.pos
        c = min(cells, key=lambda c: (math.dist(c, self.pos), c))
        return (float(c[0]), float(c[1]))

    def _fly_towards(self, target: Pos, dt: float) -> bool:
        dx, dy = target[0] - self.pos[0], target[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        step = sc.CROW_SPEED * dt
        if dist <= step or dist < 1e-6:
            self.pos = target
            return True
        self.heading = math.atan2(dy, dx)
        self.pos = (self.pos[0] + dx / dist * step, self.pos[1] + dy / dist * step)
        return False

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.peck_cd = max(0.0, self.peck_cd - dt)
        if self.state != "fly":
            self.caw_timer -= dt
        frog = world.frog_target
        if self.state == "sit":
            self.layer = GROUND
            if not world.tiles.standable(self.cell):          # cloud melted away
                self._take_off(world, None)
                return
            if frog is not None and manhattan(frog, self.cell) == 1 and self.peck_cd <= 0:
                self.state, self.timer, self.peck_cell = "peck", sc.CROW_PECK_WINDUP, frog
                self.heading = math.atan2(frog[1] - self.pos[1], frog[0] - self.pos[0])
                return
            if self.caw_timer <= 0:
                self.state, self.timer = "caw", sc.CROW_CAW_TIME
                self.caw_timer = world.rng.uniform(*sc.CROW_CAW_EVERY)
                self.caws += 1
                world.haste(*sc.CROW_HASTE)
                world.emit(Event("sky.caw", pos=self.pos))
                return
            self.timer -= dt
            if self.timer <= 0:
                fly = self._pick_fly(world)
                if fly is not None:
                    self._take_off(world, fly.id)
                else:
                    self.timer = world.rng.uniform(*sc.CROW_REST)
        elif self.state == "fly":
            self.layer = AIR
            fly = world.flies.get(self.target_fly) if self.target_fly is not None else None
            if self.target_fly is not None and (fly is None or fly.caught):
                self.target_fly, self.dest = None, self._land_cell(world)
            if fly is not None and not fly.caught:
                if self._fly_towards(fly.pos, dt) or math.dist(fly.pos, self.pos) < 0.3:
                    world.flies.remove(fly)
                    self.eaten += 1
                    world.emit(Event("sky.crow_eat", pos=fly.pos, value=fly.kind))
                    self.target_fly = None
                    self.state, self.timer = "eat", sc.CROW_EAT_TIME
            elif self.dest is not None:
                if self._fly_towards(self.dest, dt):
                    if world.tiles.standable(self.cell):
                        self.state, self.timer = "sit", world.rng.uniform(*sc.CROW_REST)
                        self.layer = GROUND
                    else:
                        self.dest = self._land_cell(world)
        elif self.state == "eat":
            self.timer -= dt
            if self.timer <= 0:
                if world.tiles.standable(self.cell):
                    self.state, self.timer = "sit", world.rng.uniform(*sc.CROW_REST)
                else:
                    self._take_off(world, None)
        elif self.state == "caw":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = "sit", world.rng.uniform(*sc.CROW_REST) * 0.5
        elif self.state == "peck":
            self.timer -= dt
            if self.timer <= 0:
                if self.peck_cell is not None and world.frog_target == self.peck_cell:
                    world.hurt_frog(self)
                world.emit(Event("sky.peck", cell=self.peck_cell, pos=self.pos))
                self.peck_cd = sc.CROW_PECK_COOLDOWN
                self.state, self.timer = "sit", world.rng.uniform(*sc.CROW_REST)

    def _take_off(self, world: "World", fly_id: int | None) -> None:
        self.state, self.target_fly = "fly", fly_id
        self.dest = None if fly_id is not None else self._land_cell(world)
        self.layer = AIR

    def hurts(self, world: "World", frog_pos: Pos) -> bool:
        return False

    def occupied(self) -> set[Cell]:
        return {self.cell}

    def telegraphs(self) -> list[Telegraph]:
        if self.state == "peck" and self.peck_cell is not None:
            return [Telegraph("zone", (self.peck_cell,), 1.0 - self.timer / sc.CROW_PECK_WINDUP)]
        return []

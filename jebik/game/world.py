"""World: one running level. Pure logic, driven by ``update(dt)`` + requests.

The scene feeds player intents via :meth:`World.request_move` and
:meth:`World.request_tongue`; the world emits :class:`~jebik.game.events.Event`
objects the renderer and audio consume via :meth:`World.drain_events`.
"""
from __future__ import annotations

import random

from .. import config
from . import events as ev
from . import frog as fs
from .events import Event
from .flies import COUNTED_KINDS, Fly, FlyManager
from .frog import Command, Frog, Tongue
from .grid import Cell, DIRS, Level, bfs_distances, manhattan, step
from .rules import Result, Rules, compute_result, rules_for
from .snake import Snake

PLAYING = "playing"
WON = "won"
LOST = "lost"


class World:
    def __init__(self, level: Level, rules: Rules | None = None,
                 seed: int | None = None, auto_spawn: bool = True,
                 spawn_enemies: bool = True):
        self.level = level
        self.rules = rules or rules_for("ezzz")
        self.rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
        self.frog = Frog(level.frog_start, facing=0)
        self.flies = FlyManager(level, self.rng, auto_spawn=auto_spawn)
        self.enemies: list[Snake] = []
        if spawn_enemies:
            for s in level.snake_starts:
                self.enemies.append(Snake.spawn(level, s, self.rng))
        if auto_spawn:
            self.flies.populate(avoid=level.frog_start)
            self.flies.drain_spawned()
        self.hearts = self.rules.hearts
        self.eaten = 0
        self.needed = level.flies_needed
        self.full = False
        self.exit_cell: Cell | None = None
        self.time = 0.0
        self.damaged = False
        self.state = PLAYING
        self.end_timer = 0.0
        self.result: Result | None = None
        self.overeats = 0
        self.events: list[Event] = []

    # ------------------------------------------------------------ intents
    def request_move(self, direction: int, super_jump: bool = False) -> None:
        if self.state != PLAYING:
            return
        f = self.frog
        if f.can_act:
            self._start_move(direction, super_jump)
        elif f.state in (fs.HOP, fs.SUPER, fs.TONGUE):
            f.buffered = Command("move", direction, super_jump)

    def request_tongue(self, direction: int | None = None) -> None:
        if self.state != PLAYING:
            return
        f = self.frog
        if f.can_act:
            if f.tongue_cd <= 0:
                self._fire_tongue(direction)
            elif direction is not None:
                f.facing = direction
        elif f.state in (fs.HOP, fs.SUPER):
            f.buffered = Command("tongue", direction)

    def drain_events(self) -> list[Event]:
        out, self.events = self.events, []
        return out

    @property
    def show_result(self) -> bool:
        return self.state != PLAYING and self.end_timer <= 0

    # ------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        f = self.frog
        if self.state == PLAYING:
            self.time += dt
        else:
            self.end_timer -= dt
        f.super_cd = max(0.0, f.super_cd - dt)
        f.tongue_cd = max(0.0, f.tongue_cd - dt)
        f.invuln = max(0.0, f.invuln - dt)
        f.firefly = max(0.0, f.firefly - dt)
        f.idle_time = f.idle_time + dt if f.state == fs.IDLE else 0.0

        if f.state in (fs.HOP, fs.SUPER):
            f.hop_t += dt / f.hop_time
            if f.hop_t >= 1.0:
                f.hop_t = 1.0
                self._land()
        elif f.state == fs.TONGUE:
            self._update_tongue(dt)
        elif f.state in (fs.SPLASH, fs.HIT):
            f.state_timer -= dt
            if f.state_timer <= 0:
                if f.state == fs.SPLASH:
                    self._respawn()
                else:
                    f.state = fs.IDLE

        frog_target = f.ground_cell() if f.state not in (fs.SPLASH, fs.DEAD) else None
        self.flies.update(dt, f.ground_cell())
        for fly in self.flies.drain_spawned():
            if fly.kind in ("gold", "firefly"):
                self.events.append(Event(ev.FLY_SPAWN, value=fly.kind))
        for enemy in self.enemies:
            enemy.update(dt, frog_target if self.state == PLAYING else None)
        if self.state == PLAYING:
            self._check_enemies()
        if self.state == PLAYING and f.can_act and f.buffered is not None:
            cmd, f.buffered = f.buffered, None
            if cmd.kind == "move":
                self._start_move(cmd.direction, cmd.super_jump)
            elif f.tongue_cd <= 0:
                self._fire_tongue(cmd.direction)

    # ------------------------------------------------------------ movement
    def _start_move(self, direction: int, super_jump: bool) -> bool:
        f = self.frog
        f.facing = direction
        if super_jump and f.super_cd > 0:
            self.events.append(Event(ev.SUPER_DENIED))
            return False
        target = step(f.cell, direction, 2 if super_jump else 1)
        if not self.level.in_bounds(target):
            self.events.append(Event(ev.BUMP, cell=f.cell, value=direction))
            return False
        f.hop_from, f.hop_to, f.hop_t = f.cell, target, 0.0
        if super_jump:
            f.state, f.hop_time = fs.SUPER, config.SUPERJUMP_TIME
            f.super_cd = config.SUPERJUMP_COOLDOWN
            self.events.append(Event(ev.SUPERJUMP, cell=target))
        else:
            f.state, f.hop_time = fs.HOP, config.HOP_TIME
            self.events.append(Event(ev.HOP, cell=target))
        return True

    def _land(self) -> None:
        f = self.frog
        f.cell = f.hop_to
        f.state = fs.IDLE
        if not self.level.is_pad(f.cell):
            f.state, f.state_timer, f.splash_cell = fs.SPLASH, config.SPLASH_TIME, f.cell
            f.buffered = None
            self.events.append(Event(ev.SPLASH, cell=f.cell))
            self._lose_heart()
            return
        f.last_safe = f.cell
        self.events.append(Event(ev.LAND, cell=f.cell, value=f.hop_time))
        for fly in self.flies.at_cell(f.cell):
            self._eat(fly)
            if self.state != PLAYING:
                return
        if self.exit_cell == f.cell and self.state == PLAYING:
            self._win()

    def _respawn(self) -> None:
        f = self.frog
        if self.hearts <= 0:
            self._lose()
            return
        f.cell = self._safe_respawn_cell(f.last_safe)
        f.hop_from = f.hop_to = f.last_safe = f.cell
        f.state = fs.IDLE
        f.invuln = config.INVULN_TIME
        f.splash_cell = None
        for e in self.enemies:          # no spawn camping: nearby snakes back off
            if manhattan(e.head, f.cell) <= config.SNAKE_SIGHT:
                e.start_retreat()
        self.events.append(Event(ev.RESPAWN, cell=f.cell))

    def _safe_respawn_cell(self, preferred: Cell) -> Cell:
        """Nearest pad (by hops) that is not next to an enemy."""
        lv = self.level
        danger = set()
        for e in self.enemies:
            danger |= e.occupied()

        def safe(c: Cell) -> bool:
            return all(manhattan(c, d) >= config.SNAKE_SAFE_RESPAWN_DIST for d in danger)

        start = preferred if lv.is_pad(preferred) else lv.frog_start
        dist = bfs_distances(start, lv.pad_neighbors)
        for cell in sorted(dist, key=lambda c: (dist[c], c)):
            if safe(cell):
                return cell
        pads = sorted(lv.pads, key=lambda c: (manhattan(c, start), c))
        for cell in pads:
            if safe(cell):
                return cell
        return lv.frog_start

    # ------------------------------------------------------------ tongue
    def _fire_tongue(self, direction: int | None) -> None:
        f = self.frog
        if direction is not None:
            f.facing = direction
        reach = f.tongue_range
        caught: Fly | None = None
        length = float(reach)
        for d in range(1, reach + 1):
            cell = step(f.cell, f.facing, d)
            if not self.level.in_bounds(cell):
                break
            here = self.flies.at_cell(cell)
            if here:
                dx, dy = DIRS[f.facing]
                caught = min(here, key=lambda fl: (fl.pos[0] - f.cell[0]) * dx
                             + (fl.pos[1] - f.cell[1]) * dy)
                along = (caught.pos[0] - f.cell[0]) * dx + (caught.pos[1] - f.cell[1]) * dy
                length = max(0.6, min(float(reach) + 0.4, along))
                break
        f.tongue = Tongue(direction=f.facing, max_len=length)
        if caught is not None:
            caught.caught = True
            f.tongue.fly_id = caught.id
            f.extra["grab"] = caught.pos
        f.state = fs.TONGUE
        f.tongue_cd = config.TONGUE_COOLDOWN
        self.events.append(Event(ev.TONGUE, cell=f.cell, value=f.facing))

    def _update_tongue(self, dt: float) -> None:
        f = self.frog
        t = f.tongue
        if t is None:
            f.state = fs.IDLE
            return
        fly = self.flies.get(t.fly_id)
        if t.phase == "out":
            t.length = min(t.max_len, t.length + config.TONGUE_EXTEND_SPEED * dt)
            if t.length >= t.max_len:
                t.phase, t.hold = "hold", config.TONGUE_HOLD
        elif t.phase == "hold":
            t.hold -= dt
            if t.hold <= 0:
                t.phase = "in"
        else:
            t.length = max(0.0, t.length - config.TONGUE_RETRACT_SPEED * dt)
        if fly is not None and t.phase != "out":
            # the fly rides the tip; its sideways offset from the tongue line
            # (where it was grabbed) shrinks to zero as the tongue retracts
            tip = t.tip(f.pos())
            gx, gy = f.extra.get("grab", fly.pos)
            k = t.length / t.max_len if t.max_len else 0.0
            dx, dy = DIRS[t.direction]
            lat = ((gx - f.cell[0]) * (1 - abs(dx)), (gy - f.cell[1]) * (1 - abs(dy)))
            fly.pos = (tip[0] + lat[0] * k, tip[1] + lat[1] * k)
        if t.phase == "in" and t.length <= 0:
            f.tongue = None
            f.state = fs.IDLE
            if fly is not None:
                self._eat(fly)

    def _release_tongue(self) -> None:
        f = self.frog
        if f.tongue is not None:
            fly = self.flies.get(f.tongue.fly_id)
            if fly is not None:
                fly.caught = False
                fly.state, fly.wait = "hover", 0.2
        f.tongue = None

    # ------------------------------------------------------------ eating
    def _eat(self, fly: Fly) -> None:
        pos = fly.pos
        self.flies.remove(fly)
        self.events.append(Event(ev.EAT, pos=pos, cell=fly.cell, value=(fly.kind, fly.value)))
        if fly.kind in COUNTED_KINDS:
            if self.full:
                self._overeat(pos)
                return
            new = self.eaten + fly.value
            if new > self.needed:
                self.eaten = self.needed
                self._overeat(pos)
                if self.state == PLAYING:
                    self._become_full()
                return
            self.eaten = new
            if self.eaten == self.needed:
                self._become_full()
        elif fly.kind == "gold":
            if self.hearts < self.rules.max_hearts:
                self.hearts += 1
                self.events.append(Event(ev.HEART_GAIN, pos=pos))
            else:
                self.events.append(Event(ev.HEART_FULL, pos=pos))
        elif fly.kind == "firefly":
            self.frog.firefly = config.FIREFLY_DURATION
            self.events.append(Event(ev.FIREFLY, pos=pos))

    def _overeat(self, pos: tuple[float, float]) -> None:
        self.overeats += 1
        self.events.append(Event(ev.OVEREAT, pos=pos))
        self.frog.invuln = max(self.frog.invuln, config.INVULN_TIME)
        self._lose_heart()
        if self.hearts <= 0 and self.frog.state not in (fs.SPLASH,):
            self._lose()

    def _become_full(self) -> None:
        if self.full:
            return
        self.full = True
        self.events.append(Event(ev.FULL))
        self.exit_cell = self.choose_exit_cell()
        self.events.append(Event(ev.EXIT_SPAWN, cell=self.exit_cell))

    def choose_exit_cell(self) -> Cell:
        """A pad far (in frog moves, incl. super jumps) from the frog."""
        lv = self.level
        f = self.frog
        origin = f.ground_cell() if lv.is_pad(f.ground_cell()) else f.last_safe

        def moves(c: Cell):
            for d in range(4):
                for k in (1, 2):
                    n = step(c, d, k)
                    if n in lv.pads:
                        yield n
        dist = bfs_distances(origin, moves)
        blocked = {origin}
        for e in self.enemies:
            blocked |= e.occupied()
        cands = [c for c in dist if c not in blocked]
        if not cands:
            cands = [c for c in lv.pads if c != origin] or [origin]
            return self.rng.choice(sorted(cands))
        cands.sort(key=lambda c: (-dist[c], -manhattan(c, origin), c))
        top = cands[:max(1, len(cands) // 5)]
        return self.rng.choice(top)

    # ------------------------------------------------------------ damage
    def _lose_heart(self) -> None:
        self.hearts = max(0, self.hearts - 1)
        self.damaged = True

    def _check_enemies(self) -> None:
        f = self.frog
        if f.invuln > 0 or f.airborne or f.state in (fs.SPLASH, fs.DEAD, fs.WON):
            return
        for e in self.enemies:
            if e.touches(f.pos()):
                self._hit(e)
                return

    def _hit(self, enemy: Snake) -> None:
        f = self.frog
        self._lose_heart()
        f.invuln = config.INVULN_TIME
        self.events.append(Event(ev.HIT, pos=f.pos()))
        enemy.start_retreat()
        if self.hearts <= 0:
            self._lose()
            return
        if f.state in (fs.IDLE, fs.TONGUE):
            self._release_tongue()
            f.state, f.state_timer = fs.HIT, config.HIT_STUN_TIME

    def _lose(self) -> None:
        if self.state != PLAYING:
            return
        self._release_tongue()
        self.frog.state = fs.DEAD
        self.frog.buffered = None
        self.state = LOST
        self.end_timer = config.LOSE_DELAY
        self.events.append(Event(ev.LOSE))

    def _win(self) -> None:
        self.frog.state = fs.WON
        self.frog.buffered = None
        self.state = WON
        self.end_timer = config.WIN_DELAY
        self.result = compute_result(self.level.id, self.rules.difficulty, self.time,
                                     self.eaten, self.hearts, not self.damaged,
                                     self.level.par_time)
        self.events.append(Event(ev.WIN))

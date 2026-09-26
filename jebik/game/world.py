"""World: one running level. Pure logic, driven by ``update(dt)`` + requests.

The scene feeds player intents via :meth:`World.request_move` and
:meth:`World.request_tongue`; the world emits :class:`~jebik.game.events.Event`
objects the renderer and audio consume via :meth:`World.drain_events`.

The behaviour is split into mixins: frog actions (``actions.py``), goals —
eating, exit, bosses, winning (``goals.py``) — and damage (``damage.py``).
The "public API for enemies" section below is what world packages use.
"""
from __future__ import annotations

import random

from . import events as ev
from . import frog as fs
from .actions import FrogActions
from .damage import Damage
from .enemy import Boss, Enemy, create_enemy
from .events import Event
from .flies import FlyManager
from .frog import Frog
from .goals import Goals
from .grid import Cell, Level
from .rules import LOST, PLAYING, WON, Result, Rules, rules_for
from .tiles import TileMap

__all__ = ["World", "PLAYING", "WON", "LOST"]


class World(FrogActions, Goals, Damage):
    def __init__(self, level: Level, rules: Rules | None = None,
                 seed: int | None = None, auto_spawn: bool = True,
                 spawn_enemies: bool = True):
        self.level = level
        self.rules = rules or rules_for("ezzz", level)
        self.rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
        self.tiles = TileMap.from_level(level)
        self.frog = Frog(level.frog_start, facing=0)
        self.flies = FlyManager(level, self.rng, auto_spawn=auto_spawn,
                                can_rest=self.tiles.standable)
        self.hearts = self.rules.hearts
        self.eaten = 0
        self.needed = level.flies_needed
        self.full = False
        self.exit_cell: Cell | None = None
        self.time = 0.0
        self.time_left: float | None = self.rules.time_limit
        self.damaged = False
        self.state = PLAYING
        self.lose_reason: str | None = None
        self.end_timer = 0.0
        self.result: Result | None = None
        self.overeats = 0
        self.events: list[Event] = []
        self.haste_timer = 0.0
        self.haste_factor = 1.0
        self.enemies: list[Enemy] = []
        if spawn_enemies:
            for spawn in level.spawns:
                self.enemies.append(create_enemy(self, spawn))
        if auto_spawn:
            self.flies.populate(avoid=level.frog_start)
            self.flies.drain_spawned()

    # ------------------------------------------------------------ intents
    def request_move(self, direction: int, super_jump: bool = False) -> None:
        if self.state != PLAYING:
            return
        f = self.frog
        if f.can_act:
            self._start_move(direction, super_jump)
        elif f.state in (fs.HOP, fs.SUPER, fs.TONGUE):
            f.buffered = fs.Command("move", direction, super_jump)

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
            f.buffered = fs.Command("tongue", direction)

    def drain_events(self) -> list[Event]:
        out, self.events = self.events, []
        return out

    @property
    def show_result(self) -> bool:
        return self.state != PLAYING and self.end_timer <= 0

    # ------------------------------------------------------------ public API for enemies
    def emit(self, event: Event) -> None:
        self.events.append(event)

    @property
    def frog_target(self) -> Cell | None:
        """The frog's (ground) cell for hunters; None when it can't be hunted."""
        f = self.frog
        if self.state != PLAYING or f.state in (fs.SPLASH, fs.DEAD):
            return None
        return f.ground_cell()

    @property
    def boss(self) -> Boss | None:
        return next((e for e in self.enemies if isinstance(e, Boss)), None)

    @property
    def enemy_speed(self) -> float:
        """Speed multiplier for all enemies (crow's caw makes them faster)."""
        return self.haste_factor if self.haste_timer > 0 else 1.0

    def haste(self, factor: float, seconds: float) -> None:
        self.haste_factor, self.haste_timer = factor, max(self.haste_timer, seconds)

    def can_stand(self, cell: Cell) -> bool:
        """A tile to stand on, or an enemy that carries the frog (whale back)."""
        return self.tiles.standable(cell) or any(e.supports(cell) for e in self.enemies)

    def blocked(self, cell: Cell) -> bool:
        return self.tiles.blocks(cell) or any(e.blocks(cell) for e in self.enemies)

    def make_hole(self, cell: Cell, seconds: float) -> None:
        """Temporary hole (mole, boar, whale); restores itself."""
        self.events.extend(self.tiles.make_hole(cell, seconds))
        self._ground_check()

    def hurt_frog(self, source: Enemy | None = None) -> bool:
        """Direct damage (peck, beam, jet). Respects invulnerability / jumps."""
        f = self.frog
        if self.state != PLAYING or f.invuln > 0 or f.airborne \
                or f.state in (fs.SPLASH, fs.DEAD, fs.WON):
            return False
        self._hit(source)
        return True

    def push_frog(self, direction: int, cells: int = 1) -> bool:
        """Shove the frog (wave / gulp / wind). May push it into a hole."""
        return self._push(direction, cells)

    # ------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        f = self.frog
        if self.state == PLAYING:
            self.time += dt
            if self.time_left is not None:
                self.time_left = max(0.0, self.time_left - dt)
                if self.time_left <= 0:
                    self._lose("timeout")
        else:
            self.end_timer -= dt
        self.haste_timer = max(0.0, self.haste_timer - dt)
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

        self._update_tiles(dt)
        self.flies.update(dt, f.ground_cell())
        for fly in self.flies.drain_spawned():
            if fly.kind in ("gold", "firefly"):
                self.events.append(Event(ev.FLY_SPAWN, value=fly.kind))
        for enemy in list(self.enemies):
            enemy.update(dt, self)
        if self.state == PLAYING:
            self._check_enemies()
        if self.state == PLAYING and f.can_act and f.buffered is not None:
            cmd, f.buffered = f.buffered, None
            if cmd.kind == "move":
                self._start_move(cmd.direction, cmd.super_jump)
            elif f.tongue_cd <= 0:
                self._fire_tongue(cmd.direction)

    def _update_tiles(self, dt: float) -> None:
        changes = self.tiles.update(dt)
        if not changes:
            return
        self.events.extend(changes)
        for e in changes:
            if e.kind == ev.ROW_SHIFT:
                self._carry(e.cell[1], e.value)
        self._ground_check()

    def _carry(self, row: int, direction: int) -> None:
        """A moving row shifted: carry the grounded frog and resting flies."""
        f = self.frog
        if f.grounded and f.cell[1] == row and self.state == PLAYING:
            f.cell = (f.cell[0] + direction, row)
            f.hop_from = f.hop_to = f.cell
            if not self.level.in_bounds(f.cell):
                self._fall(f.cell)
        self.flies.carry_row(row, direction, self.level.width)

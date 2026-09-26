"""Frog actions of the :class:`~jebik.game.world.World`: hops, landing, tongue."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .. import config
from . import events as ev
from . import frog as fs
from .events import Event
from .flies import Fly
from .frog import Tongue
from .grid import DIRS, step
from .rules import PLAYING

if TYPE_CHECKING:
    from .world import World


class FrogActions:
    """Mixin: movement and tongue. ``self`` is the World."""

    def _start_move(self: "World", direction: int, super_jump: bool) -> bool:
        f = self.frog
        f.facing = direction
        if super_jump and f.super_cd > 0:
            self.events.append(Event(ev.SUPER_DENIED))
            return False
        target = step(f.cell, direction, 2 if super_jump else 1)
        if not self.level.in_bounds(target) or self.blocked(target):
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

    def _push(self: "World", direction: int, cells: int) -> bool:
        f = self.frog
        if self.state != PLAYING or not f.grounded:
            return False
        target = f.cell
        for _ in range(cells):
            nxt = step(target, direction)
            if self.blocked(nxt):
                break
            target = nxt
        if target == f.cell:
            return False
        self._release_tongue()
        f.hop_from, f.hop_to, f.hop_t = f.cell, target, 0.0
        f.state, f.hop_time = fs.HOP, config.HOP_TIME * 1.4
        self.events.append(Event(ev.PUSHED, cell=target, value=direction))
        return True

    def _land(self: "World") -> None:
        f = self.frog
        f.cell = f.hop_to
        f.state = fs.IDLE
        if not self.level.in_bounds(f.cell) or not self.can_stand(f.cell):
            self._fall(f.cell)
            return
        f.last_safe = f.cell
        self.events.append(Event(ev.LAND, cell=f.cell, value=f.hop_time))
        self.events.extend(self.tiles.on_land(f.cell))
        for e in self.enemies:
            e.on_frog_land(self, f.cell)
        if self.exit_cell == f.cell and self.state == PLAYING:
            self._win()                  # the exit first: a fly resting on it is no overeat
            return
        for fly in self.flies.at_cell(f.cell):
            self._eat(fly)
            if self.state != PLAYING:
                return

    # ------------------------------------------------------------ tongue
    def _fire_tongue(self: "World", direction: int | None) -> None:
        f = self.frog
        if direction is not None:
            f.facing = direction
        reach = f.tongue_range
        line = [step(f.cell, f.facing, d) for d in range(1, reach + 1)]
        line = line[:next((i for i, c in enumerate(line) if not self.level.in_bounds(c)), len(line))]
        caught: Fly | None = None
        length = float(reach)
        fly_at = None
        for i, cell in enumerate(line):
            here = self.flies.at_cell(cell)
            if here:
                dx, dy = DIRS[f.facing]
                caught = min(here, key=lambda fl: (fl.pos[0] - f.cell[0]) * dx
                             + (fl.pos[1] - f.cell[1]) * dy)
                along = (caught.pos[0] - f.cell[0]) * dx + (caught.pos[1] - f.cell[1]) * dy
                length = max(0.6, min(float(reach) + 0.4, along))
                fly_at = i
                break
        hit_enemy, hit_at = None, None
        for e in self.enemies:
            idx = e.tongue_hit(self, line)
            if idx is not None and (hit_at is None or idx < hit_at):
                hit_enemy, hit_at = e, idx
        f.tongue = Tongue(direction=f.facing, max_len=length)
        if hit_enemy is not None and (fly_at is None or hit_at < fly_at):
            f.tongue.max_len = hit_at + 1.0
            f.tongue.enemy = hit_enemy
        elif caught is not None:
            caught.caught = True
            f.tongue.fly_id = caught.id
            f.extra["grab"] = caught.pos
        f.state = fs.TONGUE
        f.tongue_cd = config.TONGUE_COOLDOWN
        self.events.append(Event(ev.TONGUE, cell=f.cell, value=f.facing))

    def _update_tongue(self: "World", dt: float) -> None:
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
                if t.enemy is not None:
                    enemy, t.enemy = t.enemy, None
                    enemy.on_tongued(self)
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

    def _release_tongue(self: "World") -> None:
        f = self.frog
        if f.tongue is not None:
            fly = self.flies.get(f.tongue.fly_id)
            if fly is not None:
                fly.caught = False
                fly.state, fly.wait = "hover", 0.2
        f.tongue = None

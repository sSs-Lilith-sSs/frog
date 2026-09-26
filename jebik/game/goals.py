"""Goals of the :class:`~jebik.game.world.World`: eating, exit, bosses, win.

Exit rule: the exit appears when **exactly** ``needed`` flies are eaten and,
on a boss level, the boss is defeated (in either order).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .. import config
from . import events as ev
from . import frog as fs
from .enemy import Boss
from .events import Event
from .flies import COUNTED_KINDS, Fly
from .grid import Cell, bfs_distances, manhattan, step
from .rules import PLAYING, WON, compute_result

if TYPE_CHECKING:
    from .world import World


class Goals:
    """Mixin: flies, exit, boss bookkeeping and winning. ``self`` is the World."""

    # ------------------------------------------------------------ eating
    def _eat(self: "World", fly: Fly) -> None:
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
            if self.time_left is not None:
                self.time_left += self.rules.gold_time
                self.events.append(Event(ev.TIME_BONUS, pos=pos, value=self.rules.gold_time))
            elif self.hearts < self.rules.max_hearts:
                self.hearts += 1
                self.events.append(Event(ev.HEART_GAIN, pos=pos))
            else:
                self.events.append(Event(ev.HEART_FULL, pos=pos))
        elif fly.kind == "firefly":
            self.frog.firefly = config.FIREFLY_DURATION
            self.events.append(Event(ev.FIREFLY, pos=pos))

    def _overeat(self: "World", pos: tuple[float, float]) -> None:
        self.overeats += 1
        self.events.append(Event(ev.OVEREAT, pos=pos))
        self.frog.invuln = max(self.frog.invuln, config.INVULN_TIME)
        self._lose_heart("overeat")
        if self.hearts <= 0 and self.frog.state != fs.SPLASH:
            self._lose("overeat" if self.rules.one_hit else "hearts")

    def _become_full(self: "World") -> None:
        if self.full:
            return
        self.full = True
        self.events.append(Event(ev.FULL))
        self._maybe_open_exit()

    # ------------------------------------------------------------ exit
    @property
    def exit_ready(self: "World") -> bool:
        boss = self.boss
        return self.full and (boss is None or boss.defeated)

    def _maybe_open_exit(self: "World") -> None:
        if self.exit_ready and self.exit_cell is None and self.state == PLAYING:
            self.exit_cell = self.choose_exit_cell()
            self.events.append(Event(ev.EXIT_SPAWN, cell=self.exit_cell))

    def choose_exit_cell(self: "World") -> Cell:
        """A tile far (in frog moves, incl. super jumps) from the frog."""
        f = self.frog
        tiles = self.tiles
        origin = f.ground_cell() if tiles.standable(f.ground_cell()) else f.last_safe

        def good(c: Cell) -> bool:        # a fixed, lasting tile (no unstable / moving row)
            t = tiles.tile(c)
            return t is not None and t.standable and t.unstable is None and c[1] not in tiles.rows

        def moves(c: Cell):
            for d in range(4):
                for k in (1, 2):
                    n = step(c, d, k)
                    if tiles.standable(n):
                        yield n
        dist = bfs_distances(origin, moves)
        blocked = {origin}
        for e in self.enemies:
            blocked |= e.occupied()
        cands = [c for c in dist if c not in blocked and good(c)]
        if not cands:
            cands = [c for c in tiles.standable_cells() if c != origin and good(c)] \
                or [c for c in tiles.standable_cells() if c != origin] or [origin]
            return self.rng.choice(sorted(cands))
        cands.sort(key=lambda c: (-dist[c], -manhattan(c, origin), c))
        top = cands[:max(1, len(cands) // 5)]
        return self.rng.choice(top)

    # ------------------------------------------------------------ bosses
    def boss_hit(self: "World", boss: Boss) -> None:
        """Called by :meth:`Boss.take_hit` (HUD pill + popup)."""
        self.events.append(Event(ev.BOSS_HIT, pos=boss.center(), value=(boss.kind, boss.hp)))

    def boss_defeated(self: "World", boss: Boss) -> None:
        self.events.append(Event(ev.BOSS_DEFEATED, pos=boss.center(), value=boss.kind))
        self._maybe_open_exit()

    # ------------------------------------------------------------ win
    def _win(self: "World") -> None:
        self.frog.state = fs.WON
        self.frog.buffered = None
        self.state = WON
        self.end_timer = config.WIN_DELAY
        self.result = compute_result(self.level.id, self.rules.difficulty, self.time,
                                     self.eaten, self.hearts, not self.damaged,
                                     self.level.par_time, self.time_left)
        self.events.append(Event(ev.WIN))

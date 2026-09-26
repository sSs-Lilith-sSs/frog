"""Damage of the :class:`~jebik.game.world.World`: hits, falls, respawn, losing.

EZZZ: every hit / fall / extra fly costs a heart; 0 hearts = lost.
TOBI PIZDA (``rules.one_hit``): the first hit / fall / extra fly loses the
level at once (the scene restarts it); running out of time loses too.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .. import config
from . import events as ev
from . import frog as fs
from .enemy import Enemy
from .events import Event
from .grid import Cell, bfs_distances, manhattan
from .rules import LOST, PLAYING

if TYPE_CHECKING:
    from .world import World


class Damage:
    """Mixin: hearts, hits, falling, respawning. ``self`` is the World."""

    def _lose_heart(self: "World", reason: str) -> None:
        self.hearts = max(0, self.hearts - 1)
        self.damaged = True
        if self.rules.one_hit:
            self.hearts = 0
            self._lose(reason)

    # ------------------------------------------------------------ enemies
    def _check_enemies(self: "World") -> None:
        f = self.frog
        if f.invuln > 0 or f.airborne or f.state in (fs.SPLASH, fs.DEAD, fs.WON):
            return
        pos = f.pos()
        for e in self.enemies:
            if e.hurts(self, pos):
                self._hit(e)
                return

    def _hit(self: "World", enemy: Enemy | None) -> None:
        f = self.frog
        self.events.append(Event(ev.HIT, pos=f.pos(), value=enemy.kind if enemy else None))
        self._lose_heart("hit")
        f.invuln = config.INVULN_TIME
        if enemy is not None:
            enemy.on_frog_hit(self)
        if self.state != PLAYING:
            return
        if self.hearts <= 0:
            self._lose("hearts")
            return
        if f.state in (fs.IDLE, fs.TONGUE):
            self._release_tongue()
            f.state, f.state_timer = fs.HIT, config.HIT_STUN_TIME

    # ------------------------------------------------------------ falling
    def _ground_check(self: "World") -> None:
        """The ground vanished under the frog (sinking pad, hole, row edge)?"""
        f = self.frog
        if self.state == PLAYING and f.grounded and not self.can_stand(f.cell):
            self._fall(f.cell)
        self.flies.unrest_where(lambda c: not self.tiles.standable(c))

    def _fall(self: "World", cell: Cell) -> None:
        f = self.frog
        self._release_tongue()
        f.cell = cell
        f.state, f.state_timer, f.splash_cell = fs.SPLASH, config.SPLASH_TIME, cell
        f.buffered = None
        self.events.append(Event(ev.SPLASH, cell=cell))
        self._lose_heart("fall")

    def _respawn(self: "World") -> None:
        f = self.frog
        if self.hearts <= 0:
            self._lose("hearts")
            return
        f.cell = self._safe_respawn_cell(f.last_safe)
        f.hop_from = f.hop_to = f.last_safe = f.cell
        f.state = fs.IDLE
        f.invuln = config.INVULN_TIME
        f.splash_cell = None
        for e in self.enemies:
            e.on_frog_respawn(self, f.cell)
        self.events.append(Event(ev.RESPAWN, cell=f.cell))

    def _safe_respawn_cell(self: "World", preferred: Cell) -> Cell:
        """Nearest standable tile (by hops) that is not next to an enemy."""
        tiles = self.tiles
        danger: set[Cell] = set()
        for e in self.enemies:
            danger |= e.occupied()

        def safe(c: Cell) -> bool:
            t = tiles.tile(c)
            lasting = t is not None and (t.unstable is None or t.unstable.state == "stable")
            return lasting and c[1] not in tiles.rows and \
                all(manhattan(c, d) >= config.SAFE_RESPAWN_DIST for d in danger)

        start = preferred if tiles.standable(preferred) else self.level.frog_start
        dist = bfs_distances(start, tiles.neighbors)
        for cell in sorted(dist, key=lambda c: (dist[c], c)):
            if tiles.standable(cell) and safe(cell):
                return cell
        cells = sorted(tiles.standable_cells(), key=lambda c: (manhattan(c, start), c))
        for cell in cells:
            if safe(cell):
                return cell
        return cells[0] if cells else self.level.frog_start

    # ------------------------------------------------------------ end
    def _lose(self: "World", reason: str = "hearts") -> None:
        if self.state != PLAYING:
            return
        self._release_tongue()
        if not (reason == "fall" and self.frog.state == fs.SPLASH):
            self.frog.state = fs.DEAD          # a TOBI fall stays under water
        self.frog.buffered = None
        self.state = LOST
        self.lose_reason = reason
        self.end_timer = config.LOSE_DELAY
        self.events.append(Event(ev.LOSE, value=reason))

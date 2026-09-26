"""FieldRenderer: base class for a world's playing field.

A world subclasses it and implements a few hooks; the base draws every tile
from the live :class:`~jebik.game.tiles.TileMap` and animates the generic
hazard states the same way in every world:

* unstable tile WARNING — flicker + tremble, faster toward the end;
* GONE / temporary hole — sinks (shrink + fade), then hidden; pops back in;
* moving rows — tiles slide into their new cell;
* landing dip — the tile squashes a little under the frog;
* obstacles — drawn with :meth:`obstacle_sprite`.

Hooks (override in the world):

* :meth:`build_static` — full-screen backdrop + the field "floor" (water /
  pit / abyss everywhere, tiles are drawn on top). Called once, cached.
* :meth:`tile_sprite` — sprite of one solid tile (cached per tile id).
* :meth:`tile_image` — per-frame variant (e.g. bobbing frames).
* :meth:`tile_center` — tile centre in field px (default: cell centre).
* :meth:`obstacle_sprite`, :meth:`draw_exit`, :meth:`update`, :meth:`on_event`.

Art style: supersample x3 (``render_ss``) then smoothscale; cache static
surfaces; never run numpy per frame.
"""
from __future__ import annotations

import math

import pygame as pg

from .. import config
from ..game.events import Event
from ..game.grid import Level
from ..game.tiles import GONE, OBSTACLE, SOLID, WARNING, Tile
from .common import disc_sprite, render_ss
from .glow import additive_glow

Color = tuple[int, int, int]
_LEVEL_CACHE: dict[tuple, dict] = {}      # survives restarts of the same level
SINK_TIME = 0.35           # vanish animation
POP_TIME = 0.3             # come-back animation
DIP_TIME = 0.5


class FieldRenderer:
    fill: Color = (40, 40, 40)          # behind the field when the screen shakes
    grid_color = (255, 255, 255, 55)

    def __init__(self, level: Level, cs: int, rect: pg.Rect):
        self.level = level
        self.cs = cs
        self.k = cs / 64
        self.rect = rect
        self.t = 0.0
        self.dips: dict[tuple[int, int], float] = {}
        self._sprites: dict[tuple[int, str], pg.Surface] = self.level_cache().setdefault("sprites", {})
        self._flash: dict[int, pg.Surface] = {}
        self._static: pg.Surface | None = None

    # ------------------------------------------------------------ hooks
    def build_static(self) -> pg.Surface:
        s = pg.Surface((config.SCREEN_W, config.SCREEN_H))
        s.fill(self.fill)
        return s

    def tile_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        """Sprite of a solid tile first seen at ``cell`` (cached by tile id)."""
        cs = self.cs
        return render_ss((cs, cs), lambda s, ss: pg.draw.rect(
            s, (200, 200, 200), (2 * ss, 2 * ss, (cs - 4) * ss, (cs - 4) * ss),
            border_radius=int(10 * ss)), ss=3)

    def tile_image(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        return self.sprite(tile, cell)

    def tile_center(self, tile: Tile, cell: tuple[int, int]) -> tuple[float, float]:
        return (cell[0] * self.cs + self.cs / 2, cell[1] * self.cs + self.cs / 2)

    def obstacle_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        cs = self.cs
        return render_ss((cs, cs), lambda s, ss: pg.draw.circle(
            s, (110, 80, 50), (cs * ss / 2, cs * ss / 2), cs * ss * .36), ss=3)

    def draw_exit(self, surf: pg.Surface, center: tuple[float, float], age: float) -> None:
        """The exit on its cell; ``age`` = seconds since it appeared."""
        glow = self._exit_glow()
        pulse = (0.72 + 0.28 * math.sin(self.t * 3)) * min(1.0, age / 0.4)
        img = glow[max(0, min(len(glow) - 1, int(pulse * len(glow)) - 1))]
        surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))),
                  special_flags=pg.BLEND_RGB_ADD)
        for i in range(6):                      # slow sparkles circling the exit
            a = self.t * 0.8 + i * math.pi / 3
            rr = self.cs * (0.62 + 0.06 * math.sin(self.t * 2 + i))
            sp = disc_sprite(max(1.0, round(2.4 * self.k * 2) / 2), (255, 245, 200))
            surf.blit(sp, sp.get_rect(center=(round(center[0] + math.cos(a) * rr),
                                              round(center[1] + math.sin(a) * rr * 0.8))))

    def update(self, dt: float, world, effects, view) -> None:
        """Ambient animation (ripples, falling leaves...)."""

    def on_event(self, event: Event, view, effects, audio) -> bool:
        """React to a world event: particles via ``effects``, sounds via
        ``audio.play("<world>.<name>")``. Every event passes here first —
        including world-specific kinds like ``"earth.stomp"``. Return True if
        handled (the scene then skips its default reaction)."""
        return False

    # ------------------------------------------------------------ helpers
    def level_cache(self) -> dict:
        """A dict kept for this renderer class + level layout + cell size, so
        restarting a level reuses expensive surfaces (static field, sprites)."""
        lv = self.level
        key = (type(self).__qualname__, lv.id, lv.pads, lv.obstacles, self.cs, self.rect.topleft)
        if key not in _LEVEL_CACHE:
            if len(_LEVEL_CACHE) >= 4:
                _LEVEL_CACHE.pop(next(iter(_LEVEL_CACHE)))
            _LEVEL_CACHE[key] = {}
        return _LEVEL_CACHE[key]

    def static(self) -> pg.Surface:
        if self._static is None:
            cache = self.level_cache()
            if "static" not in cache:
                cache["static"] = self.build_static()
            self._static = cache["static"]
        return self._static

    def sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        key = (tile.id, tile.kind)
        img = self._sprites.get(key)
        if img is None:
            img = self.tile_sprite(tile, cell) if tile.kind != OBSTACLE \
                else self.obstacle_sprite(tile, cell)
            self._sprites[key] = img
        return img

    def _exit_glow(self) -> list[pg.Surface]:
        if not hasattr(self, "_glow"):
            self._glow = additive_glow(78 * self.k, (150, 130, 70))
        return self._glow

    def _flash_of(self, tile: Tile, img: pg.Surface) -> pg.Surface:
        f = self._flash.get(tile.id)
        if f is None or f.get_size() != img.get_size():
            f = img.copy()
            f.fill((90, 40, 30), special_flags=pg.BLEND_RGB_ADD)
            self._flash[tile.id] = f
        return f

    def dip(self, cell: tuple[int, int], strength: float = 1.0) -> None:
        self.dips[cell] = 0.0

    def tick(self, dt: float) -> None:
        self.t += dt
        for c in list(self.dips):
            self.dips[c] += dt
            if self.dips[c] > DIP_TIME:
                del self.dips[c]

    # ------------------------------------------------------------ drawing
    def draw_tiles(self, surf: pg.Surface, world, off: tuple[int, int],
                   skip: tuple[int, int] | None = None) -> None:
        tiles = world.tiles
        fx, fy = self.rect.x + off[0], self.rect.y + off[1]
        for cell, tile in sorted(tiles.items(), key=lambda it: (it[0][1], it[0][0])):
            if tile.kind not in (SOLID, OBSTACLE) or cell == skip:
                continue
            scale, alpha, flash, jitter = self._state_look(tile)
            if scale <= 0.02 or alpha <= 0:
                continue
            img = self.tile_image(tile, cell) if tile.kind == SOLID else self.sprite(tile, cell)
            if flash:
                img = self._flash_of(tile, img)
            if cell in self.dips:
                d = self.dips[cell] / DIP_TIME
                scale *= 1 - 0.09 * math.sin(min(1.0, d) * math.pi) * (1 - d * 0.5)
            if abs(scale - 1) > 1e-3:
                img = pg.transform.smoothscale(img, (max(1, int(img.get_width() * scale)),
                                                     max(1, int(img.get_height() * scale))))
            if alpha < 255:
                img = img.copy()
                img.set_alpha(alpha)
            cx, cy = self.tile_center(tile, cell)
            cx += tiles.row_offset(cell[1]) * self.cs + jitter
            surf.blit(img, img.get_rect(center=(round(fx + cx), round(fy + cy))))

    def _state_look(self, tile: Tile) -> tuple[float, int, bool, float]:
        """(scale, alpha, flash, x jitter) for the tile's hazard state."""
        u = tile.unstable
        if tile.hole_timer > 0:
            gone_for = tile.hole_time - tile.hole_timer
            if gone_for < SINK_TIME:
                k = gone_for / SINK_TIME
                return 1 - 0.6 * k, int(255 * (1 - k)), False, 0.0
            if tile.hole_timer < POP_TIME:                 # growing back
                k = 1 - tile.hole_timer / POP_TIME
                return 0.4 + 0.6 * k, int(255 * k), False, 0.0
            return 0.0, 0, False, 0.0
        if u is None:
            return 1.0, 255, False, 0.0
        if u.state == WARNING:
            p = u.progress
            freq = 6 + 16 * p
            flash = math.sin(self.t * freq * math.pi) > 0.2 - 0.4 * p
            jitter = math.sin(self.t * 55) * (1.0 + 2.5 * p) * self.k
            return 1.0 - 0.06 * p, 255, flash, jitter
        if u.state == GONE:
            gone_for = u.progress * u.gone
            if gone_for < SINK_TIME:
                k = gone_for / SINK_TIME
                return 1 - 0.6 * k, int(255 * (1 - k)), False, 0.0
            return 0.0, 0, False, 0.0
        if u.back_t < POP_TIME:
            k = u.back_t / POP_TIME
            return 0.6 + 0.4 * k + 0.12 * math.sin(k * math.pi), int(120 + 135 * k), False, 0.0
        return 1.0, 255, False, 0.0

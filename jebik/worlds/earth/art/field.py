"""EarthField: meadow backdrop, grass tiles over merged organic pits.

The whole field is painted once with numpy (``paint.earth_field``): permanent
pits of the level merge into organic dirt holes. Each grass tile's sprite is
cut from a grass-only copy of that painting, so an unchanged tile looks exactly
like the static picture; when a tile sinks (mole / boar / crumbling ground) a
cached single-pit patch is drawn under it first.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.common import disc_sprite
from ....art.field import FieldRenderer
from ....game import events as ev
from ....game.tiles import SOLID, Tile
from .boar_draw import draw_burrow, draw_stump
from .meadow import meadow_backdrop
from .paint import crumble_overlay, earth_field, sprite

DIRT = (150, 110, 70)
CHIPS = (196, 150, 96)


@lru_cache(maxsize=16)
def pit_patch(cs: int, variant: int, row: int, rows: int) -> pg.Surface:
    """An opaque single-cell pit on the seam background (temporary holes)."""
    return earth_field(1, 1, cs, {(0, 0)}, seed=40 + variant, row0=row, rows_total=rows)


@lru_cache(maxsize=8)
def stump_sprite(k: float) -> pg.Surface:
    return sprite((64 * k, 64 * k), lambda s, q, cx, cy: draw_stump(s, cx, cy, k * q))


@lru_cache(maxsize=8)
def burrow_sprite(k: float) -> pg.Surface:
    return sprite((72 * k, 64 * k), lambda s, q, cx, cy: draw_burrow(s, cx, cy, k * q))


@lru_cache(maxsize=8)
def shadow(w: int, h: int, alpha: int = 70) -> pg.Surface:
    return sprite((w, h), lambda s, q, cx, cy: pg.draw.ellipse(s, (25, 45, 20, alpha), (0, 0, w * q, h * q)))


class EarthField(FieldRenderer):
    fill = (60, 44, 28)
    grid_color = (255, 255, 255, 40)
    # sounds from tools/gen_audio_earth.py; volumes balance the files' loudness,
    # a third value = min gap (a stomp cracks five tiles at once -> one sound)
    event_sounds = {
        "earth.hedgehog_curl": ("earth.hedgehog_roll", 1.4),
        "earth.hedgehog_bump": ("earth.bump", 1.0),
        "earth.hedgehog_fall": ("earth.fall", 1.2),
        "earth.fox_jump": ("earth.fox_leap", 1.25),
        "earth.fox_land": ("earth.fox_land", 1.2),
        "earth.mole_tremor": ("earth.mole_tremor", 1.15),
        "earth.mole_pop": ("earth.mole_pop", 1.35),
        "earth.boar_charge": ("earth.charge", 1.3),
        "earth.stomp": ("earth.stomp", 1.2),
        "earth.boar_crash": ("earth.crash", 1.3),
        "earth.stump_break": ("earth.stump", 1.4, .2),
        "earth.stump_grow": ("earth.stump_grow", .7),
        ev.TILE_WARN: ("earth.crumble_warn", 1.1, .35),
        ev.TILE_GONE: ("earth.crumble", .95, .3),
    }
    tell_sounds = {"charge": ("earth.boar_snort", 1.2), "stomp": ("earth.boar_snort", 1.2)}

    def _paint(self):
        cache = self.level_cache()
        if "paint" not in cache:
            lv = self.level
            holes = {c for c in lv.cells() if c not in lv.pads and c not in lv.obstacles}
            avoid = set(lv.obstacles) | {lv.frog_start} | {s.cell for s in lv.spawns if s.cell}
            cache["paint"] = earth_field(lv.width, lv.height, self.cs, holes, crumble=set(lv.unstable),
                                         avoid=avoid, seed=11 + lv.seed + lv.width, with_mask=True)
        return cache["paint"]

    def build_static(self) -> pg.Surface:
        lv = self.level
        s = meadow_backdrop(self.rect, seed=20 + lv.width + lv.height)
        img, _ = self._paint()
        s.blit(img, self.rect.topleft)
        cr = crumble_overlay(self.cs)
        for (x, y) in lv.unstable:
            s.blit(cr, (self.rect.x + x * self.cs, self.rect.y + y * self.cs))
        return s

    def tile_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        cs = self.cs
        _, grass = self._paint()
        home = (tile.id % self.level.width, tile.id // self.level.width)
        img = grass.subsurface((home[0] * cs, home[1] * cs, cs, cs)).copy()
        if tile.unstable is not None and home in self.level.unstable:
            img.blit(crumble_overlay(cs), (0, 0))
        return img

    def obstacle_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        k = self.k
        img = self.tile_sprite(Tile(tile.id, SOLID), cell)
        c = self.cs / 2
        sh = shadow(int(58 * k), int(50 * k))
        img.blit(sh, sh.get_rect(center=(round(c + 3 * k), round(c + 6 * k))))
        st = stump_sprite(round(k * 1.02, 3))
        img.blit(st, st.get_rect(center=(round(c), round(c))))
        return img

    def tile_blits(self, world, off, skip=None):
        cs = self.cs
        fx, fy = self.rect.x + off[0], self.rect.y + off[1]
        pits = []
        for cell, tile in world.tiles.items():      # temporary / crumbled holes: dirt pits first
            if tile.kind == SOLID and not tile.standable:
                patch = pit_patch(cs, (cell[0] * 7 + cell[1] * 3) % 4, cell[1], self.level.height)
                pits.append((patch, (fx + cell[0] * cs, fy + cell[1] * cs), False, True))
        return pits + super().tile_blits(world, off, skip)

    def draw_exit(self, surf: pg.Surface, center: tuple[float, float], age: float) -> None:
        super().draw_exit(surf, center, age)
        grow = min(1.0, age / 0.4)
        img = burrow_sprite(round(self.k * 1.05, 3))
        if grow < 1:
            img = pg.transform.smoothscale(img, (max(1, int(img.get_width() * grow)),
                                                 max(1, int(img.get_height() * grow))))
        surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1] + 2 * self.k))))
        glow = disc_sprite(max(1.0, round(3 * self.k * 2) / 2), (255, 235, 170))
        a = self.t * 1.3
        surf.blit(glow, glow.get_rect(center=(round(center[0] + math.cos(a) * 24 * self.k),
                                              round(center[1] - 20 * self.k + math.sin(a) * 6 * self.k))))

    def on_event(self, event: ev.Event, view, effects, audio) -> bool:
        k = self.k
        kind = event.kind
        self.event_sound(event, audio)
        if kind in (ev.TILE_GONE, ev.HOLE_OPEN) and event.cell is not None:
            x, y = view.to_px(event.cell)
            effects.burst(x, y, DIRT, n=10, speed=120 * k, size=4 * k, life=0.6, gravity=500 * k, up=120 * k)
            return True
        if kind == ev.TILE_WARN and event.cell is not None:
            x, y = view.to_px(event.cell)
            effects.burst(x, y, DIRT, n=5, speed=50 * k, size=3 * k, life=0.5)
            return True
        if kind == "earth.stump_break" and event.cell is not None:
            x, y = view.to_px(event.cell)
            effects.burst(x, y, CHIPS, n=18, speed=260 * k, size=6 * k, life=0.8, gravity=700 * k, up=200 * k)
            effects.shake(10 * k)
            return True
        if kind == "earth.stump_grow" and event.cell is not None:
            x, y = view.to_px(event.cell)
            effects.ring(x, y, 6 * k, 34 * k, 0.6, (150, 220, 110), 3)
            return True
        if kind == "earth.boar_crash" and event.pos is not None:
            x, y = view.to_px(event.pos)
            effects.shake(14 * k)
            effects.burst(x, y, (215, 190, 150), n=16, speed=200 * k, size=7 * k, life=0.7)
            return True
        if kind == "earth.stomp" and event.pos is not None:
            x, y = view.to_px(event.pos)
            effects.shake(12 * k)
            for i in range(3):
                effects.ring(x, y, 20 * k, (90 + 40 * i) * k, 0.6 + 0.15 * i, (200, 160, 110), 4)
            return True
        if kind == "earth.hedgehog_fall" and event.pos is not None:
            x, y = view.to_px(event.pos)
            effects.burst(x, y, DIRT, n=10, speed=90 * k, size=4 * k, life=0.5)
            effects.popup("!", x, y - 20 * k, (255, 230, 150), size=int(34 * k))
            return True
        if kind in ("earth.mole_pop", "earth.fox_land", "earth.boar_charge") \
                and (event.cell or event.pos) is not None:
            x, y = view.to_px(event.cell if event.cell is not None else event.pos)
            effects.burst(x, y, (190, 150, 105), n=8, speed=110 * k, size=4 * k, life=0.5,
                          gravity=400 * k, up=80 * k)
            return True
        return kind.startswith("earth.")

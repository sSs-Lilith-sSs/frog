"""Earth-world art — PLACEHOLDER (grass tiles over dark pits, stumps, burrow exit).

TODO(earth agent): proper field (grass texture, pit depth, crumbling look),
decor around the field, hedgehog / fox / mole / boar renderers
(``@register_enemy_art``), ``boss_icon("boar")``, story illustration.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from .... import config
from ....art.common import lerp, render_ss
from ....art.field import FieldRenderer
from ....art.world_art import WorldArt
from ....game.tiles import Tile

W, H = config.SCREEN_W, config.SCREEN_H
PIT = (52, 36, 26)
GRASS_D, GRASS_L = (82, 150, 60), (128, 196, 88)


class EarthField(FieldRenderer):
    fill = (70, 52, 34)

    def build_static(self) -> pg.Surface:
        ss = config.SS_BACKDROP
        rnd = random.Random(31 + self.level.seed)
        s = pg.Surface((W * ss, H * ss))
        for y in range(H):                                   # meadow around the field
            pg.draw.rect(s, lerp((150, 190, 100), (96, 140, 70), y / H), (0, y * ss, W * ss, ss))
        for _ in range(260):
            x, y = rnd.randint(0, W), rnd.randint(config.HUD_H, H)
            h = rnd.randint(10, 30)
            pg.draw.line(s, (70, 125, 55), (x * ss, y * ss), ((x + rnd.randint(-5, 5)) * ss, (y - h) * ss), 2 * ss)
        r = self.rect
        frame = r.inflate(24, 24)
        pg.draw.rect(s, (60, 45, 30), [v * ss for v in frame.move(0, 6)], border_radius=18 * ss)
        pg.draw.rect(s, (110, 80, 50), [v * ss for v in frame], border_radius=18 * ss)
        pg.draw.rect(s, PIT, [v * ss for v in r], border_radius=10 * ss)
        for _ in range(self.level.width * self.level.height * 3):   # pit speckles
            x, y = rnd.uniform(r.left, r.right), rnd.uniform(r.top, r.bottom)
            pg.draw.circle(s, (70, 50, 36), (x * ss, y * ss), rnd.uniform(1, 3) * ss)
        return pg.transform.smoothscale(s, (W, H))

    def tile_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        cs = self.cs
        rnd = random.Random(tile.id * 7 + 3)

        def draw(s: pg.Surface, ss: float) -> None:
            m, rad = 2 * ss, int(cs * .22 * ss)
            pg.draw.rect(s, (96, 66, 40), (m, m + 5 * ss * self.k, cs * ss - 2 * m, cs * ss - 2 * m),
                         border_radius=rad)
            pg.draw.rect(s, GRASS_D, (m, m, cs * ss - 2 * m, cs * ss - 2 * m), border_radius=rad)
            pg.draw.rect(s, GRASS_L, (m + 4 * ss, m + 3 * ss, cs * ss - 2 * m - 8 * ss, cs * ss * .55),
                         border_radius=rad)
            for _ in range(6):
                x = rnd.uniform(.2, .8) * cs * ss
                y = rnd.uniform(.35, .85) * cs * ss
                pg.draw.line(s, (60, 125, 50), (x, y), (x + rnd.uniform(-3, 3) * ss, y - 7 * ss * self.k),
                             max(1, int(1.5 * ss)))
        return render_ss((cs, cs), draw, ss=3)

    def obstacle_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        cs = self.cs

        def draw(s: pg.Surface, ss: float) -> None:            # stump on grass
            c = cs * ss / 2
            pg.draw.rect(s, GRASS_D, (2 * ss, 2 * ss, cs * ss - 4 * ss, cs * ss - 4 * ss),
                         border_radius=int(cs * .22 * ss))
            pg.draw.ellipse(s, (90, 60, 35), (c - cs * .34 * ss, c - cs * .22 * ss, cs * .68 * ss, cs * .56 * ss))
            pg.draw.ellipse(s, (196, 150, 96), (c - cs * .3 * ss, c - cs * .3 * ss, cs * .6 * ss, cs * .46 * ss))
            for r in (.2, .12, .05):
                pg.draw.ellipse(s, (150, 106, 62), (c - cs * r * ss, c - cs * (r * .77 + .07) * ss,
                                                    cs * r * 2 * ss, cs * r * 1.54 * ss), max(1, int(ss)))
        return render_ss((cs, cs), draw, ss=3)

    def draw_exit(self, surf: pg.Surface, center: tuple[float, float], age: float) -> None:
        super().draw_exit(surf, center, age)
        k, cs = self.k, self.cs
        grow = min(1.0, age / 0.4)
        r = pg.Rect(0, 0, cs * .8 * grow, cs * .56 * grow)
        r.center = (round(center[0]), round(center[1] + 4 * k))
        pg.draw.ellipse(surf, (150, 110, 70), r.inflate(12 * k, 10 * k))     # dirt mound
        pg.draw.ellipse(surf, (25, 16, 12), r)                                # the burrow
        pg.draw.arc(surf, (200, 160, 110), r.inflate(12 * k, 10 * k), 0.3, math.pi - .3, max(1, int(3 * k)))


class EarthArt(WorldArt):
    field_cls = EarthField

    def icon(self, size: int) -> pg.Surface:
        def draw(s: pg.Surface, ss: float) -> None:      # grass tuft
            u = size * ss / 20
            for dx, h, lean in ((-5, 12, -3), (0, 16, 0), (5, 11, 3), (-2, 9, -1), (3, 13, 1)):
                pg.draw.polygon(s, (90, 160, 60), [((10 + dx - 1.6) * u, 18 * u), ((10 + dx + 1.6) * u, 18 * u),
                                                   ((10 + dx + lean) * u, (18 - h) * u)])
            pg.draw.ellipse(s, (130, 95, 60), (3 * u, 16.5 * u, 14 * u, 3.5 * u))
        return render_ss((size, size), draw)


ART = EarthArt()

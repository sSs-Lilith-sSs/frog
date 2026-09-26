"""Sky-world art — PLACEHOLDER (pink cloud tiles over a dusky abyss, rainbow exit).

TODO(sky agent): proper clouds (soft puffs, melting look), decor around the
field, swallow / hawk / crow / Jesus renderers (``@register_enemy_art``),
``boss_icon("jesus")``, story illustration.
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
CLOUD, CLOUD_SHADE = (255, 196, 224), (226, 150, 196)
RAINBOW = ((235, 80, 90), (245, 150, 70), (245, 215, 80), (120, 200, 110), (90, 160, 225), (150, 110, 210))


def cloud_puffs(rnd: random.Random) -> list[tuple[float, float, float]]:
    """Blobs (x, y, r) in cell units around the centre."""
    return [(rnd.uniform(-.2, .2), rnd.uniform(-.06, .06), rnd.uniform(.26, .32)),
            (-.2 + rnd.uniform(-.04, .04), .06, rnd.uniform(.2, .25)),
            (.2 + rnd.uniform(-.04, .04), .07, rnd.uniform(.2, .25)),
            (rnd.uniform(-.1, .1), .12, .24)]


class SkyField(FieldRenderer):
    fill = (70, 40, 90)

    def build_static(self) -> pg.Surface:
        ss = config.SS_BACKDROP
        rnd = random.Random(41 + self.level.seed)
        s = pg.Surface((W * ss, H * ss))
        for y in range(H):                                     # dusk sky
            t = y / H
            col = lerp((70, 50, 120), (240, 150, 170), t) if t < .8 else lerp((240, 150, 170), (255, 200, 170), (t - .8) / .2)
            pg.draw.rect(s, col, (0, y * ss, W * ss, ss))
        for _ in range(90):
            pg.draw.circle(s, (255, 240, 250), (rnd.randint(0, W) * ss, rnd.randint(0, H // 2) * ss),
                           rnd.uniform(.8, 2.2) * ss)
        for side in (0, 1):                                    # big soft clouds at the sides
            for _ in range(9):
                x = rnd.randint(-80, 260) if side == 0 else rnd.randint(W - 260, W + 80)
                y = rnd.randint(200, H)
                pg.draw.circle(s, (255, 214, 232), (x * ss, y * ss), rnd.randint(60, 130) * ss)
        r = self.rect
        pg.draw.rect(s, (120, 80, 140), [v * ss for v in r.inflate(20, 20)], border_radius=22 * ss)
        abyss = pg.Surface((r.w * ss, r.h * ss))
        for y in range(r.h):
            pg.draw.rect(abyss, lerp((60, 30, 80), (22, 10, 40), y / r.h), (0, y * ss, r.w * ss, ss))
        for _ in range(self.level.width * self.level.height):
            pg.draw.circle(abyss, (200, 170, 230), (rnd.uniform(0, r.w) * ss, rnd.uniform(0, r.h) * ss),
                           rnd.uniform(.6, 1.6) * ss)
        s.blit(abyss, (r.x * ss, r.y * ss))
        return pg.transform.smoothscale(s, (W, H))

    def tile_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        cs = self.cs
        puffs = cloud_puffs(random.Random(tile.id * 11 + 5))

        def draw(s: pg.Surface, ss: float) -> None:
            c = cs * ss / 2
            for dx, dy, r in puffs:
                pg.draw.circle(s, CLOUD_SHADE, (c + dx * cs * ss, c + (dy + .05) * cs * ss), r * cs * ss)
            for dx, dy, r in puffs:
                pg.draw.circle(s, CLOUD, (c + dx * cs * ss, c + dy * cs * ss), r * cs * ss * .94)
            pg.draw.circle(s, (255, 236, 246), (c - .1 * cs * ss, c - .1 * cs * ss), .1 * cs * ss)
        return render_ss((cs, cs), draw, ss=3)

    def draw_exit(self, surf: pg.Surface, center: tuple[float, float], age: float) -> None:
        super().draw_exit(surf, center, age)
        cs, k = self.cs, self.k
        grow = min(1.0, age / 0.5)
        cx, cy = center
        for i, col in enumerate(RAINBOW):                      # rainbow arc on the cloud
            rr = cs * (.46 - i * .045) * grow
            if rr <= 2:
                continue
            rect = pg.Rect(0, 0, rr * 2, rr * 2)
            rect.center = (round(cx), round(cy + cs * .12))
            pg.draw.arc(surf, col, rect, 0, math.pi, max(2, int(4 * k)))


class SkyArt(WorldArt):
    field_cls = SkyField

    def icon(self, size: int) -> pg.Surface:
        def draw(s: pg.Surface, ss: float) -> None:      # pink cloud
            u = size * ss / 20
            for cx, cy, r in ((7, 12, 4.5), (12, 10, 5.5), (15.5, 13, 3.8), (10, 14, 4)):
                pg.draw.circle(s, (245, 175, 210), (cx * u, cy * u), r * u)
        return render_ss((size, size), draw)


ART = SkyArt()

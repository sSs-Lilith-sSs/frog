"""Full-screen backdrops: the menu pond (menu.py mockup) and the shores
around the playing field (scene.py mockup). Rendered once, supersampled."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame as pg

from .. import config
from .common import lerp, render_ss

W, H = config.SCREEN_W, config.SCREEN_H


def simple_pad(s: pg.Surface, c: tuple[float, float], rad: float, a: float, u: float = 1) -> None:
    """Menu lily pad (``common.pad`` in the mockup)."""
    cx, cy = c
    pg.draw.circle(s, (30, 120, 50), (cx, cy + 3 * u), rad)
    pg.draw.circle(s, (70, 180, 80), c, rad)
    pg.draw.circle(s, (95, 200, 95), c, int(rad * .75), max(1, int(3 * u)))
    ang, w = math.radians(a), math.radians(22)
    pg.draw.polygon(s, (45, 120, 170), [c, (cx + rad * 1.1 * math.cos(ang - w), cy + rad * 1.1 * math.sin(ang - w)),
                                        (cx + rad * 1.1 * math.cos(ang + w), cy + rad * 1.1 * math.sin(ang + w))])


def _menu_sky_color(y: int) -> tuple[int, int, int]:
    t = y / H
    if y < 560:
        col = [int(140 + 60 * t * 1.6), int(210 + 25 * t * 1.6), 240]
    else:
        col = [int(v * (1 - (t - .52) * .4)) for v in (50, 130, 175)]
    return tuple(max(0, min(255, v)) for v in col)


@lru_cache(maxsize=1)
def menu_background() -> pg.Surface:
    """Sky -> pond, hills, reeds and pads, same layout as the mockup
    (clouds, the big frog and the flies are separate, animated layers)."""
    ss = config.SS_BACKDROP
    s = pg.Surface((W * ss, H * ss))
    rnd = random.Random(5)
    for y in range(H):
        pg.draw.rect(s, _menu_sky_color(y), (0, y * ss, W * ss, ss))
    pg.draw.ellipse(s, (110, 180, 110), (-200 * ss, 470 * ss, 1100 * ss, 220 * ss))
    pg.draw.ellipse(s, (95, 170, 100), (900 * ss, 480 * ss, 1300 * ss, 200 * ss))
    for x in range(0, W, 18):
        h = rnd.randint(40, 120)
        if 520 < x < 1400:
            continue
        pg.draw.line(s, (60, 130, 60), (x * ss, 570 * ss),
                     ((x + rnd.randint(-10, 10)) * ss, (570 - h) * ss), 5 * ss)
        if rnd.random() < .3:
            pg.draw.ellipse(s, (120, 80, 40), ((x - 6) * ss, (570 - h - 10) * ss, 12 * ss, 34 * ss))
    for _ in range(14):
        x, y = rnd.randint(0, W), rnd.randint(640, 1060)
        simple_pad(s, (x * ss, y * ss), rnd.randint(35, 70) * ss, rnd.randint(0, 360), ss)
    simple_pad(s, (1500 * ss, 860 * ss), 150 * ss, 200, ss)       # the big pad
    return pg.transform.smoothscale(s, (W, H))


def menu_cloud_positions() -> list[tuple[int, int]]:
    """Cloud anchors in the same order/seed as the mockup."""
    rnd = random.Random(5)
    for x in range(0, W, 18):              # replay the reed/pad randomness
        rnd.randint(40, 120)
        if 520 < x < 1400:
            continue
        rnd.randint(-10, 10)
        rnd.random()
    for _ in range(14):
        rnd.randint(0, W), rnd.randint(640, 1060), rnd.randint(35, 70), rnd.randint(0, 360)
    return [(rnd.randint(100, 1800), rnd.randint(80, 300)) for _ in range(5)]


@lru_cache(maxsize=4)
def cloud_sprite(variant: int = 0) -> pg.Surface:
    blobs = [(0, 0, 40), (45, -10, 50), (95, 0, 38), (45, 15, 40)]
    if variant % 2:
        blobs = [(0, 5, 34), (38, -8, 46), (82, 2, 36), (40, 16, 36)]
    size = (200, 130)
    ox, oy = 50, 65

    def draw(s: pg.Surface, ss: float) -> None:
        for dx, dy, r in blobs:
            pg.draw.circle(s, (250, 252, 255), ((ox + dx) * ss, (oy + dy) * ss), r * ss)
    return render_ss(size, draw, ss=2)


CLOUD_ANCHOR = (50, 65)     # where the mockup's (x, y) sits inside the sprite


def pond_backdrop(field: pg.Rect, seed: int = 21) -> pg.Surface:
    """Gameplay surroundings: pond gradient, two grassy shores with reeds,
    stones and pink flowers, and the dark rounded frame of the field."""
    ss = config.SS_BACKDROP
    rnd = random.Random(seed)
    S = pg.Surface((W * ss, H * ss))
    for y in range(H):
        pg.draw.rect(S, lerp(config.C_POND_TOP, config.C_POND_BOTTOM, y / H), (0, y * ss, W * ss, ss))
    left_edge = min(340, field.left - 110)
    right_edge = max(W - 340, field.right + 110)
    for side in (0, 1):
        xs = left_edge - 600 if side == 0 else right_edge
        pg.draw.ellipse(S, (80, 150, 80), (xs * ss, 60 * ss, 600 * ss, 1150 * ss))
        pg.draw.ellipse(S, (105, 175, 95), ((xs + 30) * ss, 90 * ss, 540 * ss, 1090 * ss))
        for _ in range(55):
            if side == 0:
                x = rnd.randint(0, max(40, left_edge - 40))
            else:
                x = rnd.randint(min(W - 40, right_edge + 40), W)
            y = rnd.randint(130, H)
            r = rnd.random()
            if r < .45:
                h = rnd.randint(50, 120)
                pg.draw.line(S, (60, 120, 55), (x * ss, y * ss),
                             ((x + rnd.randint(-8, 8)) * ss, (y - h) * ss), 4 * ss)
                if rnd.random() < .5:
                    pg.draw.ellipse(S, (120, 80, 45), ((x - 5) * ss, (y - h - 4) * ss, 10 * ss, 30 * ss))
            elif r < .65:
                pg.draw.circle(S, (150, 150, 140), (x * ss, y * ss), rnd.randint(12, 26) * ss)
                pg.draw.circle(S, (175, 175, 165), ((x - 4) * ss, (y - 4) * ss), rnd.randint(6, 10) * ss)
            else:
                for a in range(0, 360, 72):
                    pg.draw.circle(S, (250, 200, 225), ((x + 7 * math.cos(math.radians(a))) * ss,
                                                        (y + 7 * math.sin(math.radians(a))) * ss), 6 * ss)
                pg.draw.circle(S, (255, 220, 80), (x * ss, y * ss), 4 * ss)
    frame = field.inflate(20, 20)
    pg.draw.rect(S, (20, 60, 70), (frame.x * ss, (frame.y + 6) * ss, frame.w * ss, frame.h * ss),
                 border_radius=18 * ss)
    pg.draw.rect(S, config.C_FIELD_BORDER, (frame.x * ss, frame.y * ss, frame.w * ss, frame.h * ss),
                 border_radius=18 * ss)
    return pg.transform.smoothscale(S, (W, H))

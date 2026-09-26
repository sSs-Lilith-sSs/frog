"""Water-world surroundings: pond, two grassy shores, reeds, stones, flowers
and the dark rounded frame of the field (scene.py mockup)."""
from __future__ import annotations

import math
import random

import pygame as pg

from .... import config
from ....art.common import lerp

W, H = config.SCREEN_W, config.SCREEN_H
POND_TOP = (80, 170, 195)
POND_BOTTOM = (45, 125, 170)
FIELD_BORDER = (30, 80, 90)


def pond_backdrop(field: pg.Rect, seed: int = 21) -> pg.Surface:
    """Gameplay surroundings: pond gradient, two grassy shores with reeds,
    stones and pink flowers, and the dark rounded frame of the field."""
    ss = config.SS_BACKDROP
    rnd = random.Random(seed)
    S = pg.Surface((W * ss, H * ss))
    for y in range(H):
        pg.draw.rect(S, lerp(POND_TOP, POND_BOTTOM, y / H), (0, y * ss, W * ss, ss))
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
    pg.draw.rect(S, FIELD_BORDER, (frame.x * ss, frame.y * ss, frame.w * ss, frame.h * ss),
                 border_radius=18 * ss)
    return pg.transform.smoothscale(S, (W, H))

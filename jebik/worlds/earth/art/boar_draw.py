"""Boar (2x2 boss), stun stars, stump, burrow and the HUD boar face — ported from the mockup."""
from __future__ import annotations

import math
import random

import numpy as np
import pygame as pg

from ....art.common import lerp, star_points
from .paint import sprite, tiny_flower


BOAR = (104, 72, 52)
BOAR_D = (70, 48, 36)
BOAR_L = (140, 102, 76)


def draw_boar(s, cx, cy, K, mode="idle"):
    """2x2 boar facing right, top-down. Spans about -62..+68 K by -46..+46 K."""
    bx = cx - 12 * K
    # hooves peeking out
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        hx0 = bx + sx * 28 * K + (6 * K if sx > 0 else 0)
        pg.draw.ellipse(s, (40, 28, 22), (hx0 - 8 * K, cy + sy * 40 * K - 6 * K, 16 * K, 12 * K))
    # tail curl
    pg.draw.arc(s, BOAR_D, (bx - 60 * K, cy - 7 * K, 14 * K, 14 * K), 0.5, 5.5, max(1, int(3.2 * K)))
    # body
    pg.draw.ellipse(s, BOAR_D, (bx - 50 * K, cy - 42 * K + 3 * K, 100 * K, 84 * K))
    pg.draw.ellipse(s, BOAR, (bx - 50 * K, cy - 42 * K, 100 * K, 84 * K))
    pg.draw.ellipse(s, BOAR_L, (bx - 40 * K, cy - 34 * K, 74 * K, 40 * K))
    pg.draw.ellipse(s, BOAR, (bx - 36 * K, cy - 20 * K, 72 * K, 40 * K))
    # fur tufts on the flanks
    for sy in (-1, 1):
        for i in range(5):
            x = bx - 30 * K + i * 13 * K
            y = cy + sy * (30 - abs(i - 2) * 2) * K
            pg.draw.arc(s, BOAR_D, (x - 5 * K, y - 4 * K, 10 * K, 8 * K), 0 if sy > 0 else math.pi,
                        math.pi if sy > 0 else 2 * math.pi, max(1, int(2 * K)))
    # bristly mane along the spine
    rnd = random.Random(2)
    for i in range(24):
        x = bx - 40 * K + i * 3.4 * K
        h = (5 + 6 * math.sin(i / 23 * math.pi)) * K
        for sgn in (-1, 1):
            pg.draw.polygon(s, (58, 40, 30), [(x - 2.4 * K, cy + sgn * 1.5 * K), (x + 2.4 * K, cy + sgn * 1.5 * K),
                                              (x + rnd.uniform(-1.5, 1.5) * K, cy + sgn * h)])
    pg.draw.line(s, (50, 34, 26), (bx - 40 * K, cy), (bx + 42 * K, cy), max(1, int(3.4 * K)))
    # head
    hx = cx + 40 * K
    pg.draw.ellipse(s, BOAR_D, (hx - 26 * K, cy - 29 * K + 2 * K, 46 * K, 58 * K))
    pg.draw.ellipse(s, BOAR, (hx - 26 * K, cy - 29 * K, 46 * K, 58 * K))
    pg.draw.ellipse(s, BOAR_L, (hx - 20 * K, cy - 22 * K, 24 * K, 18 * K))
    for sy in (-1, 1):   # ears (lying back)
        ear = [(hx - 14 * K, cy + sy * 12 * K), (hx - 30 * K, cy + sy * 34 * K), (hx - 6 * K, cy + sy * 26 * K)]
        pg.draw.polygon(s, BOAR_D, ear)
        pg.draw.polygon(s, (195, 125, 115), [(hx - 14 * K, cy + sy * 17 * K), (hx - 25 * K, cy + sy * 30 * K),
                                             (hx - 9 * K, cy + sy * 24 * K)])
    # snout
    sx0 = hx + 22 * K
    pg.draw.ellipse(s, (150, 98, 88), (sx0 - 10 * K, cy - 14 * K, 20 * K, 28 * K))
    pg.draw.ellipse(s, (218, 152, 142), (sx0 - 7 * K, cy - 13 * K, 16 * K, 26 * K))
    for sy in (-1, 1):
        pg.draw.ellipse(s, (105, 55, 55), (sx0 - 1 * K, cy + sy * 5.5 * K - 3 * K, 5.5 * K, 6 * K))
    # tusks
    for sy in (-1, 1):
        base = (sx0 - 8 * K, cy + sy * 14 * K)
        pts = [base, (base[0] + 8 * K, base[1] + sy * 6 * K), (base[0] + 17 * K, base[1] + sy * 3 * K),
               (base[0] + 9 * K, base[1] + sy * 0.5 * K), (base[0] + 2 * K, base[1] - sy * 2 * K)]
        pg.draw.polygon(s, (252, 247, 228), pts)
        pg.draw.lines(s, (205, 195, 165), False, pts[:3], max(1, int(1.3 * K)))
    # eyes
    for sy in (-1, 1):
        ex, ey = hx + 7 * K, cy + sy * 13 * K
        if mode == "stunned":
            pg.draw.circle(s, (255, 255, 255), (ex, ey), 6.5 * K)
            pts = [(ex + math.cos(t) * t * .62 * K, ey + math.sin(t) * t * .62 * K) for t in np.linspace(0, 9.5, 32)]
            pg.draw.lines(s, (40, 30, 30), False, pts, max(1, int(1.7 * K)))
        elif mode == "charge":
            pg.draw.circle(s, (255, 235, 220), (ex, ey), 5.8 * K)
            pg.draw.circle(s, (215, 40, 40), (ex + 1.2 * K, ey), 3.8 * K)
            pg.draw.circle(s, (255, 255, 255), (ex + 2.2 * K, ey - 1.2 * K), 1.2 * K)
            pg.draw.line(s, (40, 25, 20), (ex - 7 * K, ey + sy * 8 * K), (ex + 6 * K, ey + sy * 1.5 * K),
                         max(1, int(3 * K)))   # angry brow
        else:
            pg.draw.circle(s, (30, 22, 18), (ex, ey), 4.2 * K)
            pg.draw.circle(s, (255, 255, 255), (ex + 1.4 * K, ey - 1.4 * K), 1.5 * K)


def draw_stun_stars(s, cx, cy, K, rx=26, ry=10, n=4, phase=0.3):
    for i in range(n):
        a = phase + i * 2 * math.pi / n
        x, y = cx + math.cos(a) * rx * K, cy + math.sin(a) * ry * K
        r = (8 + 1.8 * math.sin(a)) * K
        pg.draw.polygon(s, (255, 210, 60), star_points(x, y, r))
        pg.draw.polygon(s, (255, 245, 170), star_points(x - r * .1, y - r * .1, r * .45))
    pts = [(cx + math.cos(a) * rx * K, cy + math.sin(a) * ry * K) for a in np.linspace(0, 2 * math.pi, 50)]
    pg.draw.lines(s, (255, 250, 220, 120), True, pts, max(1, int(1.2 * K)))


def draw_stump(s, cx, cy, K):
    for i in range(5):   # roots
        a = -.3 + i * 1.3
        x, y = cx + math.cos(a) * 22 * K, cy + math.sin(a) * 22 * K
        pg.draw.ellipse(s, (95, 64, 40), (x - 8 * K, y - 5 * K, 16 * K, 10 * K))
        pg.draw.ellipse(s, (125, 86, 54), (x - 6 * K, y - 5 * K, 11 * K, 7 * K))
    pg.draw.circle(s, (88, 58, 36), (cx + 1.5 * K, cy + 2.5 * K), 24 * K)
    pg.draw.circle(s, (120, 82, 50), (cx, cy), 24 * K)
    pg.draw.circle(s, (228, 190, 132), (cx, cy), 18.5 * K)
    for r in (15, 11, 7):
        pg.draw.circle(s, (196, 152, 98), (cx + .5 * K, cy + .5 * K), r * K, max(1, int(1.4 * K)))
    pg.draw.circle(s, (170, 125, 78), (cx + 1 * K, cy + 1 * K), 2.4 * K)
    pg.draw.line(s, (150, 105, 65), (cx + 3 * K, cy - 2 * K), (cx + 16 * K, cy - 10 * K), max(1, int(1.6 * K)))
    pg.draw.arc(s, (250, 225, 175), (cx - 17 * K, cy - 17 * K, 34 * K, 34 * K), 2.0, 3.2, max(1, int(2 * K)))
    for dx, dy, r in ((-17, 12, 5), (-12, 17, 4), (-20, 6, 3.5)):   # moss
        pg.draw.circle(s, (95, 160, 70), (cx + dx * K, cy + dy * K), r * K)
        pg.draw.circle(s, (135, 195, 95), (cx + (dx - 1) * K, cy + (dy - 1) * K), r * .5 * K)


def draw_burrow(s, cx, cy, K):
    # spilled dirt fan below the entrance
    pg.draw.ellipse(s, (120, 84, 52), (cx - 24 * K, cy + 2 * K, 48 * K, 30 * K))
    pg.draw.ellipse(s, (172, 128, 82), (cx - 22 * K, cy, 44 * K, 27 * K))
    rnd = random.Random(4)
    for _ in range(10):
        x, y = cx + rnd.uniform(-18, 18) * K, cy + rnd.uniform(8, 24) * K
        r = rnd.uniform(1.5, 3) * K
        pg.draw.circle(s, (130, 92, 58), (x + .6 * K, y + .8 * K), r)
        pg.draw.circle(s, (196, 152, 102), (x, y), r)
    # raised rim of the burrow
    pg.draw.ellipse(s, (98, 66, 40), (cx - 27 * K, cy - 22 * K + 3 * K, 54 * K, 40 * K))
    pg.draw.ellipse(s, (150, 106, 66), (cx - 27 * K, cy - 22 * K, 54 * K, 40 * K))
    pg.draw.arc(s, (205, 160, 108), (cx - 25 * K, cy - 21 * K, 50 * K, 36 * K), .6, 2.6, max(1, int(3 * K)))
    # the hole: dark, deeper toward the back (top)
    for i in range(12):
        f = i / 11
        col = lerp((80, 50, 30), (14, 8, 6), f)
        rw, rh = 42 * K * (1 - f * .5), 30 * K * (1 - f * .55)
        pg.draw.ellipse(s, col, (cx - rw / 2, cy - rh / 2 - 1 * K - f * 3 * K, rw, rh))
    # warm glow deep inside
    pg.draw.ellipse(s, (255, 190, 90), (cx - 7 * K, cy - 5 * K, 14 * K, 6 * K))
    pg.draw.ellipse(s, (255, 235, 170), (cx - 4 * K, cy - 4 * K, 8 * K, 3.5 * K))
    for dx, dy, r in ((-24, 2, 3), (23, 4, 2.6), (15, -19, 2.2)):
        pg.draw.circle(s, (120, 122, 112), (cx + dx * K + .6 * K, cy + dy * K + .8 * K), r * K)
        pg.draw.circle(s, (190, 190, 178), (cx + dx * K, cy + dy * K), r * K)
    for dx, dy in ((-27, -10), (26, -8)):
        for a in (-.6, 0, .6):
            pg.draw.line(s, (80, 160, 70), (cx + dx * K, cy + dy * K),
                         (cx + dx * K + math.sin(a) * 7 * K, cy + dy * K - math.cos(a) * 8 * K), max(1, int(2 * K)))
    tiny_flower(s, cx - 20 * K, cy - 18 * K, K * .9, "daisy")
    tiny_flower(s, cx + 24 * K, cy + 16 * K, K * .9, "butter")


def boar_face_icon(size):
    def fn(s, q, cx, cy):
        K = size * q / 60
        for sx in (-1, 1):
            pg.draw.polygon(s, BOAR_D, [(cx + sx * 10 * K, cy - 14 * K), (cx + sx * 27 * K, cy - 26 * K), (cx + sx * 22 * K, cy - 6 * K)])
            pg.draw.polygon(s, (200, 125, 115), [(cx + sx * 13 * K, cy - 14 * K), (cx + sx * 23 * K, cy - 21 * K), (cx + sx * 20 * K, cy - 9 * K)])
        pg.draw.circle(s, BOAR, (cx, cy), 21 * K)
        pg.draw.ellipse(s, BOAR_L, (cx - 13 * K, cy - 19 * K, 26 * K, 12 * K))
        for sx in (-1, 1):
            pg.draw.circle(s, (255, 235, 220), (cx + sx * 8 * K, cy - 5 * K), 4.2 * K)
            pg.draw.circle(s, (210, 40, 40), (cx + sx * 7.5 * K, cy - 4.5 * K), 2.6 * K)
            pg.draw.line(s, (40, 25, 20), (cx + sx * 13 * K, cy - 12 * K), (cx + sx * 3 * K, cy - 8 * K), max(1, int(2.5 * K)))
            pg.draw.polygon(s, (250, 245, 225), [(cx + sx * 9 * K, cy + 10 * K), (cx + sx * 17 * K, cy + 2 * K), (cx + sx * 12 * K, cy + 13 * K)])
        pg.draw.ellipse(s, (215, 150, 140), (cx - 10 * K, cy + 2 * K, 20 * K, 15 * K))
        for sx in (-1, 1):
            pg.draw.ellipse(s, (110, 60, 60), (cx + sx * 4.5 * K - 2.2 * K, cy + 7 * K, 4.4 * K, 5 * K))
    return sprite((size, size), fn)

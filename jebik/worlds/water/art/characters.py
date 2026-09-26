"""Approved art of the water-world characters: snake head, pike, heron, whale.

Pike / heron / whale are ported from the mockup and drawn by ``pike_art``,
``heron_art`` and ``whale_art``. ``K`` is the pixel unit (supersampling x cell scale).
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.common import heart, render_ss


# ---------------------------------------------------------------- snake
SNAKE_SHADOW = (20, 60, 70)
SNAKE_BODY = (90, 120, 40)
SNAKE_BELLY = (150, 180, 60)
SNAKE_SPOT = (230, 200, 70)
SNAKE_HEAD = (110, 140, 45)


@lru_cache(maxsize=8)
def snake_head_sprite(k: float, tongue: bool) -> pg.Surface:
    """Head facing right (+x); rotate at draw time."""
    size = int(64 * k)

    def draw(s: pg.Surface, ss: float) -> None:
        K = k * ss
        hx, hy = s.get_width() / 2, s.get_height() / 2
        dx, dy, px, py = 1.0, 0.0, 0.0, 1.0
        if tongue:
            tip = (hx + 24 * K, hy)
            w = max(1, int(2 * K))
            pg.draw.line(s, (220, 50, 60), (hx + 13 * K, hy), tip, w)
            pg.draw.line(s, (220, 50, 60), tip, (tip[0] + 5 * K, tip[1] + 3 * K), w)
            pg.draw.line(s, (220, 50, 60), tip, (tip[0] + 5 * K, tip[1] - 3 * K), w)
        pg.draw.ellipse(s, SNAKE_HEAD, (hx - 14 * K, hy - 14 * K, 28 * K, 28 * K))
        pg.draw.ellipse(s, (130, 160, 60), (hx - 6 * K, hy - 8 * K, 14 * K, 16 * K))
        for sgn in (-1, 1):
            ex, ey = hx + dx * 4 * K + px * sgn * 7 * K, hy + dy * 4 * K + py * sgn * 7 * K
            pg.draw.circle(s, (255, 235, 90), (ex, ey), 4 * K)
            pg.draw.line(s, (20, 20, 20), (ex - 2 * K, ey), (ex + 2 * K, ey), max(1, int(2 * K)))
        for sgn in (-1, 1):   # nostrils
            pg.draw.circle(s, (60, 80, 30), (hx + 11 * K, hy + sgn * 3 * K), 1.2 * K)
    return render_ss((size, size), draw)


def draw_pike(s: pg.Surface, c: tuple[float, float], K: float, warn: bool = False) -> None:
    cx, cy = c
    if warn:   # bubbles before the attack
        for dx, dy, r in [(-8, 4, 5), (7, -6, 7), (2, 10, 3), (12, 8, 4)]:
            pg.draw.circle(s, (225, 245, 255), (cx + dx * K, cy + dy * K), r * K, max(1, int(1.5 * K)))
        return
    pg.draw.ellipse(s, (40, 90, 110), (cx - 34 * K, cy - 12 * K, 68 * K, 28 * K))
    pg.draw.ellipse(s, (210, 240, 250), (cx - 34 * K, cy - 12 * K, 68 * K, 28 * K), max(1, int(2 * K)))
    body = [(cx + 26 * K, cy), (cx + 6 * K, cy - 11 * K), (cx - 20 * K, cy - 7 * K), (cx - 30 * K, cy),
            (cx - 20 * K, cy + 7 * K), (cx + 6 * K, cy + 11 * K)]
    pg.draw.polygon(s, (95, 125, 70), body)
    pg.draw.polygon(s, (150, 175, 95), [(cx + 20 * K, cy), (cx + 4 * K, cy - 6 * K), (cx - 16 * K, cy - 3 * K),
                                        (cx - 16 * K, cy + 3 * K), (cx + 4 * K, cy + 6 * K)])
    for i in range(4):
        pg.draw.circle(s, (200, 215, 130), (cx - 12 * K + i * 7 * K, cy + (-3 if i % 2 else 3) * K), 2 * K)
    pg.draw.polygon(s, (95, 125, 70), [(cx - 28 * K, cy), (cx - 40 * K, cy - 9 * K), (cx - 40 * K, cy + 9 * K)])
    pg.draw.circle(s, (255, 230, 80), (cx + 14 * K, cy - 4 * K), 3.5 * K)
    pg.draw.circle(s, (0, 0, 0), (cx + 15 * K, cy - 4 * K), 1.8 * K)
    for i in range(4):
        x = cx + 19 * K + i * 2 * K
        pg.draw.polygon(s, (255, 255, 255), [(x, cy + 2 * K), (x + K, cy + 5 * K), (x + 2 * K, cy + 2 * K)])


def draw_heron(s: pg.Surface, c: tuple[float, float], K: float, shadow_only: bool = False,
               shadow: bool = True) -> None:
    cx, cy = c
    if shadow:
        sh = pg.Surface((140 * K, 110 * K), pg.SRCALPHA)
        pg.draw.ellipse(sh, (10, 30, 50, 110), (10 * K, 20 * K, 120 * K, 70 * K))
        s.blit(sh, (cx - 70 * K, cy - 55 * K))
    if shadow_only:
        return
    ox, oy = cx + 18 * K, cy - 40 * K
    for sgn in (-1, 1):
        pts = [(ox, oy - 6 * K), (ox + sgn * 62 * K, oy - 20 * K), (ox + sgn * 70 * K, oy - 6 * K),
               (ox + sgn * 52 * K, oy + 4 * K), (ox + sgn * 30 * K, oy + 10 * K), (ox, oy + 8 * K)]
        pg.draw.polygon(s, (165, 175, 190), pts)
        pg.draw.polygon(s, (120, 130, 150), [(ox + sgn * 52 * K, oy + 4 * K), (ox + sgn * 70 * K, oy - 6 * K),
                                             (ox + sgn * 66 * K, oy + 6 * K)])
        for i in range(3):
            pg.draw.line(s, (60, 70, 90), (ox + sgn * (56 + i * 5) * K, oy - 8 * K + i * 3 * K),
                         (ox + sgn * (64 + i * 3) * K, oy + i * 4 * K), max(1, int(2 * K)))
    pg.draw.ellipse(s, (225, 230, 238), (ox - 10 * K, oy - 14 * K, 20 * K, 40 * K))
    pg.draw.polygon(s, (225, 230, 238), [(ox - 4 * K, oy + 22 * K), (ox + 4 * K, oy + 22 * K), (ox, oy + 34 * K)])
    pg.draw.line(s, (225, 230, 238), (ox, oy - 12 * K), (ox, oy - 30 * K), max(1, int(7 * K)))
    pg.draw.circle(s, (240, 242, 248), (ox, oy - 32 * K), 7 * K)
    pg.draw.line(s, (30, 30, 40), (ox - 3 * K, oy - 36 * K), (ox + 8 * K, oy - 44 * K), max(1, int(2 * K)))
    pg.draw.polygon(s, (240, 190, 60), [(ox - 4 * K, oy - 35 * K), (ox + 4 * K, oy - 35 * K), (ox, oy - 56 * K)])
    pg.draw.circle(s, (20, 20, 20), (ox + 3 * K, oy - 33 * K), 1.8 * K)


def draw_whale(s: pg.Surface, rect, K: float, surfaced: bool = True, hp: int = 3,
               hearts: bool = True) -> None:
    """The boss (final mockup version): silhouette under water or surfaced."""
    r = pg.Rect(rect)
    cx, cy = r.center
    L, Wd = r.w / 2, r.h / 2

    def body(dx=0.0, dy=0.0, sc=1.0):
        pts = []
        for i in range(41):
            t = i / 40 * 2 * math.pi
            x = math.cos(t)
            w = Wd * sc * (1 - ((x + 1) / 2) ** 1.6 * .75)
            pts.append((cx - L * .15 + dx + x * L * .85 * sc, cy + dy + math.sin(t) * w))
        return pts
    if not surfaced:
        sh = pg.Surface(s.get_size(), pg.SRCALPHA)
        pg.draw.polygon(sh, (8, 25, 55, 130), body())
        tx = cx + L * .7
        pg.draw.polygon(sh, (8, 25, 55, 130), [(tx, cy), (tx + L * .35, cy - Wd * .7), (tx + L * .25, cy),
                                               (tx + L * .35, cy + Wd * .7)])
        s.blit(sh, (0, 0))
        return
    ring = [(x + (x - cx) * .06, y + (y - cy) * .18) for x, y in body()]
    pg.draw.polygon(s, (215, 242, 250), ring)
    pg.draw.polygon(s, (40, 70, 120), body(4 * K, 6 * K))
    for sgn in (-1, 1):
        pg.draw.polygon(s, (55, 90, 145), [(cx - L * .35, cy + sgn * Wd * .6), (cx - L * .05, cy + sgn * Wd * 1.35),
                                           (cx + L * .08, cy + sgn * Wd * 1.25), (cx - L * .1, cy + sgn * Wd * .6)])
    tx = cx + L * .62
    pg.draw.polygon(s, (55, 90, 145), [(tx, cy), (tx + L * .42, cy - Wd * .95), (tx + L * .30, cy),
                                       (tx + L * .42, cy + Wd * .95)])
    pg.draw.polygon(s, (70, 110, 170), body())
    pg.draw.polygon(s, (100, 145, 200), body(-L * .08, -Wd * .12, .62))
    for i in range(7):
        pg.draw.circle(s, (160, 195, 230), (cx + L * (-.1 + i * .1), cy + Wd * .25 * math.sin(i * 1.7)),
                       (3 + i % 2) * K)
    for sgn in (-1, 1):
        ex, ey = cx - L * .72, cy + sgn * Wd * .62
        pg.draw.circle(s, (255, 255, 255), (ex, ey), 6 * K)
        pg.draw.circle(s, (20, 20, 30), (ex - 1.5 * K, ey), 3.5 * K)
    bh = (cx - L * .45, cy)
    pg.draw.ellipse(s, (30, 50, 90), (bh[0] - 7 * K, bh[1] - 4 * K, 14 * K, 8 * K))
    for a in range(-80, 81, 20):
        ang = math.radians(a + 180)
        for d in range(4):
            pg.draw.circle(s, (225, 248, 255), (bh[0] + math.cos(ang) * (12 + d * 11) * K,
                                                bh[1] + math.sin(ang) * (12 + d * 11) * K * .7), max(1, (5 - d)) * K)
    for i in range(3 if hearts else 0):
        heart(s, int(cx - 45 * K + i * 34 * K), int(r.top - 30 * K), (230, 60, 70) if i < hp else (70, 70, 70), .8 * K)

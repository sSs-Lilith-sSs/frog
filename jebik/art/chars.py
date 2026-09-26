"""Shared characters (frog, flies), ported from the approved ``chars.py``.

Each ``draw_*`` works in a pixel unit ``K`` (= supersampling x cell scale);
the ``*_sprite`` helpers render them once into cached, downscaled sprites.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from .common import render_ss

FROG_G = (95, 200, 80)
FROG_D = (60, 150, 55)
FROG_L = (175, 235, 140)
EYE_DARK = (25, 25, 25)


# ---------------------------------------------------------------- frog (top-down)
def draw_frog(sur: pg.Surface, o: tuple[float, float], K: float, mode: str = "idle") -> None:
    """Top-down frog facing up. Modes: idle, blink, jump, happy, sad."""
    stretch = 1.25 if mode == "jump" else 1
    g, d, l = FROG_G, FROG_D, FROG_L
    for sx in (-1, 1):  # back legs + feet + front legs
        pg.draw.ellipse(sur, d, (o[0] + sx * 20 * K - 9 * K, o[1] + 6 * K * stretch,
                                 18 * K, 22 * K * stretch))
        pg.draw.circle(sur, d, (o[0] + sx * 26 * K, o[1] + 26 * K * stretch), 6 * K)
        pg.draw.ellipse(sur, d, (o[0] + sx * 17 * K - 5 * K, o[1] - 16 * K, 10 * K, 14 * K))
    pg.draw.ellipse(sur, g, (o[0] - 20 * K, o[1] - 22 * K, 40 * K, 44 * K))
    pg.draw.ellipse(sur, l, (o[0] - 11 * K, o[1] - 4 * K, 22 * K, 20 * K))
    lw = max(1, int(1.5 * K))
    for sx in (-1, 1):
        ex, ey = o[0] + sx * 11 * K, o[1] - 18 * K
        pg.draw.circle(sur, g, (ex, ey), 10 * K)
        if mode in ("blink", "happy"):
            rect = (ex - 6 * K, ey - 4 * K - (2 * K if mode == "happy" else 0), 12 * K, 9 * K)
            a0, a1 = (0.3, math.pi - 0.3) if mode == "happy" else (math.pi + .3, 2 * math.pi - .3)
            pg.draw.arc(sur, (30, 70, 30), rect, a0, a1, max(1, int(2 * K)))
        else:
            pg.draw.circle(sur, (255, 255, 255), (ex, ey - 1 * K), 7.5 * K)
            pg.draw.circle(sur, EYE_DARK, (ex, ey - 3 * K), 4 * K)
            pg.draw.circle(sur, (255, 255, 255), (ex + 1.5 * K, ey - 4.5 * K), 1.6 * K)
            if mode == "sad":   # droopy lids
                pg.draw.ellipse(sur, g, (ex - 9 * K, ey - 11 * K, 18 * K, 9 * K))
        pg.draw.circle(sur, (255, 150, 170), (o[0] + sx * 14 * K, o[1] - 6 * K), 3.5 * K)
    mouth = (o[0] - 7 * K, o[1] - 14 * K, 14 * K, 9 * K)
    if mode == "sad":
        pg.draw.arc(sur, (40, 110, 40), (o[0] - 6 * K, o[1] - 10 * K, 12 * K, 7 * K),
                    .4, math.pi - .4, lw)
    else:
        pg.draw.arc(sur, (40, 110, 40), mouth, math.pi + .4, 2 * math.pi - .4, lw)


@lru_cache(maxsize=64)
def frog_sprite(k: float, face: int, mode: str = "idle") -> pg.Surface:
    """Frog sprite (120k x 120k), rotated to ``face`` (0 up, 1 right, ...)."""
    size = int(round(120 * k))

    def draw(s: pg.Surface, ss: float) -> None:
        draw_frog(s, (s.get_width() / 2, s.get_height() / 2), k * ss, mode)
    spr = render_ss((size, size), draw)
    return pg.transform.rotate(spr, -face * 90) if face else spr


@lru_cache(maxsize=8)
def frog_shadow(k: float) -> pg.Surface:
    w, h = int(46 * k), int(40 * k)
    return render_ss((w, h), lambda s, ss: pg.draw.ellipse(
        s, (20, 60, 70, 90), (0, 0, w * ss, h * ss)))


# ---------------------------------------------------------------- frog (front, menu)
def draw_frog_front(s: pg.Surface, c: tuple[float, float], k: float) -> None:
    """Front-facing frog used on the menu pad and the profile pill."""
    cx, cy = c

    def K(v: float) -> float:
        return v * k
    green, dark, belly = (100, 210, 80), (60, 160, 50), (170, 235, 140)
    pg.draw.ellipse(s, dark, (cx - K(28), cy + K(2), K(20), K(16)))
    pg.draw.ellipse(s, dark, (cx + K(8), cy + K(2), K(20), K(16)))
    pg.draw.ellipse(s, green, (cx - K(22), cy - K(18), K(44), K(36)))
    pg.draw.ellipse(s, belly, (cx - K(12), cy - K(4), K(24), K(18)))
    for ex in (-11, 11):
        pg.draw.circle(s, green, (cx + K(ex), cy - K(17)), K(10))
        pg.draw.circle(s, (255, 255, 255), (cx + K(ex), cy - K(18)), K(8))
        pg.draw.circle(s, (20, 20, 20), (cx + K(ex + 2), cy - K(18)), K(4))
        pg.draw.circle(s, (255, 255, 255), (cx + K(ex + 3.2), cy - K(19.5)), K(1.3))
    pg.draw.circle(s, (255, 140, 160), (cx - K(14), cy - K(4)), K(4))
    pg.draw.circle(s, (255, 140, 160), (cx + K(14), cy - K(4)), K(4))
    pg.draw.arc(s, (30, 90, 30), (cx - K(8), cy - K(10), K(16), K(10)),
                math.pi + .3, 2 * math.pi - .3, max(1, int(K(2))))


def draw_frog_front_blink(s: pg.Surface, c: tuple[float, float], k: float) -> None:
    draw_frog_front(s, c, k)
    cx, cy = c
    for ex in (-11, 11):
        pg.draw.circle(s, (100, 210, 80), (cx + ex * k, cy - 17 * k), 9 * k)
        pg.draw.arc(s, (30, 80, 30), (cx + (ex - 6) * k, cy - 22 * k, 12 * k, 8 * k),
                    math.pi + .3, 2 * math.pi - .3, max(1, int(2 * k)))


@lru_cache(maxsize=16)
def frog_front_sprite(k: float, blink: bool = False) -> pg.Surface:
    size = (int(62 * k), int(50 * k))

    def draw(s: pg.Surface, ss: float) -> None:
        fn = draw_frog_front_blink if blink else draw_frog_front
        fn(s, (size[0] * ss / 2, size[1] * ss * 0.56), k * ss)
    return render_ss(size, draw)


# ---------------------------------------------------------------- flies
def draw_fly(s: pg.Surface, c: tuple[float, float], K: float, kind: str = "fly",
             wing_up: bool = False) -> None:
    cx, cy = c
    if kind == "dragon":
        wing = (190, 235, 255, 215) if not wing_up else (215, 245, 255, 150)
        spread = 1.0 if not wing_up else 0.72
        for sy in (-1, 1):
            for sx in (-1, 1):
                ww = 20 * K * spread
                x0 = cx + 2 * K if sx > 0 else cx - 2 * K - ww
                pg.draw.ellipse(s, wing, (x0, cy + sy * 3 * K - (6 * K if sy < 0 else 0) - 2 * K,
                                          ww, 6 * K))
        pg.draw.line(s, (40, 120, 200), (cx, cy - 8 * K), (cx, cy + 18 * K), max(1, int(4 * K)))
        pg.draw.circle(s, (40, 160, 220), (cx, cy - 9 * K), 5 * K)
        pg.draw.circle(s, (20, 60, 110), (cx - 2.2 * K, cy - 11 * K), 1.6 * K)
        pg.draw.circle(s, (20, 60, 110), (cx + 2.2 * K, cy - 11 * K), 1.6 * K)
        return
    wing = (255, 240, 170, 235) if kind == "gold" else (220, 238, 255, 230)
    if wing_up:
        wing = (*wing[:3], 140)
        pg.draw.ellipse(s, wing, (cx - 11 * K, cy - 13 * K, 10 * K, 7 * K))
        pg.draw.ellipse(s, wing, (cx + 1 * K, cy - 13 * K, 10 * K, 7 * K))
    else:
        pg.draw.ellipse(s, wing, (cx - 12 * K, cy - 10 * K, 11 * K, 8 * K))
        pg.draw.ellipse(s, wing, (cx + 1 * K, cy - 10 * K, 11 * K, 8 * K))
    body = {"fly": (40, 40, 45), "gold": (235, 185, 25), "firefly": (90, 70, 40)}[kind]
    pg.draw.ellipse(s, body, (cx - 6 * K, cy - 6 * K, 12 * K, 14 * K))
    if kind == "firefly":
        pg.draw.ellipse(s, (255, 245, 120), (cx - 5 * K, cy + 1 * K, 10 * K, 8 * K))
    eye = (200, 40, 40) if kind == "fly" else (60, 40, 20)
    pg.draw.circle(s, eye, (cx - 3 * K, cy - 5 * K), 2.2 * K)
    pg.draw.circle(s, eye, (cx + 3 * K, cy - 5 * K), 2.2 * K)
    if kind == "gold":
        for a in range(0, 360, 45):
            r = math.radians(a)
            pg.draw.line(s, (255, 230, 90), (cx + 13 * K * math.cos(r), cy + 13 * K * math.sin(r)),
                         (cx + 18 * K * math.cos(r), cy + 18 * K * math.sin(r)), max(1, int(2 * K)))


@lru_cache(maxsize=32)
def fly_sprite(k: float, kind: str, wing_up: bool = False) -> pg.Surface:
    size = int(round((56 if kind == "dragon" else 40) * k))

    def draw(s: pg.Surface, ss: float) -> None:
        cy = s.get_height() / 2 - (4 * k * ss if kind == "dragon" else 0)
        draw_fly(s, (s.get_width() / 2, cy + (0 if kind == "dragon" else 2 * k * ss)),
                 k * ss, kind, wing_up)
    return render_ss((size, size), draw)


@lru_cache(maxsize=8)
def small_shadow(w: int, h: int, alpha: int = 70) -> pg.Surface:
    return render_ss((w, h), lambda s, ss: pg.draw.ellipse(
        s, (15, 50, 60, alpha), (0, 0, w * ss, h * ss)))

"""Cached character sprites of the earth world (all drawn facing RIGHT)."""
from __future__ import annotations

from functools import lru_cache

import pygame as pg

from ....art.common import heart_sprite, render_ss
from .boar_draw import boar_face_icon, draw_boar, draw_stun_stars
from .critters import (draw_fox, draw_hedgehog, draw_hedgehog_ball, draw_mole_out, draw_mound,
                       draw_tremor, dust, motion_lines)
from .paint import sprite

SPIN_FRAMES = 12


@lru_cache(maxsize=16)
def hedgehog(k: float, step: int = 0) -> pg.Surface:
    return sprite((80 * k, 80 * k), lambda s, q, cx, cy: draw_hedgehog(s, cx - 2 * k * q, cy, k * q, step))


@lru_cache(maxsize=64)
def ball(k: float, frame: int) -> pg.Surface:
    spin = frame / SPIN_FRAMES * 6.2832 / 3          # the swirl repeats every third of a turn
    return sprite((56 * k, 56 * k), lambda s, q, cx, cy: draw_hedgehog_ball(s, cx, cy, k * q, spin))


@lru_cache(maxsize=16)
def roll_trail(k: float) -> pg.Surface:
    """Motion lines + dust behind a ball rolling RIGHT (ball centre at the sprite's right third)."""
    w, h = int(120 * k), int(64 * k)

    def fn(s, q, cx, cy):
        bx = w * q * .72
        dust(s, bx - 22 * k * q, cy + 8 * k * q, k * q, n=4, dirx=-1, seed=3, spread=6, scale=.8)
        motion_lines(s, bx, cy, k * q, dirx=-1, length=26, n=3, spread=11, start=24)
    return sprite((w, h), fn)


@lru_cache(maxsize=16)
def fox(k: float, pose: str = "run", sc: float = 1.0) -> pg.Surface:
    return sprite((130 * k * sc, 60 * k * sc),
                  lambda s, q, cx, cy: draw_fox(s, cx + 6 * k * q * sc, cy, k * q, pose, sc))


@lru_cache(maxsize=16)
def mound(k: float, trail: int = 3) -> pg.Surface:
    """Mound heading RIGHT; its centre sits 30 k right of the sprite centre."""
    return sprite((130 * k, 50 * k), lambda s, q, cx, cy: draw_mound(s, cx + 30 * k * q, cy, k * q, 1, trail))


@lru_cache(maxsize=8)
def mole(k: float) -> pg.Surface:
    return sprite((80 * k, 80 * k), lambda s, q, cx, cy: draw_mole_out(s, cx, cy, k * q))


@lru_cache(maxsize=8)
def tremor(k: float, cs: int) -> pg.Surface:
    return sprite((cs, cs), lambda s, q, cx, cy: draw_tremor(s, cx, cy, k * q, cs * q))


@lru_cache(maxsize=16)
def boar(k: float, mode: str = "idle") -> pg.Surface:
    return sprite((152 * k, 104 * k), lambda s, q, cx, cy: draw_boar(s, cx, cy, k * q, mode))


@lru_cache(maxsize=48)
def stars(k: float, frame: int) -> pg.Surface:
    return sprite((80 * k, 40 * k), lambda s, q, cx, cy: draw_stun_stars(
        s, cx, cy, k * q, rx=26, ry=10, n=4, phase=frame / 16 * 6.2832 / 4))


@lru_cache(maxsize=8)
def boar_face(size: int) -> pg.Surface:
    return boar_face_icon(size)


@lru_cache(maxsize=8)
def hp_heart(size: int, full: bool) -> pg.Surface:
    return heart_sprite(size, (235, 120, 50) if full else (80, 80, 80))


@lru_cache(maxsize=16)
def shadow(w: int, h: int, alpha: int = 75) -> pg.Surface:
    return render_ss((max(2, w), max(2, h)), lambda s, q: pg.draw.ellipse(
        s, (25, 45, 20, alpha), (0, 0, max(2, w) * q, max(2, h) * q)), ss=3)


def oriented(img: pg.Surface, facing: tuple[int, int]) -> pg.Surface:
    """Turn a RIGHT-facing top-down sprite: flip for left, rotate for up/down."""
    return _oriented(img, facing)


_ORI: dict[tuple[int, tuple[int, int]], pg.Surface] = {}


def _oriented(img: pg.Surface, facing: tuple[int, int]) -> pg.Surface:
    if facing[0] >= 0 and facing[1] == 0:
        return img
    key = (id(img), facing)
    out = _ORI.get(key)
    if out is None:
        if len(_ORI) > 256:
            _ORI.clear()
        if facing[0] < 0:
            out = pg.transform.flip(img, True, False)
        else:
            out = pg.transform.rotate(img, -90 if facing[1] > 0 else 90)
        _ORI[key] = out
    return out

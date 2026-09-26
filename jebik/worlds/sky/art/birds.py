"""Swallow, hawk and crow: mockup shapes baked into cached sprites + renderers."""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.common import render_ss
from ....art.enemy_art import EnemyArt, register_enemy_art
from ....game.grid import DIRS
from .paint import T, dashed_line, glow, red_arrow_sprite

SHADOW = (60, 30, 90, 70)
RED = (235, 60, 70)


# ------------------------------------------------------------------ shapes
def _swallow_shape(t: T, body, light, dark, flap: float, silhouette: bool = False) -> None:
    sp = 1 - flap * .25
    for sx in (-1, 1):
        wing = [(sx * 4, -6), (sx * 20 * sp, -9), (sx * 40 * sp, -4), (sx * 50 * sp, 6),
                (sx * 38 * sp, 3), (sx * 22 * sp, 5), (sx * 6, 6)]
        t.poly(dark if not silhouette else body, [(x, y + 1.5) for x, y in wing])
        t.poly(body, wing)
        if not silhouette:
            t.poly(light, [(sx * 6, -6), (sx * 20 * sp, -9), (sx * 36 * sp, -5), (sx * 20 * sp, -3), (sx * 6, -1)])
    t.poly(body, [(-5, 12), (-12, 38), (-7, 37), (-2, 22), (2, 22), (7, 37), (12, 38), (5, 12)])
    t.ell(body, 0, 2, 8, 17)
    if silhouette:
        t.circ(body, 0, -13, 9)
        return
    t.ell(light, 0, 4, 4, 10)
    t.circ(body, 0, -13, 9.5)
    t.ell((215, 75, 60), 0, -19, 5.5, 3.5)                       # rusty face patch
    t.poly((245, 200, 70), [(-2.2, -22), (2.2, -22), (0, -27)])  # beak
    for sx in (-1, 1):
        t.circ((255, 255, 255), sx * 4.8, -15, 3.8)
        t.circ((20, 20, 30), sx * 5.3, -16, 2.3)
        t.circ((255, 255, 255), sx * 5.9, -16.9, .9)
    t.ell((255, 255, 255), -2.5, -9, 2.2, 1.2)


def _speed_lines(t: T, n=4, length=46, start=40, col=(255, 255, 255, 170), w=2.2) -> None:
    for i in range(n):
        x = (i - (n - 1) / 2) * 9
        L = length * (1 - abs(x) / 60)
        t.line(col, (x, start + i % 2 * 5), (x, start + L + i % 2 * 5), w)


def _hawk_shape(t: T, silhouette=None) -> None:
    br, brd, brl, cream = (150, 95, 55), (100, 60, 35), (190, 130, 75), (240, 220, 180)
    if silhouette:
        br = brd = brl = cream = silhouette
    for sx in (-1, 1):
        wing = [(sx * 6, -10), (sx * 30, -16), (sx * 52, -14), (sx * 66, -8), (sx * 70, 0), (sx * 64, 4),
                (sx * 58, 10), (sx * 50, 14), (sx * 30, 14), (sx * 8, 10)]
        t.poly(brd, [(x, y + 2) for x, y in wing])
        t.poly(br, wing)
        for i in range(4):                                       # finger feathers
            ang = -.5 + i * .38
            t.ell(brd, sx * (66 + 6 * math.cos(ang)), -2 + 9 * math.sin(ang) + 2, 7, 2.6, rot=sx * ang)
        if not silhouette:
            t.poly(brl, [(sx * 8, -10), (sx * 30, -16), (sx * 50, -14), (sx * 34, -8), (sx * 10, -4)])
            for i in range(3):
                x0 = sx * (20 + i * 12)
                t.line(brd, (x0, -8 + i), (x0 + sx * 4, 10), 2.2)
    t.poly(brd, [(-7, 14), (-14, 36), (-6, 40), (0, 41), (6, 40), (14, 36), (7, 14)])
    if not silhouette:
        t.poly(br, [(-6, 14), (-11, 34), (0, 37), (11, 34), (6, 14)])
        for y in (24, 31):
            t.line(brd, (-9, y), (9, y), 1.8)
    t.ell(br, 0, 2, 11, 18)
    if silhouette:
        t.circ(br, 0, -16, 11)
        return
    t.ell(cream, 0, 4, 6.5, 11)
    for dx, dy in [(-2.5, 0), (2.5, 3), (-2, 7), (2, 9)]:
        t.ell(brl, dx, dy, 1.3, 1.8)
    t.circ(br, 0, -16, 11.5)
    t.ell(cream, 0, -19, 7, 5)
    for sx in (-1, 1):
        t.circ((255, 215, 70), sx * 5.2, -19, 4.2)
        t.circ((25, 20, 20), sx * 5.2, -19.5, 2.5)
        t.circ((255, 255, 255), sx * 5.8, -20.4, .9)
        t.line((70, 40, 25), (sx * 1.5, -23.5), (sx * 9, -21.5), 1.9)
    t.poly((250, 200, 60), [(-3, -24), (3, -24), (0, -31)])
    t.poly((60, 50, 50), [(-1.3, -28.5), (1.3, -28.5), (0, -31.2)])


def _crow_shape(t: T, beak_open=False, peck=False, flying=False) -> None:
    body, sheen, dark = (48, 50, 78), (105, 115, 165), (30, 30, 48)
    fy = -7 if peck else 0
    if flying:
        for sx in (-1, 1):
            wing = [(sx * 6, -6), (sx * 26, -12), (sx * 42, -8), (sx * 48, 0), (sx * 40, 6), (sx * 24, 8), (sx * 8, 8)]
            t.poly(dark, [(x, y + 2) for x, y in wing])
            t.poly(body, wing)
            t.poly(sheen, [(sx * 10, -6), (sx * 26, -11), (sx * 36, -8), (sx * 22, -5)])
    else:
        t.ell(SHADOW, 3, 8, 17, 19)
    for a in (-.35, 0, .35):
        t.ell(dark, math.sin(a) * 9, 17 + math.cos(a) * 4, 4.2, 8, rot=a)
    t.ell(body, 0, 4 + fy * .3, 15, 15)
    if not flying:
        for sx in (-1, 1):
            t.ell(dark, sx * 10, 7, 7, 13, rot=-sx * .3)
            for i in range(3):
                t.ell(dark, sx * (10 + i * 1.5), 16 + i * 1.5, 2.6, 4, rot=-sx * .3)
            t.ell(sheen, sx * 9, 2, 2.4, 6.5, rot=-sx * .3)
    hy = -12 + fy
    t.circ(body, 0, hy, 12.5)
    t.ell(sheen, -5, hy - 5, 3.6, 2.2, rot=-.5)
    t.ell((70, 72, 105), 0, hy + 6, 7, 4)
    bk, bkd = (95, 95, 110), (60, 60, 72)
    if beak_open:
        t.poly(bkd, [(-4.5, hy - 9), (-1, hy - 10), (-7, hy - 20)])
        t.poly(bk, [(1, hy - 10), (4.5, hy - 9), (7, hy - 20)])
        t.poly((215, 80, 100), [(-1.8, hy - 10), (1.8, hy - 10), (0, hy - 16)])
    else:
        t.poly(bk, [(-4.5, hy - 9), (4.5, hy - 9), (0, hy - 19)])
        t.poly(bkd, [(0, hy - 9), (4.5, hy - 9), (0, hy - 19)])
    for sx in (-1, 1):
        t.circ((255, 255, 255), sx * 5.4, hy - 3, 4.2)
        t.circ((15, 15, 25), sx * 5.6, hy - 3.6, 2.7)
        t.circ((255, 255, 255), sx * 6.4, hy - 4.6, 1.1)
    if not flying:
        for sx in (-1, 1):
            for d in (-2.2, 0, 2.2):
                t.line((80, 70, 80), (sx * 5, 16), (sx * 5 + d, 21), 1.4)


# ------------------------------------------------------------------ cached sprites (facing up)
@lru_cache(maxsize=16)
def swallow_sprite(k: float, flap: int, silhouette: bool = False, lines: bool = False) -> pg.Surface:
    K = k * .8
    size = int(200 * K)

    def draw(s: pg.Surface, ss: float) -> None:
        t = T(s, size * ss / 2, size * ss / 2, K * ss)
        if lines:
            _speed_lines(t)
        if silhouette:
            _swallow_shape(t, SHADOW, SHADOW, SHADOW, flap / 2, silhouette=True)
        else:
            _swallow_shape(t, (40, 50, 110), (70, 90, 165), (25, 30, 70), flap / 2)
    return render_ss((size, size), draw, ss=3)


@lru_cache(maxsize=8)
def hawk_sprite(k: float, silhouette: bool = False, lines: bool = False) -> pg.Surface:
    K = k * .95
    size = int(170 * K)

    def draw(s: pg.Surface, ss: float) -> None:
        t = T(s, size * ss / 2, size * ss / 2, K * ss * (.92 if silhouette else 1))
        if lines:
            _speed_lines(t, n=5, length=50, start=44)
        _hawk_shape(t, silhouette=SHADOW if silhouette else None)
    return render_ss((size, size), draw, ss=3)


@lru_cache(maxsize=16)
def crow_sprite(k: float, mode: str) -> pg.Surface:
    K = k * .95
    size = int(110 * K)

    def draw(s: pg.Surface, ss: float) -> None:
        t = T(s, size * ss / 2, size * ss / 2, K * ss)
        _crow_shape(t, beak_open=mode == "caw", peck=mode == "peck", flying=mode == "fly")
    return render_ss((size, size), draw, ss=3)


def rotated(cache: dict, img: pg.Surface, key, heading: float, step: int = 10) -> pg.Surface:
    """``img`` faces up; rotate it to screen heading (radians, 0 = right)."""
    ang = int(round((-90 - math.degrees(heading)) / step) * step) % 360
    ck = (key, ang)
    out = cache.get(ck)
    if out is None:
        out = cache[ck] = pg.transform.rotozoom(img, ang, 1.0) if ang else img
    return out


def blit_c(surf: pg.Surface, img: pg.Surface, x: float, y: float) -> None:
    surf.blit(img, img.get_rect(center=(round(x), round(y))))


GRID_HEADING = {0: -math.pi / 2, 1: 0.0, 2: math.pi / 2, 3: math.pi}


# ------------------------------------------------------------------ renderers
@register_enemy_art("swallow")
class SwallowArt(EnemyArt):
    def __init__(self, view):
        super().__init__(view)
        self.rot: dict = {}
        self.band: dict = {}

    def draw(self, surf, enemy, off) -> None:
        if not enemy.flying:
            return
        k, h = self.k, GRID_HEADING[enemy.direction]
        flap = int(abs(math.sin(enemy.anim * 16)) * 2.99)
        x, y = self.px(enemy.pos, off)
        sh = rotated(self.rot, swallow_sprite(k, flap, True), ("s", flap), h)
        blit_c(surf, sh, x + 8 * k * .8, y + 14 * k * .8)
        img = rotated(self.rot, swallow_sprite(k, flap, False, True), ("b", flap), h)
        blit_c(surf, img, x, y)

    def draw_telegraph(self, surf, enemy, tg, off) -> bool:
        v, cs, k = self.view, self.cs, self.k
        blink = .5 + .5 * math.sin(v.t * (10 + 14 * tg.progress))
        if tg.style == "line" and tg.cells:
            (x0, y0), (x1, y1) = v.to_px(tg.cells[0]), v.to_px(tg.cells[-1])
            horiz = tg.direction in (1, 3)
            size = (int(x1 - x0 + cs), cs) if horiz else (cs, int(y1 - y0 + cs))
            band = self.band.get(size)
            if band is None:
                band = self.band[size] = pg.Surface(size, pg.SRCALPHA)
                band.fill((255, 60, 80, 255))
            band.set_alpha(int(40 + 45 * blink))
            surf.blit(band, (round(x0 - cs / 2 + off[0]), round(y0 - cs / 2 + off[1])))
            a, b = (x0 - cs * .3 + off[0], y0 + off[1]), (x1 + cs * .3 + off[0], y1 + off[1])
            if not horiz:
                a, b = (x0 + off[0], y0 - cs * .3 + off[1]), (x1 + off[0], y1 + cs * .3 + off[1])
            if tg.direction in (0, 3):
                a, b = b, a
            dashed_line(surf, a, b, RED, max(2, int(3 * k)), 20 * k, 12 * k, phase=-v.t * 2)
            return True
        if tg.style == "arrow" and tg.cells:
            x, y = v.to_px(tg.cells[0])
            dx, dy = DIRS[tg.direction or 0]
            x, y = x + off[0] + dx * cs * .1, y + off[1] + dy * cs * .1
            glow(surf, x, y, 34 * k * (0.8 + .3 * blink), (255, 80, 80), 130)
            blit_c(surf, red_arrow_sprite(int(62 * k), tg.direction or 0), x, y)
            return True
        return False


@register_enemy_art("hawk")
class HawkArt(EnemyArt):
    def __init__(self, view):
        super().__init__(view)
        self.rot: dict = {}

    def draw(self, surf, enemy, off) -> None:
        k = self.k
        x, y = self.px(enemy.pos, off)
        dash = enemy.state == "dash"
        bob = 0 if dash else math.sin(enemy.anim * 2.4) * 2 * k
        sh = rotated(self.rot, hawk_sprite(k, True), "s", enemy.heading)
        blit_c(surf, sh, x + 10 * k * .95, y + 22 * k * .95)
        img = rotated(self.rot, hawk_sprite(k, False, dash), ("b", dash), enemy.heading)
        if enemy.state == "windup":                  # wings pulled in, shiver
            x += math.sin(self.view.t * 60) * 1.5 * k
        blit_c(surf, img, x, y + bob)

    def draw_telegraph(self, surf, enemy, tg, off) -> bool:
        v, k = self.view, self.k
        p = tg.progress
        lay_col = (255, 120, 60)
        for c in tg.cells:
            if not (0 <= c[0] < v.level.width and 0 <= c[1] < v.level.height):
                continue
            x, y = v.to_px(c)
            r = pg.Rect(0, 0, self.cs - 8, self.cs - 8)
            r.center = (round(x + off[0]), round(y + off[1]))
            lay = pg.Surface(r.size, pg.SRCALPHA)
            pg.draw.rect(lay, (*RED, int(50 + 110 * p)), lay.get_rect(), border_radius=int(self.cs * .2))
            surf.blit(lay, r)
        a = self.px(enemy.dash_from, off)
        b = self.px(enemy.dash_to, off)
        pg.draw.line(surf, lay_col, a, b, max(3, int(5 * k)))
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        tip = [(b[0] + math.cos(ang) * 12 * k, b[1] + math.sin(ang) * 12 * k),
               (b[0] + math.cos(ang + 2.4) * 12 * k, b[1] + math.sin(ang + 2.4) * 12 * k),
               (b[0] + math.cos(ang - 2.4) * 12 * k, b[1] + math.sin(ang - 2.4) * 12 * k)]
        pg.draw.polygon(surf, lay_col, tip)
        return True


@register_enemy_art("crow")
class CrowArt(EnemyArt):
    def __init__(self, view):
        super().__init__(view)
        self.rot: dict = {}

    def draw(self, surf, enemy, off) -> None:
        k = self.k
        x, y = self.px(enemy.pos, off)
        st = enemy.state
        if st == "fly":
            flap = math.sin(enemy.anim * 14)
            sh = self._shadow()
            blit_c(surf, sh, x + 8 * k, y + 20 * k)
            img = rotated(self.rot, crow_sprite(k, "fly"), "f", enemy.heading, 15)
            if flap > 0.3:
                img = pg.transform.smoothscale(img, (max(1, int(img.get_width() * .9)), img.get_height()))
            blit_c(surf, img, x, y - 10 * k)
            return
        mode = {"caw": "caw", "peck": "peck"}.get(st, "sit")
        heading = math.pi / 2
        if st == "peck":
            heading = enemy.heading
        hop = abs(math.sin(enemy.anim * 3)) * 2 * k if st == "sit" else 0
        if st == "eat":
            hop = abs(math.sin(enemy.anim * 18)) * 3 * k
        img = rotated(self.rot, crow_sprite(k, mode), mode, heading, 90)
        blit_c(surf, img, x, y - hop)

    def _shadow(self) -> pg.Surface:
        if not hasattr(self, "_sh"):
            w = int(34 * self.k)
            self._sh = pg.Surface((w, int(w * .6)), pg.SRCALPHA)
            pg.draw.ellipse(self._sh, SHADOW, self._sh.get_rect())
        return self._sh

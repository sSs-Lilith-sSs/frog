"""Drawing primitives ported from the approved «Небо» mockups.

Everything draws on a big (supersampled) surface in its pixel units; callers
render once through ``render_ss`` and cache the result. No numpy here except
through the cached ``glow_sprite`` helper (build time only).
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame as pg

from ....art.common import lerp, render_ss
from ....art.glow import glow_sprite

# ------------------------------------------------------------------ palette B
PAL_B = ((255, 250, 246), (255, 220, 232), (215, 160, 200), (255, 255, 255))
PAL_MELT = ((255, 255, 255), (250, 232, 242), (225, 190, 215), (255, 255, 255))
CLOUD_SH = (150, 95, 160)
ABYSS_TOP, ABYSS_BOT = (245, 170, 155), (115, 85, 175)
GAP_DECOR = (200, 130, 160)
FAR_BIRD = (80, 50, 110)
SKY_STOPS = [(0.0, (255, 200, 160)), (0.28, (248, 168, 168)), (0.62, (185, 120, 190)), (1.0, (98, 72, 162))]
FRAME, FRAME_L, FRAME_D = (92, 58, 118), (150, 110, 170), (60, 36, 84)
RAINBOW = [(235, 75, 85), (250, 150, 60), (250, 215, 80), (120, 205, 110), (80, 160, 230), (140, 105, 210)]
GOLD, GOLD_L, GOLD_D = (255, 205, 70), (255, 240, 165), (215, 150, 40)
DEFAULT_BUMPS = [(-.5, .05, .42), (0, -.22, .55), (.5, 0, .44)]


def multi(stops, t: float):
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            return lerp(c0, c1, (t - t0) / max(1e-6, t1 - t0))
    return stops[-1][1]


def vgrad(s: pg.Surface, rect, c0=None, c1=None, stops=None) -> None:
    r = pg.Rect(rect)
    for y in range(r.h):
        t = y / max(1, r.h - 1)
        col = multi(stops, t) if stops else lerp(c0, c1, t)
        pg.draw.line(s, col, (r.x, r.y + y), (r.right - 1, r.y + y))


def glow(s: pg.Surface, x: float, y: float, r: float, col, a_max: int = 120) -> None:
    """Soft disc (the mockup's ``soft_glow``); sprites are cached per size."""
    r = max(2, int(r))
    g = _glow(r, tuple(col), int(a_max)) if r <= 160 else glow_sprite(r, col, a_max, power=2.0)
    s.blit(g, g.get_rect(center=(round(x), round(y))))


@lru_cache(maxsize=64)
def _glow(r: int, col, a_max: int) -> pg.Surface:
    return glow_sprite(r, col, a_max, power=2.0)


def cloud_bumps(rnd: random.Random | None):
    bumps = list(DEFAULT_BUMPS)
    if rnd is not None and rnd.random() < .5:
        bumps.append((rnd.choice([-.25, .25]), -.1, .45))
    return bumps


def cloud(s, cx, cy, cs, pal=PAL_B, bumps=None, sh=CLOUD_SH, ss=3) -> None:
    """Approved cloud tile (palette B). ``cs`` = cell size in big pixels."""
    top, mid, shade, rim = pal
    R = cs * .46
    base = pg.Rect(0, 0, R * 2, R * .9)
    base.center = (cx, cy + R * .28)
    bumps = bumps or DEFAULT_BUMPS

    def body(col, dx, dy, k):
        pg.draw.rect(s, col, base.move(dx, dy).inflate(-R * .1 * (1 - k), -R * .1 * (1 - k)),
                     border_radius=int(R * .45))
        for bx, by, br in bumps:
            pg.draw.circle(s, col, (cx + bx * R + dx, cy + by * R + dy), br * R * k)
    f = cs / (80.0 * ss)
    if sh is not None:
        body(sh, 4 * ss * f, 10 * ss * f, 1)
    body(shade, 0, 5 * ss * f, 1)
    body(mid, 0, 0, 1)
    body(top, -3 * ss * f, -5 * ss * f, .82)
    for bx, by, br in bumps:
        pg.draw.circle(s, rim, (cx + bx * R - br * R * .3, cy + by * R - br * R * .45), br * R * .2)


def melting(s, cx, cy, cs, ss=3) -> None:
    """Melting cloud: pale, see-through, with drips and 'shiver' lines."""
    w = int(cs * 1.6)
    srf = pg.Surface((w, w), pg.SRCALPHA)
    cloud(srf, w / 2, w / 2, cs, PAL_MELT, sh=None, ss=ss)
    srf.set_alpha(170)
    s.blit(srf, srf.get_rect(center=(cx, cy)))
    u = cs / 80
    for dx, dy, r in [(-.25, .42, .06), (.05, .52, .075), (.3, .45, .05)]:
        x, y, rr = cx + dx * cs, cy + dy * cs, r * cs
        pg.draw.circle(s, (255, 235, 245), (x, y), rr)
        pg.draw.polygon(s, (255, 235, 245), [(x - rr * .9, y - rr * .2), (x + rr * .9, y - rr * .2),
                                             (x, y - rr * 2.2)])
    for a in (-1, 1):
        for k in range(2):
            ang = math.radians(-90 + a * (40 + k * 26))
            pg.draw.line(s, (255, 255, 255), (cx + cs * .5 * math.cos(ang), cy + cs * .42 * math.sin(ang)),
                         (cx + cs * .62 * math.cos(ang), cy + cs * .54 * math.sin(ang)), max(1, int(3 * u)))


def far_bird(s, x, y, w, col=FAR_BIRD, lw=None) -> None:
    lw = lw or max(1, int(w * .16))
    pg.draw.arc(s, col, (x - w, y - w * .35, w, w * .7), math.radians(20), math.radians(160), lw)
    pg.draw.arc(s, col, (x, y - w * .35, w, w * .7), math.radians(20), math.radians(160), lw)


def gap_decor(s, cx, cy, cs, rnd) -> None:
    """Tiny far cloud + far bird seen through a hole."""
    ox = rnd.uniform(-.12, .12) * cs
    pg.draw.ellipse(s, GAP_DECOR, (cx - cs * .22 + ox, cy + cs * .12, cs * .44, cs * .12))
    pg.draw.circle(s, GAP_DECOR, (cx - cs * .04 + ox, cy + cs * .14), cs * .08)
    far_bird(s, cx + rnd.uniform(-.15, .15) * cs, cy - cs * .16, cs * .09)


def sparkle(s, x, y, r, col=(255, 250, 210)) -> None:
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * .28
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    pg.draw.polygon(s, col, pts)


def mini_cloud(s, cx, cy, r, col=(255, 250, 246), shade=(240, 200, 225)) -> None:
    pg.draw.ellipse(s, shade, (cx - r * 1.3, cy - r * .2, r * 2.6, r * .95))
    for dx, dy, rr in [(-.7, 0, .55), (0, -.3, .75), (.7, 0, .55)]:
        pg.draw.circle(s, shade, (cx + dx * r, cy + dy * r + r * .12), rr * r)
    for dx, dy, rr in [(-.7, 0, .55), (0, -.3, .75), (.7, 0, .55)]:
        pg.draw.circle(s, col, (cx + dx * r, cy + dy * r), rr * r)
    pg.draw.ellipse(s, col, (cx - r * 1.25, cy - r * .25, r * 2.5, r * .8))


def rainbow_arch(s, cx, cy, R, band, alpha=255) -> None:
    lay = pg.Surface((int(R * 2 + 4), int(R + 4)), pg.SRCALPHA)
    for i, col in enumerate(RAINBOW):
        pg.draw.circle(lay, (*col, 255), (R + 2, R + 2), R - i * band, draw_top_left=True, draw_top_right=True)
    pg.draw.circle(lay, (0, 0, 0, 0), (R + 2, R + 2), R - len(RAINBOW) * band,
                   draw_top_left=True, draw_top_right=True)
    pg.draw.arc(lay, (255, 255, 255, 120), (2 + band * .3, 2 + band * .3, 2 * R - band * .6, 2 * R - band * .6),
                math.radians(35), math.radians(145), max(1, int(band * .25)))
    if alpha < 255:
        lay.set_alpha(alpha)
    s.blit(lay, (cx - R - 2, cy - R - 2))


@lru_cache(maxsize=8)
def rainbow_exit_sprite(cs: int) -> pg.Surface:
    """Exit on a cloud cell: rainbow arch with two puff feet + sparkles."""
    size = int(cs * 1.5)

    def draw(s: pg.Surface, ss: float) -> None:
        c, C = size * ss / 2, cs * ss
        R = C * .52
        rainbow_arch(s, c, c + C * .18, R, R * .11)
        for sx in (-1, 1):
            mini_cloud(s, c + sx * R * .78, c + C * .2, C * .16)
        for dx, dy, r in [(-.4, -.45, .07), (.42, -.38, .055), (0, -.62, .05), (.1, .35, .04)]:
            sparkle(s, c + dx * C, c + dy * C, r * C)
    return render_ss((size, size), draw, ss=3)


@lru_cache(maxsize=8)
def red_arrow_sprite(size: int, direction: int) -> pg.Surface:
    """Swallow warning arrow; grid direction 0 up, 1 right, 2 down, 3 left."""
    def draw(s: pg.Surface, ss: float) -> None:
        k = size * ss / 60
        x = y = size * ss / 2
        ang = (direction - 1) * math.pi / 2
        pts = [(22, 0), (-8, -18), (-2, 0), (-8, 18)]
        cr, sr = math.cos(ang), math.sin(ang)
        P = [(x + (px * cr - py * sr) * k, y + (px * sr + py * cr) * k) for px, py in pts]
        pg.draw.polygon(s, (150, 20, 40), [(a + 1.5 * k, b + 2 * k) for a, b in P])
        pg.draw.polygon(s, (235, 55, 65), P)
        pg.draw.polygon(s, (255, 220, 220), P, max(1, int(2 * k)))
    return render_ss((size, size), draw, ss=3)


def dashed_line(s, a, b, col, w, dash, gap, phase=0.0) -> None:
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L == 0:
        return
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    d = -((phase * (dash + gap)) % (dash + gap))
    while d < L:
        s0, e = max(0.0, d), min(L, d + dash)
        if e > s0:
            pg.draw.line(s, col, (a[0] + ux * s0, a[1] + uy * s0), (a[0] + ux * e, a[1] + uy * e), w)
        d += dash + gap


def burst(s, x, y, r, col=(255, 250, 225), edge=(235, 170, 60), n=12, seed=3) -> None:
    rnd = random.Random(seed)
    pts = []
    for i in range(n * 2):
        a = i * math.pi / n
        rr = r * (1 if i % 2 == 0 else .68) * rnd.uniform(.9, 1.08)
        pts.append((x + rr * math.cos(a) * 1.25, y + rr * math.sin(a) * .85))
    pg.draw.polygon(s, edge, [(px + 3, py + 4) for px, py in pts])
    pg.draw.polygon(s, col, pts)
    pg.draw.polygon(s, edge, pts, max(2, int(r * .06)))


def star_points(cx, cy, r, inner=.45, rot=-math.pi / 2):
    return [(cx + (r if i % 2 == 0 else r * inner) * math.cos(rot + i * math.pi / 5),
             cy + (r if i % 2 == 0 else r * inner) * math.sin(rot + i * math.pi / 5)) for i in range(10)]


def comic_stars(s, x, y, u, n=3, rad=26, t=0.0) -> None:
    for i in range(n):
        a = -math.pi / 2 + (i - (n - 1) / 2) * .8 + t
        px, py = x + math.cos(a) * rad * u, y + math.sin(a) * rad * u * .55
        pts = star_points(px, py, 6 * u, .45, rot=-math.pi / 2 + i * .4)
        pg.draw.polygon(s, (215, 150, 30), [(p[0] + .8 * u, p[1] + .8 * u) for p in pts])
        pg.draw.polygon(s, (255, 225, 80), pts)


def sound_rings(s, x, y, u, col=(255, 255, 255), n=3, start=18, step=11, a0=-150, a1=-30) -> None:
    for i in range(n):
        r = (start + i * step) * u
        pg.draw.arc(s, col, (x - r, y - r, 2 * r, 2 * r), math.radians(-a1), math.radians(-a0),
                    max(1, int((3 - i * .6) * u)))


class T:
    """Local coords facing 'up' (-y); heading h in radians (0 = right, pi/2 = down)."""

    def __init__(self, s, cx, cy, K, h=-math.pi / 2):
        self.s, self.cx, self.cy, self.K = s, cx, cy, K
        self.F = (math.cos(h), math.sin(h))
        self.R = (-math.sin(h), math.cos(h))

    def p(self, x, y):
        f = -y
        return (self.cx + self.K * (x * self.R[0] + f * self.F[0]),
                self.cy + self.K * (x * self.R[1] + f * self.F[1]))

    def poly(self, col, pts, w=0):
        pg.draw.polygon(self.s, col, [self.p(*q) for q in pts], w)

    def circ(self, col, x, y, r, w=0):
        pg.draw.circle(self.s, col, self.p(x, y), r * self.K, int(w * self.K) if w else 0)

    def ell(self, col, x, y, rx, ry, n=28, rot=0.0):
        cr, sr = math.cos(rot), math.sin(rot)
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ex, ey = rx * math.cos(a), ry * math.sin(a)
            pts.append((x + ex * cr - ey * sr, y + ex * sr + ey * cr))
        self.poly(col, pts)

    def line(self, col, a, b, w):
        pg.draw.line(self.s, col, self.p(*a), self.p(*b), max(1, int(w * self.K)))

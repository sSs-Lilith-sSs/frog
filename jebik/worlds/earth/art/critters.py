"""Hedgehog, fox and mole drawing — ported from the approved mockup (all face RIGHT, K = px unit)."""
from __future__ import annotations

import math
import random

import pygame as pg

from ....art.common import render_ss
from .paint import alpha_circle


def shadow_sprite(w, h, alpha=80, col=(25, 45, 20)):
    return render_ss((max(2, int(w)), max(2, int(h))), lambda s, q: pg.draw.ellipse(
        s, (*col, alpha), (0, 0, int(w) * q, int(h) * q)), ss=3)


def draw_hedgehog(s, cx, cy, K, step=0):
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):   # feet
        off = 3 * K * (1 if (sx * sy > 0) == bool(step) else -1)
        pg.draw.ellipse(s, (120, 80, 70), (cx + sx * 11 * K - 4 * K + off, cy + sy * 15 * K - 3 * K, 8 * K, 6 * K))
    # spike coat: star outline around an ellipse (skip the face)
    def coat(rx, ry, spikes, col, shift=0.0, depth=6):
        pts = []
        n = spikes * 2
        for i in range(n + 1):
            t = math.radians(-125) + math.radians(250) * i / n
            ang = t + math.pi
            rr = 1.0 if i % 2 == 0 else (1 - depth / rx)
            pts.append((cx - 4 * K + shift + math.cos(ang) * rx * rr, cy + math.sin(ang) * ry * rr))
        pts.append((cx + 12 * K, cy))
        pg.draw.polygon(s, col, pts)
    coat(27 * K, 22 * K, 17, (78, 60, 52))
    coat(23 * K, 18.5 * K, 15, (116, 92, 78), 1 * K, 5 * K)
    coat(17 * K, 13 * K, 12, (150, 122, 102), 2 * K, 4 * K)
    rnd = random.Random(3)
    for _ in range(26):   # little spike strokes
        ang = rnd.uniform(math.radians(60), math.radians(300))
        r0 = rnd.uniform(.35, .8)
        x0 = cx - 4 * K + math.cos(ang) * 20 * K * r0
        y0 = cy + math.sin(ang) * 16 * K * r0
        pg.draw.line(s, (205, 185, 160), (x0, y0), (x0 + math.cos(ang) * 4 * K, y0 + math.sin(ang) * 4 * K),
                     max(1, int(1.3 * K)))
    # face
    face = (232, 200, 162)
    pg.draw.ellipse(s, face, (cx + 6 * K, cy - 10 * K, 18 * K, 20 * K))
    pg.draw.polygon(s, face, [(cx + 14 * K, cy - 8 * K), (cx + 30 * K, cy - 1.5 * K), (cx + 30 * K, cy + 1.5 * K),
                              (cx + 14 * K, cy + 8 * K)])
    for sy in (-1, 1):
        pg.draw.circle(s, (195, 140, 120), (cx + 11 * K, cy + sy * 10 * K), 3.4 * K)
        pg.draw.circle(s, (240, 170, 160), (cx + 11 * K, cy + sy * 10 * K), 1.8 * K)
        ex, ey = cx + 19 * K, cy + sy * 5 * K
        pg.draw.circle(s, (25, 20, 20), (ex, ey), 2.4 * K)
        pg.draw.circle(s, (255, 255, 255), (ex + .7 * K, ey - .8 * K), .9 * K)
        pg.draw.circle(s, (250, 150, 160), (cx + 15 * K, cy + sy * 7.5 * K), 2 * K)
    pg.draw.circle(s, (30, 25, 25), (cx + 30 * K, cy), 2.8 * K)
    pg.draw.circle(s, (120, 110, 110), (cx + 30.5 * K, cy - 1 * K), .9 * K)


def draw_hedgehog_ball(s, cx, cy, K, spin=0.0):
    R = 21 * K
    pts = []
    for i in range(48):
        ang = spin + i * 2 * math.pi / 48
        rr = R if i % 2 == 0 else R * .8
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    pg.draw.polygon(s, (78, 60, 52), pts)
    pg.draw.circle(s, (116, 92, 78), (cx, cy), R * .78)
    for j in range(3):   # swirl of spikes
        for i in range(10):
            f = i / 10
            ang = spin + j * 2.094 + f * 3.2
            rr = R * (.15 + .6 * f)
            x0, y0 = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
            pg.draw.line(s, (170, 145, 122), (x0, y0),
                         (x0 + math.cos(ang + 1.2) * 4 * K, y0 + math.sin(ang + 1.2) * 4 * K), max(1, int(1.5 * K)))
    pg.draw.circle(s, (150, 122, 102), (cx - 5 * K, cy - 6 * K), 5 * K)
    # peeking nose + feet tucked
    pg.draw.circle(s, (232, 200, 162), (cx + R * .55, cy + R * .45), 4 * K)
    pg.draw.circle(s, (30, 25, 25), (cx + R * .62, cy + R * .52), 1.6 * K)


def motion_lines(s, cx, cy, K, dirx=-1, length=30, n=3, spread=12, col=(255, 255, 255, 170), start=26):
    for i in range(n):
        dy = (i - (n - 1) / 2) * spread * K
        ln = length * K * (1 - .25 * abs(i - (n - 1) / 2))
        x0 = cx + dirx * start * K
        pg.draw.line(s, col, (x0, cy + dy), (x0 + dirx * ln, cy + dy), max(1, int(3.2 * K)))
        pg.draw.circle(s, col, (x0, cy + dy), 1.6 * K)
        pg.draw.circle(s, col, (x0 + dirx * ln, cy + dy), 1.6 * K)


def dust(s, cx, cy, K, n=5, dirx=-1, seed=1, spread=16, scale=1.0):
    rnd = random.Random(seed)
    for i in range(n):
        x = cx + dirx * (i * 7 + rnd.uniform(0, 6)) * K * scale
        y = cy + rnd.uniform(-spread, spread) * K
        r = (9 - i * 1.1) * K * scale
        alpha_circle(s, (215, 190, 150, 150 - i * 18), (x, y), r)
        alpha_circle(s, (240, 225, 195, 120 - i * 15), (x - 2 * K, y - 2 * K), r * .55)


FOX = (232, 122, 48)
FOX_D = (190, 90, 35)
FOX_W = (252, 244, 232)


def draw_fox(s, cx, cy, K, pose="run", sc=1.0):
    K = K * sc
    stretch = 1.25 if pose == "jump" else 1.0
    # legs
    legc = (70, 45, 35)
    if pose == "run":
        legs = [(14, -8, 12, 0), (14, 8, 8, 0), (-14, -9, -12, 0), (-14, 9, -8, 0)]
    else:   # jump: stretched fore & aft
        legs = [(15, -7, 17, 0), (15, 7, 15, 0), (-15, -7, -17, 0), (-15, 7, -15, 0)]
    for lx, ly, dx, _ in legs:
        x0, y0 = cx + lx * K, cy + ly * K
        x1, y1 = x0 + dx * K, y0 + (ly / abs(ly)) * 2 * K
        pg.draw.line(s, FOX_D, (x0, y0), (x1, y1), max(1, int(5 * K)))
        pg.draw.circle(s, legc, (x1, y1), 3.2 * K)
    # tail
    tx = cx - 22 * K * stretch
    tail = [(cx - 14 * K, cy - 5 * K), (tx - 10 * K, cy - 11 * K), (tx - 24 * K, cy - 6 * K),
            (tx - 28 * K, cy + 1 * K), (tx - 22 * K, cy + 7 * K), (tx - 8 * K, cy + 9 * K), (cx - 14 * K, cy + 5 * K)]
    pg.draw.polygon(s, FOX, tail)
    pg.draw.ellipse(s, FOX, (tx - 26 * K, cy - 10 * K, 30 * K, 19 * K))
    pg.draw.ellipse(s, FOX_W, (tx - 30 * K, cy - 7 * K, 13 * K, 13 * K))
    pg.draw.ellipse(s, (255, 170, 100), (tx - 16 * K, cy - 7 * K, 16 * K, 6 * K))
    # body
    bl = 34 * K * stretch
    pg.draw.ellipse(s, FOX, (cx - bl / 2, cy - 10 * K, bl, 20 * K))
    pg.draw.ellipse(s, FOX_D, (cx - bl / 2 + 4 * K, cy - 3 * K, bl - 10 * K, 6 * K))
    pg.draw.ellipse(s, (248, 150, 80), (cx - bl / 2 + 3 * K, cy - 8 * K, bl - 8 * K, 5 * K))
    # head
    hx = cx + bl / 2 + 3 * K
    pg.draw.circle(s, FOX, (hx, cy), 10 * K)
    for sy in (-1, 1):   # ears (pointing back)
        ear = [(hx - 2 * K, cy + sy * 4 * K), (hx - 12 * K, cy + sy * 13 * K), (hx + 3 * K, cy + sy * 10 * K)]
        pg.draw.polygon(s, FOX_D, ear)
        pg.draw.polygon(s, (60, 40, 35), [(hx - 7 * K, cy + sy * 9.5 * K), (hx - 12 * K, cy + sy * 13 * K),
                                          (hx - 4 * K, cy + sy * 11.5 * K)])
    snout = [(hx + 3 * K, cy - 8 * K), (hx + 17 * K, cy - 1.5 * K), (hx + 17 * K, cy + 1.5 * K), (hx + 3 * K, cy + 8 * K)]
    pg.draw.polygon(s, FOX_W, snout)
    pg.draw.polygon(s, FOX, [(hx - 2 * K, cy - 5 * K), (hx + 15 * K, cy - 1 * K), (hx + 15 * K, cy + 1 * K),
                             (hx - 2 * K, cy + 5 * K)])
    pg.draw.circle(s, (30, 25, 25), (hx + 17 * K, cy), 2.4 * K)
    for sy in (-1, 1):
        ex, ey = hx + 5 * K, cy + sy * 5 * K
        pg.draw.ellipse(s, (30, 25, 25), (ex - 2.5 * K, ey - 1.6 * K, 5 * K, 3.2 * K))
        pg.draw.circle(s, (255, 255, 255), (ex + .8 * K, ey - .5 * K), .8 * K)


MOLE = (72, 66, 82)
MOLE_L = (110, 104, 122)
PINK = (245, 160, 170)


def draw_mound(s, cx, cy, K, dirx=1, trail=3):
    n = trail * 3
    for i in range(n, 0, -1):   # furrow of raised soil behind
        x = cx - dirx * (8 + i * 5.5) * K
        y = cy + math.sin(i * .7) * 2.5 * K
        r = (9.5 - i * 6.5 / n) * K
        pg.draw.ellipse(s, (104, 74, 48), (x - r, y - r * .75 + 1.5 * K, 2 * r, 1.5 * r))
        pg.draw.ellipse(s, (150, 110, 72), (x - r, y - r * .75, 2 * r, 1.4 * r))
    for i in range(n, 0, -2):
        x = cx - dirx * (8 + i * 5.5) * K
        y = cy + math.sin(i * .7) * 2.5 * K
        pg.draw.circle(s, (178, 134, 90), (x, y - 1.5 * K), (2.4 - i * 1.2 / n) * K)
    pg.draw.ellipse(s, (86, 60, 38), (cx - 17 * K, cy - 13 * K + 3 * K, 34 * K, 28 * K))
    pg.draw.ellipse(s, (138, 98, 62), (cx - 17 * K, cy - 14 * K, 34 * K, 28 * K))
    pg.draw.ellipse(s, (170, 126, 82), (cx - 12 * K, cy - 11 * K, 20 * K, 16 * K))
    pg.draw.ellipse(s, (196, 152, 104), (cx - 8 * K, cy - 9 * K, 9 * K, 6 * K))
    rnd = random.Random(7)
    for _ in range(9):
        ang = rnd.uniform(0, 6.28)
        rr = rnd.uniform(4, 15) * K
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * .8
        r = rnd.uniform(1.6, 3) * K
        pg.draw.circle(s, (100, 70, 44), (x + .6 * K, y + .8 * K), r)
        pg.draw.circle(s, (160, 118, 76), (x, y), r)
    for i in range(3):   # little cracks in front
        ang = dirx * 0 + (i - 1) * .5
        x0 = cx + dirx * 15 * K
        pg.draw.line(s, (80, 55, 35), (x0, cy + (i - 1) * 6 * K),
                     (x0 + dirx * 7 * K * math.cos(ang), cy + (i - 1) * 6 * K + 5 * K * math.sin(ang)),
                     max(1, int(1.6 * K)))


def draw_tremor(s, cx, cy, K, cs_q):
    # red-orange warning pad + wobbly rings + jumping pebbles
    r = pg.Rect(0, 0, cs_q * .9, cs_q * .9)
    r.center = (cx, cy)
    tmp = pg.Surface(r.size, pg.SRCALPHA)
    pg.draw.rect(tmp, (255, 120, 60, 80), (0, 0, *r.size), border_radius=int(r.w * .2))
    pg.draw.rect(tmp, (255, 140, 60, 220), (0, 0, *r.size), max(1, int(3 * K)), border_radius=int(r.w * .2))
    s.blit(tmp, r.topleft)
    for j, rad in enumerate((9, 17, 25)):
        pts = []
        for i in range(61):
            a = i / 60 * 2 * math.pi
            rr = rad * K * (1 + .07 * math.sin(a * 9 + j))
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * .8))
        pg.draw.lines(s, (120, 70, 35, 200 - j * 50), True, pts, max(1, int(2.2 * K)))
    for dx, dy, lift in ((-14, -10, 5), (12, -12, 7), (16, 10, 4), (-10, 13, 6)):
        pg.draw.ellipse(s, (40, 60, 25, 90), (cx + dx * K - 2.5 * K, cy + dy * K - 1 * K, 5 * K, 3 * K))
        pg.draw.circle(s, (150, 112, 72), (cx + dx * K, cy + (dy - lift) * K), 2.6 * K)
        for sgn in (-1, 1):   # shake ticks
            pg.draw.line(s, (255, 250, 240), (cx + (dx + sgn * 4) * K, cy + (dy - lift - 2) * K),
                         (cx + (dx + sgn * 6.5) * K, cy + (dy - lift - 3) * K), max(1, int(1.3 * K)))


def draw_mole_out(s, cx, cy, K):
    """Mole popped out of a hole (hole drawn by the field). Faces down-screen (toward viewer)."""
    rnd = random.Random(11)
    for _ in range(12):   # thrown dirt
        ang = rnd.uniform(0, 6.28)
        rr = rnd.uniform(23, 33) * K
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        r = rnd.uniform(1.8, 3.4) * K
        pg.draw.circle(s, (100, 70, 44), (x + .7 * K, y + 1 * K), r)
        pg.draw.circle(s, (165, 120, 78), (x, y), r)
    pg.draw.ellipse(s, (30, 20, 14, 120), (cx - 16 * K, cy - 6 * K, 32 * K, 24 * K))
    pg.draw.circle(s, MOLE, (cx, cy - 2 * K), 15 * K)
    pg.draw.circle(s, MOLE_L, (cx - 4 * K, cy - 8 * K), 6 * K)
    for sx in (-1, 1):   # big digging paws
        px, py = cx + sx * 15 * K, cy + 5 * K
        pg.draw.ellipse(s, PINK, (px - 6 * K, py - 5 * K, 12 * K, 10 * K))
        for i in range(4):
            a = math.radians(60 + i * 20) if sx > 0 else math.radians(120 - i * 20)
            a = -a + math.pi   # claws point outwards-down
            fx = px + sx * abs(math.cos(a)) * 6 * K
            fy = py + 3 * K + (i - 1.5) * 1.5 * K
            pg.draw.line(s, (250, 245, 235), (fx, fy), (fx + sx * 3.5 * K, fy + 2 * K), max(1, int(1.6 * K)))
    for sx in (-1, 1):   # squinty eyes
        pg.draw.arc(s, (25, 20, 30), (cx + sx * 6 * K - 3 * K, cy - 5 * K, 6 * K, 4 * K), .3, math.pi - .3,
                    max(1, int(1.5 * K)))
        pg.draw.circle(s, (250, 150, 170), (cx + sx * 9 * K, cy + 1 * K), 2 * K)
    nx, ny = cx, cy + 5 * K   # star nose
    for i in range(10):
        a = i * 2 * math.pi / 10
        pg.draw.circle(s, (240, 120, 140), (nx + math.cos(a) * 3.8 * K, ny + math.sin(a) * 3.8 * K), 1.8 * K)
    pg.draw.circle(s, (255, 170, 185), (nx, ny), 3 * K)
    pg.draw.circle(s, (200, 90, 110), (nx - 1 * K, ny + .5 * K), .7 * K)
    pg.draw.circle(s, (200, 90, 110), (nx + 1 * K, ny + .5 * K), .7 * K)

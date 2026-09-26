"""Water world field ("style B"): organic numpy pools + lily pads ``pad_B``.

Ported from the approved mockup ``water.py``. The field background (water and
pools) is rendered once per level; every pad is a separate cached sprite so
it can bob gently and dip when the frog lands on it.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
import pygame as pg

from .... import config
from ....art.common import blur, lerp, render_ss

TWO_PI = 6.28


@dataclass
class PadSpec:
    cell: tuple[int, int]
    cx: float           # centre in field pixels
    cy: float
    radius: float
    angle: float
    flower: bool
    phase: float


def water_background(gw: int, gh: int, cs: int, holes: set[tuple[int, int]],
                     seed: int = 4, ss: int = config.SS_FIELD) -> pg.Surface:
    """Field water with blurred organic pools (no pads). Returns gw*cs x gh*cs."""
    rnd = random.Random(seed)
    k = cs / 64
    c = cs * ss
    W, H = gw * c, gh * c
    s = pg.Surface((W, H))
    for y in range(H):
        pg.draw.line(s, lerp((95, 185, 200), (60, 150, 185), y / H), (0, y), (W, y))
    for _ in range(gw * gh):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        w = int(rnd.randint(20, 60) * ss * k / 2)
        pg.draw.arc(s, (150, 215, 225), (x, y, w, max(1, w // 3)), 0.3, 2.8, ss)
    # mask of holes (union incl. connectors), blurred -> organic rounded pools
    m = pg.Surface((W, H))
    m.fill((0, 0, 0))
    mg = int(c * .14)
    white = (255, 255, 255)
    for (x, y) in holes:
        pg.draw.rect(m, white, (x * c + mg, y * c + mg, c - 2 * mg, c - 2 * mg),
                     border_radius=int(c * .3))
        for dx, dy in ((1, 0), (0, 1)):
            if (x + dx, y + dy) in holes:
                pg.draw.rect(m, white, (x * c + mg, y * c + mg,
                                        c * (1 + dx) - 2 * mg, c * (1 + dy) - 2 * mg))
        if {(x + 1, y), (x, y + 1), (x + 1, y + 1)} <= holes:
            pg.draw.rect(m, white, (x * c + mg, y * c + mg, 2 * c - 2 * mg, 2 * c - 2 * mg))
    if holes:
        a = pg.surfarray.array_red(m).astype(np.float32) / 255
        a = blur(a, int(c * .12))                         # soft rounded outline
        inside = np.clip((a - .35) / .3, 0, 1)            # pool alpha
        depth = np.clip(blur(inside, int(c * .14)), 0, 1)  # deeper toward the middle
        rim = np.clip(1 - abs(a - .36) / .05, 0, 1) * .6   # light foam rim
        sel = (inside > 0) | (rim > 0)                     # only touch pixels near pools
        px = pg.surfarray.pixels3d(s)
        base = px[sel].astype(np.float32)
        ins, dep, rm = inside[sel][:, None], depth[sel][:, None], rim[sel][:, None]
        shallow = np.array((70, 155, 190), np.float32)
        deep = np.array((12, 45, 85), np.float32)
        col = shallow * (1 - dep) + deep * dep
        base = base * (1 - ins) + col * ins
        base = base * (1 - rm) + np.array((190, 232, 238), np.float32) * rm
        px[sel] = base.astype(np.uint8)
        del px
    for (x, y) in sorted(holes):   # a few ripples only on the deepest spots
        cx, cy = x * c + c // 2, y * c + c // 2
        if rnd.random() < .6:
            r = pg.Rect(0, 0, c * .46, c * .17)
            r.center = (cx, cy)
            pg.draw.ellipse(s, (60, 120, 170), r, max(1, int(ss * 2 * k)))
        pg.draw.circle(s, (160, 215, 240), (cx + rnd.randint(-12, 12) * ss * k,
                                            cy + rnd.randint(-12, 12) * ss * k),
                       rnd.randint(2, 4) * ss * k, max(1, int(ss * k)))
    return pg.transform.smoothscale(s, (gw * cs, gh * cs))


def pad_layout(gw: int, gh: int, cs: int, holes: set[tuple[int, int]],
               seed: int = 4) -> list[PadSpec]:
    """Pad positions/sizes as in the mockup: pads next to water shrink and
    lean away from it; open pads get a little jitter."""
    rnd = random.Random(seed * 7919 + 17)
    k = cs / 64
    pads = []
    for y in range(gh):
        for x in range(gw):
            if (x, y) in holes:
                continue
            nb = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if (x + dx, y + dy) in holes]
            px = -sum(d[0] for d in nb) * 3 * k
            py = -sum(d[1] for d in nb) * 3 * k
            j = 0 if nb else 3
            cx = x * cs + cs / 2 + px + rnd.randint(-j, j) * k
            cy = y * cs + cs / 2 + py + rnd.randint(-j, j) * k
            radius = cs * (rnd.uniform(.34, .37) if nb else rnd.uniform(.37, .43))
            pads.append(PadSpec((x, y), cx, cy, radius, rnd.uniform(0, TWO_PI),
                                rnd.random() < .04, rnd.uniform(0, TWO_PI)))
    return pads


def draw_pad(s: pg.Surface, cx: float, cy: float, R: float, a: float,
             flower: bool, u: float) -> None:
    """``pad_B`` from the mockup. ``u`` = pixel unit (SS * cell scale)."""
    w = .32

    def leaf(col, rad, off=(0, 0)):
        pts = [(cx + off[0], cy + off[1])] + [
            (cx + off[0] + rad * math.cos(a + w + (TWO_PI - 2 * w) * i / 40),
             cy + off[1] + rad * math.sin(a + w + (TWO_PI - 2 * w) * i / 40)) for i in range(41)]
        pg.draw.polygon(s, col, pts)
    leaf((35, 95, 110), R, (2 * u, 4 * u))
    for i in range(7):
        leaf(lerp((55, 150, 68), (130, 212, 112), i / 6), int(R * (1 - i * .09)))
    for i in range(7):
        t = a + w + (TWO_PI - 2 * w) * (i + .5) / 7
        pg.draw.line(s, (85, 172, 88), (cx, cy), (cx + R * .85 * math.cos(t),
                                                  cy + R * .85 * math.sin(t)), max(1, int(u)))
    pg.draw.arc(s, (205, 245, 195), (cx - R * .7, cy - R * .7, R * 1.4, R * 1.4),
                a + 2.2, a + 3.4, max(1, int(2 * u)))
    if flower:
        fx, fy = cx - R * .25, cy + R * .2
        for i in range(8):
            t = i * .785
            pg.draw.ellipse(s, (250, 170, 200), (fx + 9 * u * math.cos(t) - 6 * u,
                                                 fy + 9 * u * math.sin(t) - 6 * u, 12 * u, 12 * u))
        pg.draw.circle(s, (255, 225, 90), (fx, fy), 5 * u)


def pad_sprite(radius: float, angle: float, flower: bool, k: float) -> pg.Surface:
    """One pad, centred in its sprite."""
    half = int(radius + 8 * k) + 2
    size = (half * 2, half * 2)

    def draw(s: pg.Surface, ss: float) -> None:
        draw_pad(s, half * ss, half * ss, radius * ss, angle, flower, ss * k)
    return render_ss(size, draw, ss=3)


BOB_FRAMES = 7
BOB_DEGREES = 2.2


def pad_frames(spec: PadSpec, k: float) -> list[pg.Surface]:
    """Slight rotation frames for a gentle bob (-BOB_DEGREES..+BOB_DEGREES)."""
    base = pad_sprite(spec.radius, spec.angle, spec.flower, k)
    frames = []
    for i in range(BOB_FRAMES):
        deg = -BOB_DEGREES + 2 * BOB_DEGREES * i / (BOB_FRAMES - 1)
        frames.append(base if abs(deg) < 1e-6 else pg.transform.rotozoom(base, deg, 1.0))
    return frames


def draw_exit(s: pg.Surface, cx: float, cy: float, u: float) -> None:
    """Exit pad with a big lotus (no glow; glow is a separate sprite)."""
    draw_pad(s, cx, cy, int(28 * u), random.Random(1).uniform(0, TWO_PI), False, u)
    for layer, (col, rr, n) in enumerate([((250, 150, 190), 13, 8), ((255, 190, 215), 9, 8),
                                          ((255, 230, 240), 5, 6)]):
        for i in range(n):
            t = i * 2 * math.pi / n + layer * .3
            pg.draw.ellipse(s, col, (cx + rr * u * math.cos(t) - 6 * u,
                                     cy + rr * u * math.sin(t) - 6 * u, 12 * u, 12 * u))
    pg.draw.circle(s, (255, 215, 80), (cx, cy), 4 * u)


def exit_sprite(k: float) -> pg.Surface:
    size = int(80 * k)
    return render_ss((size, size), lambda s, ss: draw_exit(s, size * ss / 2, size * ss / 2, ss * k))

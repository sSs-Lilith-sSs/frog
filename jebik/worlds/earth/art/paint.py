"""Earth field painting — ported from the approved mockup (numpy at build time only)."""
from __future__ import annotations

import math
import random

import numpy as np
import pygame as pg

from ....art.common import blur, render_ss


def sprite(size, fn, ss=3):
    """fn(surface, K_ss, cx, cy) drawn supersampled; returns downscaled sprite."""
    w, h = size
    return render_ss((int(w), int(h)), lambda s, q: fn(s, q, s.get_width() / 2, s.get_height() / 2), ss=ss)


def blit_c(dst, img, c, rot=0.0):
    if rot:
        img = pg.transform.rotozoom(img, rot, 1.0)
    dst.blit(img, img.get_rect(center=(round(c[0]), round(c[1]))))


def alpha_ellipse(s, col, rect):
    r = pg.Rect(rect)
    tmp = pg.Surface((max(1, r.w), max(1, r.h)), pg.SRCALPHA)
    pg.draw.ellipse(tmp, col, (0, 0, r.w, r.h))
    s.blit(tmp, r.topleft)


def alpha_circle(s, col, c, rad):
    rad = max(1, rad)
    tmp = pg.Surface((int(rad * 2) + 2, int(rad * 2) + 2), pg.SRCALPHA)
    pg.draw.circle(tmp, col, (rad + 1, rad + 1), rad)
    s.blit(tmp, (c[0] - rad - 1, c[1] - rad - 1))


def vnoise(Wd, Ht, n, seed):
    r = np.random.default_rng(seed)
    small = (r.random((max(2, n[0]), max(2, n[1]))) * 255).astype(np.uint8)
    s = pg.Surface(small.shape)
    pg.surfarray.blit_array(s, np.stack([small] * 3, -1))
    big = pg.transform.smoothscale(s, (Wd, Ht))
    return pg.surfarray.array_red(big).astype(np.float32) / 255


# =================================================================== FIELD
GRASS_DARK = np.array((62, 138, 58), np.float32)
GRASS_LIGHT = np.array((150, 212, 98), np.float32)
SEAM_TOP = (64, 112, 50)
SEAM_BOT = (52, 98, 44)
RIM = np.array((150, 108, 66), np.float32)
WALL = np.array((168, 118, 72), np.float32)
MID = np.array((104, 68, 42), np.float32)
DEEP = np.array((44, 27, 16), np.float32)
PIT_BOTTOM = (55, 38, 20)
LIP = (88, 58, 34)


def _cell_mask(Wd, Ht, c, cells, mg, rad, connect):
    """Opaque-white-on-transparent mask of ``cells`` (cell size ``c`` px)."""
    m = pg.Surface((Wd, Ht), pg.SRCALPHA)
    m.fill((255, 255, 255, 0))
    wht = (255, 255, 255, 255)
    for (x, y) in cells:
        pg.draw.rect(m, wht, (x * c + mg, y * c + mg, c - 2 * mg, c - 2 * mg), border_radius=rad)
        if connect:
            for dx, dy in ((1, 0), (0, 1)):
                if (x + dx, y + dy) in cells:
                    pg.draw.rect(m, wht, (x * c + mg, y * c + mg, c * (1 + dx) - 2 * mg, c * (1 + dy) - 2 * mg))
            if {(x + 1, y), (x, y + 1), (x + 1, y + 1)} <= cells:
                pg.draw.rect(m, wht, (x * c + mg, y * c + mg, 2 * c - 2 * mg, 2 * c - 2 * mg))
    return m


def _mask_array(m, size):
    """Antialiased float mask (0..1) of a supersampled mask surface at ``size``."""
    return pg.surfarray.array_alpha(pg.transform.smoothscale(m, size)).astype(np.float32) / 255


def clover(s, cx, cy, u, rot):
    for i in range(3):
        a = rot + i * 2.094
        for sgn in (-1, 1):
            px = cx + math.cos(a) * 4.2 * u + math.cos(a + sgn * 1.2) * 2.2 * u
            py = cy + math.sin(a) * 4.2 * u + math.sin(a + sgn * 1.2) * 2.2 * u
            pg.draw.circle(s, (70, 160, 70), (px, py), 3.2 * u)
    for i in range(3):
        a = rot + i * 2.094
        pg.draw.circle(s, (120, 200, 100), (cx + math.cos(a) * 4.5 * u, cy + math.sin(a) * 4.5 * u), 1.4 * u)
    pg.draw.circle(s, (160, 225, 130), (cx, cy), 1.3 * u)


def tiny_flower(s, cx, cy, u, kind):
    petal, mid = {"daisy": ((250, 250, 245), (255, 205, 60)),
                  "butter": ((255, 220, 70), (240, 160, 30)),
                  "pink": ((250, 175, 205), (255, 230, 120)),
                  "blue": ((130, 165, 245), (255, 240, 180))}[kind]
    n = 8 if kind == "daisy" else 5
    for i in range(n):
        a = i * 2 * math.pi / n
        pg.draw.circle(s, petal, (cx + math.cos(a) * 3.6 * u, cy + math.sin(a) * 3.6 * u), 2.5 * u)
    pg.draw.circle(s, mid, (cx, cy), 2.2 * u)


def _field_pixels(gw, gh, cs, grass_mask, pit_mask, grass, crumble, rnd, seed, row0, rows_total):
    """The numpy part of the field (soft shading / noise) at 1 px per screen px.

    Everything here is blurred or noise-based, so supersampling it (as the
    mockup did at x2) is invisible — only the vector decor drawn afterwards
    is supersampled. Returns (rgb uint8 (W, H, 3), grass mask float (W, H))."""
    c = cs
    Wd, Ht = gw * c, gh * c
    gm = _mask_array(grass_mask, (Wd, Ht))
    gm = blur(gm, int(c * .012))
    pm = _mask_array(pit_mask, (Wd, Ht))
    a = blur(pm, int(c * .13))
    n_wob = vnoise(Wd, Ht, (gw * 5, gh * 5), seed + 9)
    a = np.clip(a + (n_wob - .5) * .42 * np.clip(1 - np.abs(a - .45) / .4, 0, 1), 0, 1)
    inside = np.clip((a - .42) / .16, 0, 1)
    n_big = vnoise(Wd, Ht, (gw * 3, gh * 3), seed + 1)
    n_mid = vnoise(Wd, Ht, (gw * 9, gh * 9), seed + 2)
    n_fine = vnoise(Wd, Ht, (gw * 28, gh * 28), seed + 3)
    # scalar maps first; colours are mixed channel by channel below
    t = (np.arange(Ht, dtype=np.float32) / c + row0) / (rows_total or gh)      # seam gradient
    seam_mul = 0.92 + 0.12 * n_mid
    rim = np.clip((a - .06) / .2, 0, 1) * (1 - inside)                          # dirt lip around pits
    rim_mul = 0.88 + 0.22 * n_fine
    o = int(c * .035)                                                           # tiles' drop shadow
    sh = blur(np.roll(np.roll(gm, o, 0), int(o * 1.3), 1), int(c * .03))
    shade = 1 - .38 * (sh * (1 - gm))
    inner = np.clip(blur(gm, int(c * .07)) * 1.25 - .15, 0, 1)
    ramp = np.arange(c, dtype=np.float32) / c
    light = 1 - (np.tile(ramp, gw)[:, None] * .45 + np.tile(ramp, gh)[None, :] * .55)
    lum = .38 * inner + .27 * light + .2 * n_big + .15 * n_mid
    lum = np.clip(lum * (0.93 + 0.14 * n_fine), 0, 1)
    tint = np.zeros((gw, gh, 3), np.float32)
    for (x, y) in grass:
        v = rnd.uniform(-1, 1)
        tint[x, y] = (8 * v, 5 * v, -6 * v)
        if (x, y) in crumble:
            tint[x, y] = (38, 8, -18)
    depth = np.clip(blur(inside, int(c * .13)), 0, 1)                           # pit interiors
    depth = np.clip((depth - .45) / .55, 0, 1) ** 1.1
    d1 = np.clip(depth * 2, 0, 1)
    d2 = np.clip(depth * 2 - 1, 0, 1)
    oo = int(c * .16)
    top = 1 - .55 * blur(inside * (1 - np.roll(inside, oo, 1)), int(c * .05))
    bot = blur(inside * (1 - np.roll(inside, -oo, 1)), int(c * .05))
    pit_mul = 0.86 + 0.26 * n_fine
    lip = np.clip(1 - np.abs(a - .43) / .035, 0, 1) * .45                      # inner lip line
    out = np.empty((Wd, Ht, 3), np.uint8)
    for i in range(3):
        img = (SEAM_TOP[i] + (SEAM_BOT[i] - SEAM_TOP[i]) * t)[None, :] * seam_mul
        img += (RIM[i] * rim_mul - img) * rim
        img *= shade
        gcol = GRASS_DARK[i] + (GRASS_LIGHT[i] - GRASS_DARK[i]) * lum
        gcol += np.repeat(np.repeat(tint[..., i], c, 0), c, 1)
        img += (gcol - img) * gm
        pc = WALL[i] + (MID[i] - WALL[i]) * d1 + (DEEP[i] - MID[i]) * d2
        pc *= top
        pc += PIT_BOTTOM[i] * bot
        pc *= pit_mul
        img += (pc - img) * inside
        img += (LIP[i] - img) * lip
        out[..., i] = np.clip(img, 0, 255)
    return out, gm


def earth_field(gw, gh, cs, pits, crumble=(), fresh=(), avoid=(), seed=3, ss=2, row0=0, rows_total=None,
                with_mask=False):
    """Grass tiles + organic dirt pits. Returns (gw*cs, gh*cs) surface
    (and the grass-only layer with ``with_mask``).

    Shading is computed with numpy at screen resolution; blades, pebbles and
    decor are drawn supersampled (x ``ss``) on top, then scaled down."""
    rnd = random.Random(seed)
    pits = set(pits)
    crumble = set(crumble)
    c = cs * ss
    Wd, Ht = gw * c, gh * c
    u = ss * cs / 64
    grass = {(x, y) for x in range(gw) for y in range(gh)} - pits
    grass_mask = _cell_mask(Wd, Ht, c, grass, int(c * .05), int(c * .2), False)
    pit_mask = _cell_mask(Wd, Ht, c, pits, int(c * .1), int(c * .4), True)
    pix, gm = _field_pixels(gw, gh, cs, grass_mask, pit_mask, grass, crumble, rnd, seed, row0, rows_total)
    small = pg.surfarray.make_surface(pix)
    s = pg.transform.smoothscale(small, (Wd, Ht))

    # grass blade tufts (clipped to tiles)
    bl = pg.Surface((Wd, Ht), pg.SRCALPHA)
    for (x, y) in grass:
        for _ in range(26):
            px = x * c + rnd.uniform(.12, .88) * c
            py = y * c + rnd.uniform(.12, .88) * c
            ang = rnd.uniform(0, 2 * math.pi)
            ln = rnd.uniform(3, 6) * u
            lt = rnd.random() < .6
            col = (185, 235, 130, 120) if lt else (50, 115, 45, 110)
            for d in (-.45, 0, .45):
                pg.draw.line(bl, col, (px, py), (px + math.cos(ang + d) * ln, py + math.sin(ang + d) * ln),
                             max(1, int(.9 * u)))
    bl.blit(grass_mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
    s.blit(bl, (0, 0))

    # pebbles / roots inside pits
    for (x, y) in sorted(pits):
        for _ in range(10):
            px = x * c + rnd.uniform(.2, .8) * c
            py = y * c + rnd.uniform(.2, .8) * c
            pg.draw.circle(s, (92, 64, 42), (px, py), rnd.uniform(.6, 1.2) * u)
        for _ in range(2):
            px = x * c + rnd.uniform(.3, .7) * c
            py = y * c + rnd.uniform(.35, .75) * c
            r = rnd.uniform(1.6, 2.8) * u
            pg.draw.circle(s, (70, 48, 32), (px, py), r)
            pg.draw.circle(s, (98, 70, 46), (px - r * .3, py - r * .3), r * .45)
        if rnd.random() < .5:   # tiny root hanging in from the top wall
            px = x * c + rnd.uniform(.3, .7) * c
            py = y * c + c * .2
            pts = [(px + math.sin(i * .9) * 2 * u, py + i * 2.5 * u) for i in range(5)]
            pg.draw.lines(s, (150, 110, 70), False, pts, max(1, int(1.2 * u)))
    # fresh pits: loose clods around the rim
    for (x, y) in sorted(set(fresh)):
        cx, cy = x * c + c / 2, y * c + c / 2
        for i in range(9):
            ang = rnd.uniform(0, 2 * math.pi)
            rr = c * rnd.uniform(.43, .52)
            px, py = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
            r = rnd.uniform(2, 4) * u
            pg.draw.circle(s, (110, 76, 48), (px + u, py + u * 1.5), r)
            pg.draw.circle(s, (170, 124, 80), (px, py), r)

    # little decor on tiles
    for (x, y) in sorted(grass):
        if (x, y) in avoid or (x, y) in crumble:
            continue
        r = rnd.random()
        if r > .34:
            continue
        corner = rnd.choice(((.22, .22), (.78, .22), (.22, .78), (.78, .78)))
        px, py = x * c + corner[0] * c, y * c + corner[1] * c
        if r < .15:
            clover(s, px, py, u * 1.05, rnd.uniform(0, 6.28))
        elif r < .27:
            tiny_flower(s, px, py, u * .95, rnd.choice(("daisy", "daisy", "butter", "pink", "blue")))
        else:
            pg.draw.circle(s, (120, 125, 110), (px + .6 * u, py + .8 * u), 2.8 * u)
            pg.draw.circle(s, (178, 180, 165), (px, py), 2.6 * u)
            pg.draw.circle(s, (210, 212, 200), (px - .8 * u, py - .8 * u), 1 * u)
    img = pg.transform.smoothscale(s, (gw * cs, gh * cs))
    if not with_mask:
        return img
    # grass-only layer (alpha = tile mask) for per-tile sprites
    grass_layer = _with_alpha(img)
    pg.surfarray.pixels_alpha(grass_layer)[...] = (np.clip(gm, 0, 1) * 255).astype(np.uint8)
    return img, grass_layer


def _with_alpha(img):
    out = pg.Surface(img.get_size(), pg.SRCALPHA)
    out.blit(img, (0, 0))
    return out


def crumble_overlay(cs, seed=5):
    """Cracks + falling crumbs over a 'crumbling ground' tile."""
    rnd = random.Random(seed)

    def fn(s, q, cx, cy):
        u = q * cs / 64
        c = cs * q
        # warning outline (dashed, orange)
        r = pg.Rect(0, 0, c * .88, c * .88)
        r.center = (cx, cy)
        n = 16
        pts = []
        for i in range(n * 4):
            f = i / (n * 4)
            side = int(f * 4)
            g = f * 4 - side
            if side == 0:
                pts.append((r.left + g * r.w, r.top))
            elif side == 1:
                pts.append((r.right, r.top + g * r.h))
            elif side == 2:
                pts.append((r.right - g * r.w, r.bottom))
            else:
                pts.append((r.left, r.bottom - g * r.h))
        for i in range(0, len(pts) - 1, 2):
            pg.draw.line(s, (255, 170, 60, 220), pts[i], pts[i + 1], max(1, int(2.4 * u)))
        # cracks
        def crack(x, y, ang, ln, w, depth):
            pts = [(x, y)]
            for _ in range(4):
                ang += rnd.uniform(-.5, .5)
                x += math.cos(ang) * ln / 4
                y += math.sin(ang) * ln / 4
                pts.append((x, y))
            pg.draw.lines(s, (70, 45, 28), False, pts, max(1, int(w)))
            pg.draw.lines(s, (200, 160, 110, 150), False, [(p[0] + .8 * u, p[1] + .8 * u) for p in pts],
                          max(1, int(w * .4)))
            if depth > 0:
                for p in pts[1:3]:
                    crack(p[0], p[1], ang + rnd.choice((-1, 1)) * rnd.uniform(.6, 1.1), ln * .5, w * .65,
                          depth - 1)
        for i in range(5):
            ang = i * 2 * math.pi / 5 + rnd.uniform(-.3, .3)
            crack(cx + math.cos(ang) * 3 * u, cy + math.sin(ang) * 3 * u, ang, c * .36, 2.6 * u, 1)
        pg.draw.circle(s, (70, 45, 28), (cx, cy), 3.2 * u)
        # crumbs
        for _ in range(7):
            ang = rnd.uniform(0, 6.28)
            rr = c * rnd.uniform(.12, .38)
            pg.draw.circle(s, (150, 110, 70), (cx + math.cos(ang) * rr, cy + math.sin(ang) * rr),
                           rnd.uniform(1.2, 2.2) * u)
    return sprite((cs, cs), fn)

"""Studio splash art: «21th / MANGO / CAT» golden monument, dusk sky, city, beams.

Everything is pre-rendered once (numpy allowed here, never per frame):

* :func:`sky` — deep blue -> purple -> orange dusk with clouds and stars;
* :func:`beam` — one searchlight cone (RGB, for additive blits);
* :func:`city` — dark towers at both sides (alpha layer);
* :func:`logo` — the extruded 3D monument text on a stepped base.

The splash scene only rotates beams and scales the city / logo layers.
"""
from __future__ import annotations

import random
from functools import lru_cache

import numpy as np
import pygame as pg

from .. import config
from .common import blur
from .splash_glyphs import glyph

W, H = config.SCREEN_W, config.SCREEN_H
HORIZON = 800
LOGO_ZOOM = config.STUDIO_ZOOM[1]          # logo layer is rendered at the closest zoom
CITY_ZOOM = 1.0 + (LOGO_ZOOM - 1.0) * 0.6

# logo layout at zoom 1 (screen px): (text, cap height, small-suffix)
LINES = (("21", 150, "TH"), ("MANGO", 106, ""), ("CAT", 214, ""))
LINE_GAP = 26
TRACK = 0.1                                 # letter spacing, x cap height
LOGO_TOP = 150
DEPTH = 62                                  # extrusion length (px at zoom 1)
EXTRUDE = (-0.52, 0.855)                    # direction: down-left (seen from low left)


# ---------------------------------------------------------------- sky
@lru_cache(maxsize=1)
def sky() -> pg.Surface:
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    stops = [(0.0, (6, 10, 38)), (0.3, (26, 34, 102)), (0.52, (92, 48, 128)),
             (0.64, (186, 76, 112)), (0.71, (238, 120, 70)), (0.74, (255, 178, 92)), (1.0, (40, 20, 40))]
    rgb = np.zeros((H, 1, 3), np.float32)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        t = np.clip((y - a) / (b - a), 0, 1)
        sel = (y >= a) & (y <= b)
        rgb = np.where(sel[..., None], np.array(ca) + (np.array(cb) - np.array(ca)) * t[..., None], rgb)
    rgb = np.repeat(rgb, W, axis=1)
    xs = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
    glow = np.exp(-((y - .735) / .05) ** 2) * np.exp(-(xs / .9) ** 2)       # hot horizon glow
    rgb += glow[..., None] * np.array((60, 40, 10), np.float32)
    s = pg.Surface((W, H))
    pg.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
    rnd = random.Random(21)
    for _ in range(160):                                                  # stars
        sx, sy = rnd.randint(0, W), int(rnd.random() ** 1.8 * H * .45)
        c = int(150 + 105 * rnd.random() * (1 - sy / (H * .45)))
        s.set_at((sx, sy), (c, c, min(255, c + 20)))
    cw, ch = W // 4, H // 4                                               # soft cloud bands
    cy_, cx_ = np.mgrid[0:ch, 0:cw].astype(np.float32)
    alpha = np.zeros((ch, cw), np.float32)
    tint = np.zeros((ch, cw), np.float32)
    for _ in range(22):
        y0 = rnd.uniform(.4, .7) * ch
        x0, sx, sy = rnd.uniform(-40, cw + 40), rnd.uniform(40, 130), rnd.uniform(2.5, 6)
        g = np.exp(-((cx_ - x0) / sx) ** 2 - ((cy_ - y0) / sy) ** 2) * rnd.uniform(.35, .7)
        alpha = np.maximum(alpha, g)
        tint = np.maximum(tint, g * np.clip((y0 / ch - .4) / .3, 0, 1))
    lo, hi = np.array((46, 26, 74), np.float32), np.array((236, 120, 96), np.float32)
    rgb = lo + (hi - lo) * np.clip(tint / np.maximum(alpha, 1e-3), 0, 1)[..., None] ** 1.3
    clouds = pg.Surface((cw, ch), pg.SRCALPHA)
    pg.surfarray.blit_array(clouds, rgb.transpose(1, 0, 2).astype(np.uint8))
    pg.surfarray.pixels_alpha(clouds)[...] = (np.clip(alpha, 0, 1) * 200).T.astype(np.uint8)
    s.blit(pg.transform.smoothscale(clouds, (W, H)), (0, 0))
    return s


# ---------------------------------------------------------------- beam
@lru_cache(maxsize=1)
def beam(length: int = 1500, width: int = 340) -> pg.Surface:
    """Searchlight cone, source at the bottom centre, pointing up."""
    v = np.linspace(1, 0, length, dtype=np.float32)[None, :]              # 1 at the source
    x = np.linspace(-1, 1, width, dtype=np.float32)[:, None]
    half = 0.05 + 0.95 * (1 - v)                                           # cone opening
    core = np.exp(-(x / (half * .5)) ** 2) + 0.35 * np.exp(-(x / (half * .12)) ** 2)
    along = (0.3 + 0.7 * v ** 1.4) * np.clip((1 - v) * 40, 0, 1)
    inten = core * along
    col = np.array((185, 205, 255), np.float32)
    rgb = inten[..., None] * col[None, None, :] * 1.05
    s = pg.Surface((width, length))
    pg.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8))
    return s


@lru_cache(maxsize=1)
def flare(radius: int = 90) -> pg.Surface:
    d = radius * 2
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    r = np.hypot(xx - radius, yy - radius) / radius
    inten = np.clip(1 - r, 0, 1) ** 2.2
    rgb = inten[..., None] * np.array((255, 230, 190), np.float32)
    s = pg.Surface((d, d))
    pg.surfarray.blit_array(s, rgb.astype(np.uint8))
    return s


# ---------------------------------------------------------------- city
def _tower(s: pg.Surface, x: float, w: float, top: float, k: float, rnd: random.Random,
           col: tuple, lights: list) -> None:
    """Art-deco tower: stepped setbacks and a spire."""
    base = H * k
    steps = rnd.randint(2, 4)
    cur_w, cur_top = w, top
    for i in range(steps):
        y = cur_top + (base - cur_top) * (i / steps) * 0.5
        pg.draw.rect(s, col, (x + (w - cur_w) / 2, y, cur_w, base - y + 2))
        cur_w *= rnd.uniform(.62, .8)
    tip = cur_top - rnd.uniform(30, 80) * k
    cx = x + w / 2
    pg.draw.polygon(s, col, [(cx - 4 * k, cur_top + 4), (cx + 4 * k, cur_top + 4), (cx, tip)])
    lights.append((cx, tip))
    gx, gy = 11 * k, 15 * k                                 # lit windows on a grid
    for row in range(int((base - top) * .75 / gy)):
        for col in range(int(w * .8 / gx)):
            if rnd.random() < .07:
                wx = x + w * .1 + col * gx
                wy = top + (base - top) * .25 + row * gy
                pg.draw.rect(s, (255, 205, 120) if rnd.random() < .8 else (180, 210, 255),
                             (wx, wy, 3 * k, 5 * k))


@lru_cache(maxsize=1)
def city() -> tuple[pg.Surface, list[tuple[float, float]], pg.Rect]:
    """Dark skyline at both sides rendered at CITY_ZOOM (cropped to its content),
    spire light spots (crop coords) and the crop rect in the zoomed layer."""
    k = CITY_ZOOM
    s = pg.Surface((int(W * k), int(H * k)), pg.SRCALPHA)
    rnd = random.Random(7)
    lights: list[tuple[float, float]] = []
    for layer, col, y0 in ((0, (40, 26, 58), 560), (1, (14, 10, 26), 620)):
        for side in (0, 1):
            x = 0.0
            while x < W * .36:
                w = rnd.uniform(60, 150) * (1.2 if layer else 1)
                top = rnd.uniform(y0, y0 + 220) - (W * .36 - x) * (.45 if layer else .3)
                px = x if side == 0 else W - x - w
                _tower(s, px * k, w * k, top * k, k, rnd, col, lights if layer else [])
                x += w * rnd.uniform(.75, 1.05)
    box = s.get_bounding_rect()
    crop = s.subsurface(box).copy()
    return crop, [(x - box.x, y - box.y) for x, y in lights], box


@lru_cache(maxsize=1)
def floor() -> pg.Surface:
    """Ground in front of the city: dark gradient with a warm glow under the monument."""
    fh = 700
    y = np.linspace(0, 1, fh, dtype=np.float32)[None, :]
    x = np.linspace(-1, 1, W, dtype=np.float32)[:, None]
    base = np.array((26, 16, 36), np.float32) * (1 - y[..., None] * .85)
    glow = np.exp(-(x / .3) ** 2 - (y / .06) ** 2)[..., None] * np.array((80, 50, 18), np.float32)
    s = pg.Surface((W, fh))
    pg.surfarray.blit_array(s, np.clip(base + glow, 0, 255).astype(np.uint8))
    return s


@lru_cache(maxsize=1)
def vignette() -> pg.Surface:
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    r = np.hypot((xx - W / 8) / (W / 8), (yy - H / 8) / (H / 8))
    a = (np.clip((r - .75) / .7, 0, 1) ** 1.5 * 210).T
    s = pg.Surface((W // 4, H // 4), pg.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pg.surfarray.pixels_alpha(s)[...] = a.astype(np.uint8)
    return pg.transform.smoothscale(s, (W, H))


# ---------------------------------------------------------------- logo
def _line_layout() -> list[tuple[str, float, float, float]]:
    """(char, x, y, height) of every glyph at zoom 1, centred on screen."""
    out, y = [], float(LOGO_TOP)
    for text, h, small in LINES:
        chars = [(c, h) for c in text] + [(c, h * .5) for c in small]
        widths = [glyph(c)[1] * hh for c, hh in chars]
        total = sum(widths) + TRACK * h * (len(chars) - 1)
        x = W / 2 - total / 2
        for (c, hh), w in zip(chars, widths):
            out.append((c, x, y, hh))
            x += w + TRACK * h
        y += h + LINE_GAP
    return out


def _pedestal(bottom_text: float) -> list[tuple[float, float, float, float]]:
    """Base boxes (x0, y0, x1, y1) at zoom 1: cornice, ribbed plinth, three steps."""
    y = bottom_text + 16
    boxes = [(W / 2 - 350, y, W / 2 + 350, y + 18)]           # cornice
    y += 18
    boxes.append((W / 2 - 322, y, W / 2 + 322, y + 92))       # plinth with pillars
    y += 92
    half = 322
    for _ in range(3):                                         # steps
        half += 52
        boxes.append((W / 2 - half, y, W / 2 + half, y + 24))
        y += 24
    return boxes


def ground_y() -> float:
    """Screen y (zoom 1) where the monument stands on the ground."""
    glyphs = _line_layout()
    return _pedestal(max(y + h for _, _, y, h in glyphs))[-1][3]


@lru_cache(maxsize=1)
def logo() -> tuple[pg.Surface, pg.Rect]:
    """The monument, and its rect in the screen zoomed by LOGO_ZOOM about the centre."""
    z, ss = LOGO_ZOOM, 2
    glyphs = _line_layout()
    boxes = _pedestal(max(y + h for _, _, y, h in glyphs))

    def zc(x: float, y: float) -> tuple[float, float]:
        return (W / 2 + (x - W / 2) * z, H / 2 + (y - H / 2) * z)
    pts = [zc(gx, gy) for _, gx, gy, _ in glyphs] + [zc(gx + glyph(c)[1] * gh, gy + gh) for c, gx, gy, gh in glyphs]
    pts += [zc(b[0], b[1]) for b in boxes] + [zc(b[2], b[3]) for b in boxes]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    pad = int(DEPTH * z) + 10
    crop = pg.Rect(int(x0) - pad, int(y0) - 10, int(x1 - x0) + pad + 20, int(y1 - y0) + pad + 20)

    def tr(x: float, y: float) -> tuple[float, float]:
        X, Y = zc(x, y)
        return ((X - crop.x) * ss, (Y - crop.y) * ss)
    letters = pg.Surface((crop.w * ss, crop.h * ss))
    base = pg.Surface((crop.w * ss, crop.h * ss))
    for ch, gx, gy, h in glyphs:
        ops, _ = glyph(ch)
        for op, poly in ops:
            pg.draw.polygon(letters, (255, 255, 255) if op == "+" else (0, 0, 0),
                            [tr(gx + px * h, gy + py * h) for px, py in poly])
    for bx0, by0, bx1, by1 in boxes:
        pg.draw.polygon(base, (255, 255, 255), [tr(bx0, by0), tr(bx1, by0), tr(bx1, by1), tr(bx0, by1)])
    ml = pg.surfarray.array_red(pg.transform.smoothscale(letters, crop.size)).astype(np.float32) / 255
    mb = pg.surfarray.array_red(pg.transform.smoothscale(base, crop.size)).astype(np.float32) / 255
    return _extrude(ml, mb, boxes, glyphs, z, crop), crop


def _normals(mask: np.ndarray, r: int) -> tuple[np.ndarray, np.ndarray]:
    b = blur(mask, r)
    gx, gy = np.gradient(b)                       # arrays are (x, y)
    n = np.hypot(gx, gy) + 1e-6
    return -gx / n * np.clip(n * r * 2, 0, 1), -gy / n * np.clip(n * r * 2, 0, 1)


def _extrude(ml: np.ndarray, mb: np.ndarray, boxes, glyphs, z: float, crop: pg.Rect) -> pg.Surface:
    mask = np.maximum(ml, mb)
    w, h = mask.shape
    nx, ny = _normals(mask, 3)
    # side walls: left faces catch the dusk light, undersides stay dark
    lit = 0.28 + 0.62 * np.clip(-nx, 0, 1) + 0.12 * np.clip(-ny, 0, 1)
    ys = np.linspace(0, 1, h, dtype=np.float32)[None, :]              # 0 top .. 1 bottom of the crop
    side_base = np.where((mb > ml)[..., None], np.array((104, 64, 26), np.float32),
                         np.array((136, 84, 24), np.float32))
    side = side_base * (lit * (1.08 - 0.25 * ys))[..., None]
    out = pg.Surface((w, h), pg.SRCALPHA)
    depth = int(DEPTH * z)
    bands = 6
    layers = []
    for b in range(bands):                       # pre-darkened copies, far = darker
        k = 1.0 - 0.5 * (b / (bands - 1)) ** 1.2
        layer = pg.Surface((w, h), pg.SRCALPHA)
        pg.surfarray.blit_array(layer, np.clip(side * k, 0, 255).astype(np.uint8))
        pg.surfarray.pixels_alpha(layer)[...] = (mask * 255).astype(np.uint8)
        layers.append(layer)
    for d in range(depth, 0, -1):
        band = min(bands - 1, int(d / depth * bands))
        out.blit(layers[band], (round(EXTRUDE[0] * d), round(EXTRUDE[1] * d)))
    out.blit(_front(ml, mb, mask, boxes, glyphs, z, crop), (0, 0))
    ground = int(H / 2 + (boxes[-1][3] - H / 2) * z) - crop.y       # it stands on the ground
    if 0 <= ground < h:
        pg.surfarray.pixels_alpha(out)[:, ground:] = 0
    return _keystone(out, ground)


def _keystone(surf: pg.Surface, ground: int, top_squeeze: float = .09, right_drop: float = .05,
              strip: int = 2) -> pg.Surface:
    """Fake a low camera on the left with thin strips (cheap, no numpy):
    rows get narrower toward the top, columns shorter toward the right. The
    ground line stays straight."""
    w, h = surf.get_size()
    gl = max(1, min(h, ground))
    rows = pg.Surface((w, h), pg.SRCALPHA)
    for y in range(0, gl, strip):                    # 1) top recedes: narrower rows
        k = 1 - top_squeeze * (1 - y / gl)
        sw = max(1, round(w * k))
        piece = pg.transform.smoothscale(surf.subsurface((0, y, w, min(strip, gl - y))), (sw, min(strip, gl - y)))
        rows.blit(piece, ((w - sw) // 2, y))
    out = pg.Surface((w, h), pg.SRCALPHA)
    for x in range(0, w, strip):                     # 2) right side further: shorter columns
        k = 1 - right_drop * (x / w)
        sh = max(1, round(gl * k))
        cw = min(strip, w - x)
        piece = pg.transform.smoothscale(rows.subsurface((x, 0, cw, gl)), (cw, sh))
        out.blit(piece, (x, gl - sh))
    return out


def _front(ml, mb, mask, boxes, glyphs, z: float, crop: pg.Rect) -> pg.Surface:
    w, h = mask.shape
    xs = np.arange(w, dtype=np.float32)[:, None] + crop.x          # zoomed screen coords
    ys = np.arange(h, dtype=np.float32)[None, :] + crop.y
    # gold: per glyph box, bright at the top of the letters -> deep amber at the bottom
    t = np.zeros((w, h), np.float32)
    for ch, gx, gy, gh in glyphs:
        x0 = int(W / 2 + (gx - W / 2) * z) - crop.x - 4
        x1 = int(W / 2 + (gx + glyph(ch)[1] * gh - W / 2) * z) - crop.x + 4
        y0 = H / 2 + (gy - H / 2) * z - crop.y
        y1 = H / 2 + (gy + gh - H / 2) * z - crop.y
        ry = np.arange(max(0, int(y0) - 2), min(h, int(y1) + 3))
        t[max(0, x0):max(0, x1), ry[0]:ry[-1] + 1] = np.clip((ry - y0) / (y1 - y0), 0, 1)[None, :]
    top, mid, bot = (np.array(c, np.float32) for c in ((255, 244, 178), (250, 196, 72), (176, 104, 22)))
    t3 = t[..., None]
    gold = np.where(t3 < .5, top + (mid - top) * (t3 / .5), mid + (bot - mid) * ((t3 - .5) / .5))
    # bronze base: pillars on the plinth (lit faces, dark recesses), lit step edges
    def zy(v: float) -> float:
        return H / 2 + (v - H / 2) * z
    by = np.clip((ys - zy(boxes[0][1])) / (220 * z), 0, 1)
    shade = np.ones((w, h), np.float32) * (1.05 - 0.4 * by)
    px0, py0, _, py1 = boxes[1]
    u = ((xs - (W / 2 + (px0 - W / 2) * z)) / (64 * z)) % 1.0
    plinth = (ys > zy(py0) + 5 * z) & (ys < zy(py1) - 3 * z)
    pillar = np.where(u < .05, 1.3, np.where(u < .72, 1.18 - 0.45 * (u / .72),         # round-ish column
                                             np.where(u < .78, .32, .5)))
    shade = np.where(plinth, shade * pillar, shade)
    for bx0, by0, bx1, by1 in boxes:                           # bright top edge of every slab
        shade = np.where((ys >= zy(by0)) & (ys < zy(by0) + 3.5 * z), shade * 1.3, shade)
    bronze = np.array((232, 170, 72), np.float32) * shade[..., None]
    rgb = np.where((mb > ml)[..., None], bronze, gold)
    # bevel: light from the upper left on the inner edges, dark lower-right rims
    nx, ny = _normals(mask, 5)
    bev = np.clip(-nx * 0.55 - ny * 0.85, -1, 1)
    edge = 1 - blur(mask, 4)
    rgb = rgb * (1 + (0.55 * bev * np.clip(edge * 2.2, 0, 1)))[..., None]
    sheen = np.exp(-(((xs * 0.45 + ys) - (crop.y + h * 0.3 + crop.centerx * 0.45)) / (h * 0.06)) ** 2)
    rgb = rgb + sheen[..., None] * np.array((60, 50, 25), np.float32) * (mb <= ml)[..., None]
    rim = np.clip((0.5 - np.abs(mask - 0.5)) * 2, 0, 1)
    rgb = rgb * (1 - 0.45 * rim)[..., None]
    s = pg.Surface((w, h), pg.SRCALPHA)
    pg.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8))
    pg.surfarray.pixels_alpha(s)[...] = (mask * 255).astype(np.uint8)
    return s

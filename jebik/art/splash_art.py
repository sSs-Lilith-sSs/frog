"""Studio splash art: «21th / MANGO / CAT» golden monument, dusk sky, city, beams.

Everything is pre-rendered once (numpy allowed here, never per frame):

* :func:`sky` — deep blue -> purple -> orange dusk with clouds and stars;
* :func:`beam` — one searchlight cone (RGB, for additive blits);
* :func:`city` — dark towers at both sides (alpha layer);
* :func:`logo` — the extruded 3D monument text on a stepped base.

The splash scene only rotates beams and scales the city / logo layers.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
import pygame as pg

from .. import config
from .common import blur, lerp
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
    clouds = pg.Surface((W // 8, H // 8), pg.SRCALPHA)                    # soft cloud bands
    for _ in range(26):
        cy = rnd.uniform(.38, .7) * H / 8
        cx, w = rnd.uniform(-20, W / 8 + 20), rnd.uniform(30, 90)
        lit = (cy * 8 / H - .38) / .32
        col = lerp((50, 30, 80), (230, 110, 90), lit ** 1.5)
        pg.draw.ellipse(clouds, (*col, 150), (cx - w / 2, cy - 2, w, rnd.uniform(3, 7)))
    s.blit(pg.transform.smoothscale(clouds, (W, H)), (0, 0))
    return s


# ---------------------------------------------------------------- beam
@lru_cache(maxsize=1)
def beam(length: int = 1500, width: int = 300) -> pg.Surface:
    """Searchlight cone, source at the bottom centre, pointing up."""
    v = np.linspace(1, 0, length, dtype=np.float32)[None, :]              # 1 at the source
    x = np.linspace(-1, 1, width, dtype=np.float32)[:, None]
    half = 0.05 + 0.95 * (1 - v)                                           # cone opening
    core = np.exp(-(x / (half * .55)) ** 2)
    along = (0.25 + 0.75 * v ** 1.6) * np.clip((1 - v) * 40, 0, 1)
    inten = core * along
    col = np.array((170, 190, 255), np.float32)
    rgb = inten[..., None] * col[None, None, :] * 0.9
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
    for _ in range(int(w * (base - top) / 900 / k)):
        wx = x + rnd.uniform(.12, .88) * w
        wy = rnd.uniform(top + (base - top) * .25, base - 10 * k)
        pg.draw.rect(s, (255, 205, 120) if rnd.random() < .8 else (180, 210, 255),
                     (wx, wy, 3 * k, 4 * k))


@lru_cache(maxsize=1)
def city() -> tuple[pg.Surface, list[tuple[float, float]]]:
    """Dark skyline at both sides (rendered at CITY_ZOOM), plus spire light spots."""
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
    pg.draw.rect(s, (10, 8, 18), (0, int(HORIZON * k + 90 * k), s.get_width(), s.get_height()))
    return s, lights


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
    """Base boxes (x0, y0, x1, y1) at zoom 1: grooved plinth + three steps."""
    boxes, y = [], bottom_text + 18
    half = 330
    boxes.append((W / 2 - half, y, W / 2 + half, y + 64))
    y += 64
    for i in range(3):
        half += 46
        boxes.append((W / 2 - half, y, W / 2 + half, y + 26))
        y += 26
    return boxes


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
    return out


def _front(ml, mb, mask, boxes, glyphs, z: float, crop: pg.Rect) -> pg.Surface:
    w, h = mask.shape
    xs = np.arange(w, dtype=np.float32)[:, None] + crop.x          # zoomed screen coords
    ys = np.arange(h, dtype=np.float32)[None, :] + crop.y
    # gold: per text line, bright at the top of the letters -> deep amber at the bottom
    t = np.zeros((w, h), np.float32)
    for _, _, gy, gh in glyphs:
        y0 = H / 2 + (gy - H / 2) * z
        y1 = H / 2 + (gy + gh - H / 2) * z
        sel = (ys >= y0 - 2) & (ys <= y1 + 2)
        t = np.where(sel, np.clip((ys - y0) / (y1 - y0), 0, 1), t)
    top, mid, bot = (np.array(c, np.float32) for c in ((255, 244, 178), (250, 196, 72), (176, 104, 22)))
    t3 = t[..., None]
    gold = np.where(t3 < .5, top + (mid - top) * (t3 / .5), mid + (bot - mid) * ((t3 - .5) / .5))
    # bronze base: slightly darker gold, grooves on the plinth, lit step edges
    by = np.clip((ys - (H / 2 + (boxes[0][1] - H / 2) * z)) / (200 * z), 0, 1)[..., None]
    bronze = np.array((226, 166, 70), np.float32) * (1 - 0.35 * by) + np.zeros_like(xs)[..., None]
    x0 = W / 2 + (boxes[0][0] - W / 2) * z
    groove = (np.abs(((xs - x0) / (22 * z)) % 2 - 1) < 0.18) & \
             (ys > H / 2 + (boxes[0][1] + 8 - H / 2) * z) & (ys < H / 2 + (boxes[0][3] - 8 - H / 2) * z)
    bronze = np.where(groove[..., None], bronze * 0.55, bronze)
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

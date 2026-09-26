"""Shared drawing helpers: supersampling, fonts/text, small vector icons."""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable

import numpy as np
import pygame as pg

from .. import config

Color = tuple[int, ...]


def lerp(a: Color, b: Color, t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def blur(a: np.ndarray, k: int) -> np.ndarray:
    """Separable box blur (radius ``k``) with edge padding — from the mockup.

    Each pass runs a cumulative sum along the contiguous axis and transposes,
    which is several times faster than summing along axis 0."""
    if k <= 0:
        return a
    a = np.asarray(a, dtype=np.float32)
    for _ in range(2):
        p = np.pad(a, ((0, 0), (k + 1, k)), mode="edge")
        c = np.cumsum(p, axis=1, dtype=np.float32)
        a = np.ascontiguousarray(((c[:, 2 * k + 1:] - c[:, :-2 * k - 1]) / (2 * k + 1)).T)
    return a


# ---------------------------------------------------------------- supersampling
def smooth_down(src: pg.Surface, size: tuple[int, int]) -> pg.Surface:
    """Downscale with correct alpha (no dark fringes).

    Scales premultiplied colour, then un-premultiplies and bleeds nearby
    colour into fully transparent pixels, so later rotations / squashes of
    the sprite stay clean too.
    """
    size = (max(1, int(size[0])), max(1, int(size[1])))
    if not src.get_flags() & pg.SRCALPHA:
        return pg.transform.smoothscale(src, size)
    pre = src.premul_alpha()
    small = pg.transform.smoothscale(pre, size)
    rgb = pg.surfarray.array3d(small).astype(np.float32)
    alpha = pg.surfarray.array_alpha(small).astype(np.float32)
    a = alpha[..., None]
    straight = np.where(a > 0, rgb * 255.0 / np.maximum(a, 1.0), 0.0)
    # colour bleed for invisible pixels: a blurred copy of the premultiplied
    # sprite (down + up smoothscale), un-premultiplied
    tiny = pg.transform.smoothscale(small, (max(1, size[0] // 6), max(1, size[1] // 6)))
    soft = pg.transform.smoothscale(tiny, size)
    srgb = pg.surfarray.array3d(soft).astype(np.float32)
    sa = pg.surfarray.array_alpha(soft).astype(np.float32)[..., None]
    bleed = srgb * 255.0 / np.maximum(sa, 1.0)
    out_rgb = np.where(a > 0, straight, bleed)
    out = pg.Surface(size, pg.SRCALPHA)
    pg.surfarray.blit_array(out, np.clip(out_rgb, 0, 255).astype(np.uint8))
    pg.surfarray.pixels_alpha(out)[...] = alpha.astype(np.uint8)
    return out


def render_ss(size: tuple[int, int], draw: Callable[[pg.Surface, float], None],
              ss: int = config.SS_SPRITE) -> pg.Surface:
    """Draw ``draw(surface, ss)`` on a big transparent surface, scale down."""
    big = pg.Surface((int(size[0] * ss), int(size[1] * ss)), pg.SRCALPHA)
    draw(big, ss)
    return smooth_down(big, size)


# ---------------------------------------------------------------- text
@lru_cache(maxsize=64)
def font(size: int, bold: bool = True) -> pg.font.Font:
    return pg.font.Font(str(config.FONT_BOLD if bold else config.FONT_REGULAR), int(size))


@lru_cache(maxsize=1024)
def text_surface(text: str, size: int, color: Color = (255, 255, 255), bold: bool = True,
                 outline: Color | None = None, outline_w: int = 0) -> pg.Surface:
    """Rendered text (cached). With ``outline`` a round outline is added."""
    f = font(size, bold)
    img = f.render(text, True, color)
    if not outline:
        return img
    w = outline_w or max(2, size // 12)
    base = f.render(text, True, outline)
    out = pg.Surface((img.get_width() + 2 * w, img.get_height() + 2 * w), pg.SRCALPHA)
    steps = max(16, w * 6)
    for i in range(steps):
        ang = 2 * math.pi * i / steps
        out.blit(base, (w + round(w * math.cos(ang)), w + round(w * math.sin(ang))))
    for r in range(1, w):
        out.blit(base, (w - r, w)); out.blit(base, (w + r, w))
        out.blit(base, (w, w - r)); out.blit(base, (w, w + r))
    out.blit(img, (w, w))
    return out


def draw_text(surf: pg.Surface, text: str, size: int, pos: tuple[float, float],
              color: Color = (255, 255, 255), bold: bool = True, anchor: str = "center",
              outline: Color | None = None, outline_w: int = 0, alpha: int = 255) -> pg.Rect:
    img = text_surface(text, int(size), tuple(color), bold,
                       tuple(outline) if outline else None, outline_w)
    rect = img.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def fit_size(text: str, size: int, max_w: int, bold: bool = True, min_size: int = 12) -> int:
    """Largest font size <= ``size`` that fits ``text`` into ``max_w``."""
    while size > min_size and font(size, bold).size(text)[0] > max_w:
        size -= 1
    return size


def wrap(text: str, size: int, max_w: int, bold: bool = False) -> list[str]:
    lines: list[str] = []
    f = font(size, bold)
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = f"{cur} {word}".strip()
            if cur and f.size(test)[0] > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = test
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- icons
def heart(s: pg.Surface, x: float, y: float, col: Color, sc: float = 1.0) -> None:
    """Heart from the mockup: two circles + triangle (x,y = left lobe)."""
    pg.draw.circle(s, col, (x, y), 11 * sc)
    pg.draw.circle(s, col, (x + 15 * sc, y), 11 * sc)
    pg.draw.polygon(s, col, [(x - 11 * sc, y + 4 * sc), (x + 26 * sc, y + 4 * sc),
                             (x + 7.5 * sc, y + 24 * sc)])


@lru_cache(maxsize=64)
def heart_sprite(size: int, col: Color, shine: bool = True) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        sc = size * ss / 40
        heart(s, 12.5 * sc, 12 * sc, col, sc)
        if shine:
            light = lerp(col, (255, 255, 255), 0.55)
            pg.draw.ellipse(s, light, (5 * sc, 5 * sc, 8 * sc, 6 * sc))
    return render_ss((size, size), draw)


def star_points(cx: float, cy: float, r: float, inner: float = 0.47,
                rot: float = -math.pi / 2) -> list[tuple[float, float]]:
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * inner
        a = rot + i * math.pi / 5
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


@lru_cache(maxsize=64)
def star_sprite(size: int, filled: bool = True, outline: Color = (150, 100, 20)) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        c = size * ss / 2
        pts = star_points(c, c * 1.04, c * 0.95)
        col = config.C_STAR if filled else config.C_STAR_EMPTY
        pg.draw.polygon(s, col, pts)
        if filled:
            pg.draw.polygon(s, (255, 235, 150), star_points(c - c * .08, c * .98, c * .45))
        pg.draw.polygon(s, outline if filled else (160, 155, 140), pts, max(1, int(size * ss / 16)))
    return render_ss((size, size), draw)


@lru_cache(maxsize=32)
def lock_sprite(size: int, col: Color = (90, 95, 90)) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        u = size * ss / 20
        pg.draw.rect(s, col, (5 * u, 2 * u, 10 * u, 12 * u), int(2.2 * u), border_radius=int(5 * u))
        pg.draw.rect(s, col, (3 * u, 8.5 * u, 14 * u, 10.5 * u), border_radius=int(2.5 * u))
        pg.draw.circle(s, (235, 235, 225), (10 * u, 12.8 * u), 1.7 * u)
        pg.draw.rect(s, (235, 235, 225), (9.3 * u, 13 * u, 1.4 * u, 3.4 * u))
    return render_ss((size, size), draw)


def triangle(s: pg.Surface, center: tuple[float, float], size: float, direction: int,
             col: Color) -> None:
    """Filled triangle pointing up/right/down/left (0..3)."""
    cx, cy = center
    ang = -math.pi / 2 + direction * math.pi / 2
    pts = [(cx + size * math.cos(ang + k * 2 * math.pi / 3),
            cy + size * math.sin(ang + k * 2 * math.pi / 3)) for k in range(3)]
    pg.draw.polygon(s, col, pts)


@lru_cache(maxsize=32)
def triangle_sprite(size: int, direction: int, col: Color) -> pg.Surface:
    return render_ss((size, size), lambda s, ss: triangle(
        s, (size * ss / 2, size * ss / 2), size * ss * 0.45, direction, col))


@lru_cache(maxsize=16)
def arrow_up_sprite(size: int, col: Color) -> pg.Surface:
    """Hollow 'shift' style arrow for the super-jump icon."""
    def draw(s: pg.Surface, ss: float) -> None:
        u = size * ss / 20
        pts = [(10 * u, 2 * u), (18 * u, 10.5 * u), (13.5 * u, 10.5 * u), (13.5 * u, 17 * u),
               (6.5 * u, 17 * u), (6.5 * u, 10.5 * u), (2 * u, 10.5 * u)]
        pg.draw.polygon(s, col, pts, max(1, int(2.2 * u)))
    return render_ss((size, size), draw)


@lru_cache(maxsize=512)
def disc_sprite(radius: float, col: Color) -> pg.Surface:
    d = max(2, int(math.ceil(radius * 2)) + 2)
    return render_ss((d, d), lambda s, ss: pg.draw.circle(
        s, col, (d * ss / 2, d * ss / 2), radius * ss))


@lru_cache(maxsize=16)
def ring_sprite(radius: int, width: int, col: Color) -> pg.Surface:
    d = radius * 2 + 4
    return render_ss((d, d), lambda s, ss: pg.draw.circle(
        s, col, (d * ss / 2, d * ss / 2), radius * ss, int(width * ss)))


@lru_cache(maxsize=512)
def arc_ring(radius: int, width: int, frac: float, col: Color, bg: Color) -> pg.Surface:
    """Cooldown ring: background disc + progress arc from 12 o'clock clockwise.

    Cached — callers should quantise ``frac`` (e.g. to 1/64 steps)."""
    d = radius * 2 + 4
    frac = max(0.0, min(1.0, frac))

    def draw(s: pg.Surface, ss: float) -> None:
        c = (d * ss / 2, d * ss / 2)
        pg.draw.circle(s, bg, c, radius * ss)
        if frac <= 0:
            return
        r_out, r_in = radius * ss, (radius - width) * ss
        n = max(3, int(64 * frac))
        a0 = -math.pi / 2
        pts = [(c[0] + r_out * math.cos(a0 + 2 * math.pi * frac * i / n),
                c[1] + r_out * math.sin(a0 + 2 * math.pi * frac * i / n)) for i in range(n + 1)]
        pts += [(c[0] + r_in * math.cos(a0 + 2 * math.pi * frac * i / n),
                 c[1] + r_in * math.sin(a0 + 2 * math.pi * frac * i / n)) for i in range(n, -1, -1)]
        pg.draw.polygon(s, col, pts)
        for a in (a0, a0 + 2 * math.pi * frac):          # rounded caps
            rm = (r_out + r_in) / 2
            pg.draw.circle(s, col, (c[0] + rm * math.cos(a), c[1] + rm * math.sin(a)),
                           (r_out - r_in) / 2)
    return render_ss((d, d), draw, ss=3)


@lru_cache(maxsize=256)
def rounded_panel(size: tuple[int, int], fill: Color, border: Color | None = None,
                  radius: int = 28, border_w: int = 4, shadow: Color | None = None,
                  shadow_off: int = 8) -> pg.Surface:
    """Anti-aliased rounded rectangle (optionally with a drop 'shadow' slab)."""
    w, h = size
    total = (w, h + (shadow_off if shadow else 0))

    def draw(s: pg.Surface, ss: float) -> None:
        r = int(radius * ss)
        if shadow:
            pg.draw.rect(s, shadow, (0, shadow_off * ss, w * ss, h * ss), border_radius=r)
        pg.draw.rect(s, fill, (0, 0, w * ss, h * ss), border_radius=r)
        if border:
            pg.draw.rect(s, border, (0, 0, w * ss, h * ss), int(border_w * ss), border_radius=r)
    return render_ss(total, draw, ss=3)

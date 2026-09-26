"""Soft glows (numpy, rendered once and cached by the callers)."""
from __future__ import annotations

import numpy as np
import pygame as pg


def glow_sprite(radius: float, col=(255, 240, 160), max_alpha: int = 120,
                power: float = 1.8) -> pg.Surface:
    """Soft round glow: radial alpha gradient."""
    d = int(radius * 2) + 2
    g = pg.Surface((d, d), pg.SRCALPHA)
    g.fill((*col, 0))
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    r = np.hypot(xx - d / 2 + .5, yy - d / 2 + .5) / radius
    alpha = np.clip(1 - r, 0, 1) ** power * max_alpha
    pg.surfarray.pixels_alpha(g)[...] = alpha.T.astype(np.uint8)
    return g


def additive_glow(radius: float, col=(255, 235, 150), levels: int = 8,
                  power: float = 1.6) -> list[pg.Surface]:
    """Light for BLEND_RGB_ADD blits, pre-rendered at ``levels`` intensities."""
    d = int(radius * 2) + 2
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    r = np.hypot(xx - d / 2 + .5, yy - d / 2 + .5) / radius
    inten = (np.clip(1 - r, 0, 1) ** power).T[..., None]
    frames = []
    for i in range(levels):
        s = pg.Surface((d, d))
        rgb = inten * np.array(col, np.float32) * ((i + 1) / levels)
        pg.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8))
        frames.append(s)
    return frames

"""Water-world art: field (pools + lily pads), snake, pike, heron, whale, icons.

Importing this package registers the enemy renderers.
"""
from __future__ import annotations

import pygame as pg

from ....art.common import render_ss
from ....art.world_art import WorldArt
from . import predator_art, snake_art, whale_art  # noqa: F401  (register the renderers)
from .field import WaterField


class WaterArt(WorldArt):
    field_cls = WaterField

    def icon(self, size: int) -> pg.Surface:
        def draw(s: pg.Surface, ss: float) -> None:      # water drop
            u = size * ss / 20
            pg.draw.circle(s, (70, 160, 215), (10 * u, 12.5 * u), 6 * u)
            pg.draw.polygon(s, (70, 160, 215), [(10 * u, 1.5 * u), (4.4 * u, 10.5 * u), (15.6 * u, 10.5 * u)])
            pg.draw.circle(s, (190, 230, 250), (8 * u, 13 * u), 1.8 * u)
        return render_ss((size, size), draw)

    def boss_icon(self, kind: str, size: int) -> pg.Surface | None:
        return whale_art.whale_icon(size) if kind == "whale" else None


ART = WaterArt()

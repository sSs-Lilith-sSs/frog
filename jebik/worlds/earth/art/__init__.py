"""Earth-world art: meadow, grass tiles over organic pits, stumps, burrow exit,
hedgehog / fox / mole / boar renderers — ported from the approved mockups."""
from __future__ import annotations

import pygame as pg

from ....art.common import render_ss
from ....art.world_art import WorldArt
from . import renderers  # noqa: F401  (registers the enemy renderers)
from .field import EarthField
from .sprites import boar_face


class EarthArt(WorldArt):
    field_cls = EarthField

    def icon(self, size: int) -> pg.Surface:
        def draw(s: pg.Surface, ss: float) -> None:      # grass tuft on a dirt mound
            u = size * ss / 20
            pg.draw.ellipse(s, (120, 84, 52), (3 * u, 15.5 * u, 14 * u, 4 * u))
            pg.draw.ellipse(s, (150, 106, 66), (3 * u, 15 * u, 14 * u, 3.5 * u))
            for dx, h, lean in ((-5, 12, -3), (0, 16, 0), (5, 11, 3), (-2, 9, -1), (3, 13, 1)):
                pg.draw.polygon(s, (90, 160, 60), [((10 + dx - 1.6) * u, 17 * u), ((10 + dx + 1.6) * u, 17 * u),
                                                   ((10 + dx + lean) * u, (17 - h) * u)])
        return render_ss((size, size), draw)

    def boss_icon(self, kind: str, size: int) -> pg.Surface | None:
        return boar_face(size) if kind == "boar" else None


ART = EarthArt()

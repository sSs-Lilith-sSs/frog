"""Composite "backdrop + resting tiles" cache for slow blitters (browser build).

Drawing a level blits ~100-250 alpha tile sprites every frame. That is cheap
natively but slow in WebAssembly (no SIMD alpha blitters), so the web build
keeps one opaque copy of the static backdrop with every *stable* tile (no
hazard / dip / moving-row effect) already drawn on it, and per frame blits that
copy plus only the tiles that are changing. The copy is rebuilt whenever the
set of stable tiles or their images changes; a field whose tiles animate all
the time (bobbing lily pads) makes it rebuild too often and switches it off.
Only usable when nothing is drawn between the backdrop and the tiles (no
"under" enemies, no rings) and the screen does not shake — the caller checks.
"""
from __future__ import annotations

import pygame as pg

from .. import paths

ENABLED: bool | None = None   # None: only in the browser (desktop blits fast enough)
WINDOW = 30                   # frames looked at by the thrash check
MAX_REBUILDS = 8              # rebuilds within WINDOW frames that switch it off


def enabled() -> bool:
    return paths.is_web() if ENABLED is None else ENABLED


class TileCache:
    def __init__(self, field_art) -> None:
        from .field import FieldRenderer
        self.art = field_art
        self.sig: tuple | None = None
        self.surface: pg.Surface | None = None
        self.history: list[bool] = []       # recent frames: rebuilt?
        # a world that draws its tiles itself (not via tile_blits) cannot be cached
        self.off = type(field_art).draw_tiles is not FieldRenderer.draw_tiles
        self.rebuilds = 0

    def frame(self, world, skip) -> pg.Surface | None:
        """The composite for this frame (None: draw the normal way)."""
        if self.off:
            return None
        blits = self.art.tile_blits(world, (0, 0), skip)
        sig = tuple((id(img), pos) for img, pos, _clip, stable in blits if stable)
        rebuilt = sig != self.sig
        if rebuilt:
            comp = self.art.static().copy()
            for img, pos, _clip, stable in blits:
                if stable:
                    comp.blit(img, pos)
            self.surface, self.sig = comp, sig
            self.rebuilds += 1
        self.history = (self.history + [rebuilt])[-WINDOW:]
        if sum(self.history) > MAX_REBUILDS:
            self.off, self.surface = True, None
            return None
        return self.surface

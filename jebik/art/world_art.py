"""WorldArt: what a world's art package gives the renderer, and its loader.

Each ``jebik/worlds/<id>/art/__init__.py`` defines ``ART = MyWorldArt()``
(a subclass of :class:`WorldArt`) and imports its enemy renderers so they
register. Scenes call :func:`art_for` — the module is imported lazily, the
first time the world is drawn.
"""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import TYPE_CHECKING

import pygame as pg

from ..game.grid import Level
from .common import render_ss
from .field import FieldRenderer

if TYPE_CHECKING:
    from ..story import Card


class WorldArt:
    field_cls: type[FieldRenderer] = FieldRenderer

    def field(self, level: Level, cs: int, rect: pg.Rect) -> FieldRenderer:
        """A fresh renderer for one level (holds per-level caches)."""
        return self.field_cls(level, cs, rect)

    def icon(self, size: int) -> pg.Surface:
        """World picture for level select / cutscenes."""
        return render_ss((size, size), lambda s, ss: pg.draw.circle(
            s, (200, 200, 200), (size * ss / 2, size * ss / 2), size * ss * .4))

    def boss_icon(self, kind: str, size: int) -> pg.Surface | None:
        """Small portrait for the HUD boss pill (None: generic crown)."""
        return None

    def draw_story(self, card: "Card", surf: pg.Surface, rect: pg.Rect, t: float) -> bool:
        """Draw a story card illustration into ``rect``; False = generic art."""
        return False


@lru_cache(maxsize=None)
def art_for(world_id: str) -> WorldArt:
    from ..worlds import world_by_id
    module = importlib.import_module(world_by_id(world_id).art_module)
    art = getattr(module, "ART", None)
    if not isinstance(art, WorldArt):
        raise TypeError(f"{module.__name__}.ART must be a WorldArt instance")
    return art

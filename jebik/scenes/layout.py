"""Field layout on the 1920x1080 logical screen (cell size + field rect)."""
from __future__ import annotations

import pygame as pg

from .. import config
from ..game.grid import Level

W, H = config.SCREEN_W, config.SCREEN_H


def top_space(level: Level) -> int:
    """Pixels above the field: HUD bar + boss pill + the level's own reserve."""
    boss = config.BOSS_PILL_RESERVE if level.boss else 0
    return config.HUD_H + boss + level.top_reserve


def cell_size(level: Level) -> int:
    """The level's fixed ``cell:`` or the biggest even size <= MAX_CELL that fits."""
    if level.cell:
        return level.cell
    fit_w = (W - 2 * config.FIELD_MARGIN_X) // level.width
    fit_h = (H - top_space(level) - 2 * config.FIELD_MARGIN_Y) // level.height
    cs = min(config.MAX_CELL, fit_w, fit_h)
    return max(40, cs - cs % 2)


def field_rect(level: Level, cs: int) -> pg.Rect:
    fw, fh = level.width * cs, level.height * cs
    top = top_space(level)
    return pg.Rect((W - fw) // 2, top + (H - top - fh) // 2, fw, fh)

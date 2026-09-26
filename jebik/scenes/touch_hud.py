"""On-screen touch buttons: ⏸ pause (bottom-left) and ⇧ superjump (bottom-right)."""
from __future__ import annotations

import math

import pygame as pg

from .. import config
from ..art.common import arc_ring, arrow_up_sprite, disc_sprite, ring_sprite
from ..game.gestures import Circle, TouchPad

R = config.TOUCH_BUTTON_R
M = config.TOUCH_BUTTON_MARGIN
PAUSE_CENTER = (M + R, config.SCREEN_H - M - R)
SUPER_CENTER = (config.SCREEN_W - M - R, config.SCREEN_H - M - R)


def make_touchpad() -> TouchPad:
    return TouchPad(Circle(PAUSE_CENTER, R), Circle(SUPER_CENTER, R))


def _blit_alpha(surf: pg.Surface, img: pg.Surface, center: tuple[float, float], alpha: int) -> None:
    img = img.copy()
    img.set_alpha(alpha)
    surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


def _base(surf: pg.Surface, center: tuple[int, int], fill: tuple, alpha: int) -> None:
    _blit_alpha(surf, disc_sprite(R, fill), center, alpha)
    _blit_alpha(surf, ring_sprite(R, 4, config.C_HUD_LINE), center, alpha)


def draw_touch_buttons(surf: pg.Surface, pad: TouchPad, super_frac: float, t: float) -> None:
    alpha = config.TOUCH_BUTTON_ALPHA
    # pause: two rounded bars
    _base(surf, PAUSE_CENTER, config.C_HUD_BG, alpha)
    bars = pg.Surface((2 * R, 2 * R), pg.SRCALPHA)
    for dx in (-16, 16):
        pg.draw.rect(bars, config.C_HUD_TEXT, (R + dx - 8, R - 26, 16, 52), border_radius=6)
    _blit_alpha(surf, bars, PAUSE_CENTER, 235)
    # superjump: cooldown ring + arrow, glowing while armed
    armed = pad.super_armed
    ready = super_frac >= 1
    fill = config.C_BUTTON_HOT if armed else config.C_HUD_BG
    _base(surf, SUPER_CENTER, fill, 230 if armed else alpha)
    if armed:
        pulse = 0.5 + 0.5 * math.sin(t * 8)
        _blit_alpha(surf, ring_sprite(R + 8, 5, (255, 240, 170)), SUPER_CENTER, int(120 + 120 * pulse))
    frac = round(max(0.0, min(1.0, super_frac)) * 64) / 64
    col = (120, 220, 90) if ready else (95, 160, 85)
    ring = arc_ring(R - 12, 8, frac, col, (60, 90, 70))
    _blit_alpha(surf, ring, SUPER_CENTER, 235 if armed else 200)
    arrow_col = (255, 250, 220) if armed else ((235, 245, 230) if ready else (150, 170, 150))
    _blit_alpha(surf, arrow_up_sprite(52, arrow_col), SUPER_CENTER, 255)

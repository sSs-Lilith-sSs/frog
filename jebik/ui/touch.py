"""pygame side of touch input: finger events -> logical pixels / mouse clicks.

SDL also synthesizes mouse events from touches (``event.touch`` is true, or
``event.which`` is ``SDL_TOUCH_MOUSEID``); the app drops those and handles
the finger events itself, so nothing is handled twice.
"""
from __future__ import annotations

import pygame as pg

from .. import config
from ..game.gestures import to_logical

TOUCH_MOUSEID = 0xFFFFFFFF          # SDL_TOUCH_MOUSEID ((Uint32)-1)
FINGER_EVENTS = (pg.FINGERDOWN, pg.FINGERMOTION, pg.FINGERUP)
MOUSE_EVENTS = (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION, pg.MOUSEWHEEL)


def is_touch_mouse(event: pg.event.Event) -> bool:
    """True for a mouse event SDL synthesized from a touch."""
    if event.type not in MOUSE_EVENTS:
        return False
    return bool(getattr(event, "touch", False)) or getattr(event, "which", None) in (TOUCH_MOUSEID, -1)


def window_size() -> tuple[int, int]:
    try:
        return pg.display.get_window_size()
    except (AttributeError, pg.error):
        return (config.SCREEN_W, config.SCREEN_H)


def localize(event: pg.event.Event) -> pg.event.Event:
    """Copy of a finger event with ``pos`` in logical pixels."""
    pos = to_logical(event.x, event.y, window_size())
    return pg.event.Event(event.type, finger_id=getattr(event, "finger_id", 0),
                          x=event.x, y=event.y, pos=pos)


class FingerMouse:
    """Turns the first finger into left-button mouse events (menus, sliders)."""

    def __init__(self) -> None:
        self.finger: int | None = None

    def convert(self, event: pg.event.Event) -> list[pg.event.Event]:
        fid, pos = event.finger_id, event.pos
        motion = pg.event.Event(pg.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(1, 0, 0))
        if event.type == pg.FINGERDOWN:
            if self.finger is not None:
                return []
            self.finger = fid
            return [motion, pg.event.Event(pg.MOUSEBUTTONDOWN, pos=pos, button=1)]
        if fid != self.finger:
            return []
        if event.type == pg.FINGERMOTION:
            return [motion]
        self.finger = None
        return [pg.event.Event(pg.MOUSEBUTTONUP, pos=pos, button=1)]

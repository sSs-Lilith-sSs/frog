"""Touch gestures, independent of pygame: swipes, taps and on-screen buttons.

Fingers are fed in logical screen pixels with a timestamp (seconds). The
:class:`TouchPad` turns them into game actions:

* swipe (at least ``TOUCH_SWIPE_MIN_DIST`` within ``TOUCH_SWIPE_MAX_TIME``)
  -> ``("move", direction, superjump)``; keeping the finger down and swiping
  again chains further hops;
* short tap on the field -> ``("tongue",)``;
* finger down on the pause button -> ``("pause",)``;
* finger down on the superjump button arms (or disarms) the superjump: the
  next swipe becomes a superjump.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .. import config

Point = tuple[float, float]
Action = tuple


def to_logical(nx: float, ny: float, window: tuple[int, int],
               logical: tuple[int, int] = (config.SCREEN_W, config.SCREEN_H)) -> tuple[int, int]:
    """Normalized window coords (SDL finger events) -> logical pixels.

    The logical screen is scaled to fit the window keeping its aspect ratio
    (pygame.SCALED letterboxes), so the bars are taken into account.
    """
    ww, wh = max(1, window[0]), max(1, window[1])
    lw, lh = logical
    scale = min(ww / lw, wh / lh)
    ox, oy = (ww - lw * scale) / 2, (wh - lh * scale) / 2
    x = (nx * ww - ox) / scale
    y = (ny * wh - oy) / scale
    return (int(max(0, min(lw - 1, x))), int(max(0, min(lh - 1, y))))


def swipe_direction(dx: float, dy: float) -> int:
    """0 up, 1 right, 2 down, 3 left (screen y grows downwards)."""
    if abs(dx) > abs(dy):
        return 1 if dx > 0 else 3
    return 2 if dy > 0 else 0


@dataclass
class Finger:
    start: Point
    t0: float
    pos: Point
    moved: bool = False        # swiped or dragged: no longer a tap
    button: str | None = None  # finger went down on an on-screen button


@dataclass
class Circle:
    center: Point
    radius: float

    def contains(self, p: Point) -> bool:
        return math.hypot(p[0] - self.center[0], p[1] - self.center[1]) <= self.radius


class TouchPad:
    def __init__(self, pause_btn: Circle, super_btn: Circle):
        self.buttons = {"pause": pause_btn, "super": super_btn}
        self.fingers: dict[int, Finger] = {}
        self.super_armed = False

    def button_at(self, p: Point) -> str | None:
        for name, c in self.buttons.items():
            if c.contains(p):
                return name
        return None

    def reset(self) -> None:
        self.fingers.clear()
        self.super_armed = False

    # ------------------------------------------------------------ events
    def down(self, fid: int, p: Point, t: float) -> list[Action]:
        button = self.button_at(p)
        self.fingers[fid] = Finger(p, t, p, button=button)
        if button == "pause":
            return [("pause",)]
        if button == "super":
            self.super_armed = not self.super_armed
            return [("arm", self.super_armed)]
        return []

    def motion(self, fid: int, p: Point, t: float) -> list[Action]:
        f = self.fingers.get(fid)
        if f is None or f.button:
            return []
        f.pos = p
        dx, dy = p[0] - f.start[0], p[1] - f.start[1]
        if math.hypot(dx, dy) < config.TOUCH_SWIPE_MIN_DIST:
            return []
        if t - f.t0 > config.TOUCH_SWIPE_MAX_TIME:
            # too slow for a swipe: restart measuring from here
            f.start, f.t0, f.moved = p, t, True
            return []
        f.start, f.t0, f.moved = p, t, True        # chain: swipe again to hop on
        sup, self.super_armed = self.super_armed, False
        return [("move", swipe_direction(dx, dy), sup)]

    def up(self, fid: int, p: Point, t: float) -> list[Action]:
        out = self.motion(fid, p, t)
        f = self.fingers.pop(fid, None)
        if f is None or f.button or out:
            return out
        dist = math.hypot(p[0] - f.start[0], p[1] - f.start[1])
        if not f.moved and dist <= config.TOUCH_TAP_MAX_DIST and t - f.t0 <= config.TOUCH_TAP_MAX_TIME:
            return [("tongue",)]
        return []

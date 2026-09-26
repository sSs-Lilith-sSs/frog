"""Keyboard + mouse focus handling shared by every menu screen.

Arrow keys move focus spatially (to the nearest widget in that direction),
Enter/Space activate, the mouse hovers/clicks. A focused widget may consume
Left/Right itself (sliders, choices).
"""
from __future__ import annotations

from typing import Callable, Sequence

import pygame as pg

from .widgets import Widget

NAV_KEYS = {pg.K_UP: (0, -1), pg.K_DOWN: (0, 1), pg.K_LEFT: (-1, 0), pg.K_RIGHT: (1, 0),
            pg.K_w: (0, -1), pg.K_s: (0, 1), pg.K_a: (-1, 0), pg.K_d: (1, 0)}
ACTIVATE_KEYS = (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE)


class FocusGroup:
    def __init__(self, widgets: Sequence[Widget] = (), on_move: Callable[[], None] | None = None):
        self.widgets: list[Widget] = list(widgets)
        self.index = 0
        self.on_move = on_move
        self.mouse_mode = False
        self._pressed: Widget | None = None
        self._fix_index()

    # ------------------------------------------------------------ helpers
    def set_widgets(self, widgets: Sequence[Widget], keep: bool = True) -> None:
        cur = self.focused
        self.widgets = list(widgets)
        if keep and cur in self.widgets:
            self.index = self.widgets.index(cur)
        self._fix_index()

    def _focusable(self) -> list[int]:
        return [i for i, w in enumerate(self.widgets) if w.visible and w.focusable]

    def _fix_index(self) -> None:
        ok = self._focusable()
        if ok and self.index not in ok:
            self.index = ok[0]
        for i, w in enumerate(self.widgets):
            w.focused = i == self.index and bool(ok)

    @property
    def focused(self) -> Widget | None:
        if 0 <= self.index < len(self.widgets):
            return self.widgets[self.index]
        return None

    def focus(self, widget: Widget, sound: bool = False) -> None:
        if widget in self.widgets and widget.focusable:
            changed = self.widgets.index(widget) != self.index
            self.index = self.widgets.index(widget)
            self._fix_index()
            if changed and sound and self.on_move:
                self.on_move()

    # ------------------------------------------------------------ navigation
    def move(self, dx: int, dy: int) -> bool:
        cur = self.focused
        if cur is None:
            return False
        cx, cy = cur.rect.center
        best, best_score = None, None
        for i in self._focusable():
            w = self.widgets[i]
            if w is cur:
                continue
            wx, wy = w.rect.center
            ddx, ddy = wx - cx, wy - cy
            primary = ddx * dx + ddy * dy
            if primary <= 4:
                continue
            secondary = abs(ddx * dy) + abs(ddy * dx)
            score = primary + secondary * 2.2
            if best_score is None or score < best_score:
                best, best_score = i, score
        if best is None:
            # wrap around vertically in simple lists
            ok = self._focusable()
            if dy and ok:
                ordered = sorted(ok, key=lambda i: (self.widgets[i].rect.centery,
                                                    abs(self.widgets[i].rect.centerx - cx)))
                best = ordered[-1] if dy < 0 else ordered[0]
                if best == self.index:
                    return False
            else:
                return False
        self.index = best
        self._fix_index()
        if self.on_move:
            self.on_move()
        return True

    # ------------------------------------------------------------ events
    def handle(self, event: pg.event.Event) -> bool:
        cur = self.focused
        if event.type == pg.KEYDOWN:
            self.mouse_mode = False
            if cur is not None and cur.handle_key(event):
                return True
            if event.key in NAV_KEYS:
                dx, dy = NAV_KEYS[event.key]
                self.move(dx, dy)
                return True
            if event.key == pg.K_TAB:
                ok = self._focusable()
                if ok:
                    pos = ok.index(self.index) if self.index in ok else 0
                    step = -1 if event.mod & pg.KMOD_SHIFT else 1
                    self.index = ok[(pos + step) % len(ok)]
                    self._fix_index()
                    if self.on_move:
                        self.on_move()
                return True
            if event.key in ACTIVATE_KEYS and cur is not None:
                cur.activate()
                return True
            return False
        if event.type == pg.MOUSEMOTION:
            self.mouse_mode = True
            for w in self.widgets:
                w.hovered = w.visible and w.rect.collidepoint(event.pos)
                if w.hovered and w.focusable and w is not self.focused:
                    self.focus(w, sound=True)
            if self._pressed is not None:
                self._pressed.drag(event.pos)
            return False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for w in self.widgets:
                if w.visible and w.focusable and w.rect.collidepoint(event.pos):
                    self.focus(w)
                    self._pressed = w
                    w.press(event.pos)
                    return True
            return False
        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            w, self._pressed = self._pressed, None
            if w is not None:
                w.release(event.pos)
                return True
        if event.type == pg.MOUSEWHEEL and cur is not None:
            return cur.wheel(event.y)
        return False

    def update(self, dt: float) -> None:
        for w in self.widgets:
            if w.visible:
                w.update(dt)

    def draw(self, surf: pg.Surface) -> None:
        for w in self.widgets:
            if w.visible:
                w.draw(surf)

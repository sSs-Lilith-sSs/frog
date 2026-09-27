"""Menu widgets: rounded buttons, sliders, choices, toggles and text input.

Labels are callables (or plain strings) evaluated at draw time, so switching
the language updates every screen instantly.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

import pygame as pg

from .. import config, paths, web
from ..art.common import (draw_text, fit_size, lock_sprite, rounded_panel,
                          triangle_sprite)

Label = str | Callable[[], str]
_sound_hook: Callable[[str], None] | None = None


def set_sound_hook(fn: Callable[[str], None] | None) -> None:
    global _sound_hook
    _sound_hook = fn


def play(name: str) -> None:
    if _sound_hook:
        _sound_hook(name)


def _txt(label: Label) -> str:
    return label() if callable(label) else label


class Widget:
    focusable = True

    def __init__(self, rect: pg.Rect | tuple):
        self.rect = pg.Rect(rect)
        self.visible = True
        self.focused = False
        self.hovered = False
        self.t = 0.0
        self.shake = 0.0

    @property
    def hot(self) -> bool:
        return self.focused

    def handle_key(self, event: pg.event.Event) -> bool:
        return False

    def activate(self) -> None:
        pass

    def press(self, pos: tuple[int, int]) -> None:
        pass

    def release(self, pos: tuple[int, int]) -> None:
        if self.rect.collidepoint(pos):
            self.activate()

    def drag(self, pos: tuple[int, int]) -> None:
        pass

    def wheel(self, dy: int) -> bool:
        return False

    def update(self, dt: float) -> None:
        self.t += dt
        self.shake = max(0.0, self.shake - dt)

    def shake_offset(self) -> int:
        return int(math.sin(self.shake * 60) * 10 * self.shake / 0.4) if self.shake > 0 else 0

    def draw(self, surf: pg.Surface) -> None:
        pass


class Button(Widget):
    """Big rounded button from the mockup (yellow + ▶ when focused)."""

    def __init__(self, rect, label: Label, on_click: Callable[[], None] | None = None,
                 size: int = 40, locked: bool | Callable[[], bool] = False,
                 selected: Callable[[], bool] | None = None, arrow: bool = True,
                 radius: int | None = None, shadow: int = 7, border: int = 4,
                 icon: Callable[[pg.Surface, pg.Rect], None] | None = None,
                 sub: Label | None = None, fill: tuple | None = None):
        super().__init__(rect)
        self.label = label
        self.on_click = on_click
        self.size = size
        self._locked = locked
        self.selected = selected
        self.arrow = arrow
        self.radius = radius if radius is not None else self.rect.h // 2
        self.shadow = shadow
        self.border = border
        self.icon = icon
        self.sub = sub
        self.fill = fill
        self.pressed = False

    @property
    def locked(self) -> bool:
        return self._locked() if callable(self._locked) else bool(self._locked)

    def activate(self) -> None:
        if self.locked:
            self.shake = 0.4
            play("denied")
            return
        play("click")
        if self.on_click:
            self.on_click()

    def press(self, pos) -> None:
        self.pressed = True

    def release(self, pos) -> None:
        was = self.pressed
        self.pressed = False
        if was and self.rect.collidepoint(pos):
            self.activate()

    def colors(self) -> tuple[tuple, tuple]:
        if self.locked:
            return config.C_BUTTON_DISABLED, (95, 105, 95)
        sel = self.selected() if self.selected else False
        if self.hot or sel:
            return config.C_BUTTON_HOT, config.C_INK
        return self.fill or config.C_BUTTON, config.C_INK

    def draw(self, surf: pg.Surface) -> None:
        fill, ink = self.colors()
        r = self.rect.move(self.shake_offset(), 0)
        down = self.shadow if self.pressed else 0
        panel = rounded_panel(r.size, fill, config.C_BUTTON_SHADOW, self.radius, self.border,
                              config.C_BUTTON_SHADOW if self.shadow and not self.pressed else None,
                              self.shadow)
        surf.blit(panel, (r.x, r.y + down))
        r = r.move(0, down)
        text = _txt(self.label)
        pad_l = 70 if (self.arrow or self.locked or self.icon) and r.w > 260 else 24
        max_w = r.w - 2 * pad_l
        size = fit_size(text, self.size, max_w)
        cy = r.centery - (12 if self.sub else 0) - 2
        draw_text(surf, text, size, (r.centerx, cy), ink)
        if self.sub:
            sub = _txt(self.sub)
            draw_text(surf, sub, fit_size(sub, 24, max_w, bold=False), (r.centerx, cy + 34),
                      (90, 110, 90), bold=False)
        if self.icon:
            self.icon(surf, r)
        if self.locked and r.w > 200:
            lk = lock_sprite(34)
            surf.blit(lk, lk.get_rect(center=(r.x + 44, r.centery)))
        elif self.arrow and self.hot and r.w > 200:
            bob = math.sin(self.t * 6) * 3
            tri = triangle_sprite(34, 1, ink)
            surf.blit(tri, tri.get_rect(center=(r.x + 42 + bob, r.centery - 1)))


class Row(Widget):
    """Base for settings rows: label on the left, control on the right."""

    def __init__(self, rect, label: Label, control_w: int = 520):
        super().__init__(rect)
        self.label = label
        self.control = pg.Rect(self.rect.right - control_w - 24, self.rect.y, control_w, self.rect.h)

    def draw_row(self, surf: pg.Surface) -> None:
        if self.hot:
            surf.blit(rounded_panel(self.rect.size, (255, 236, 170), (225, 190, 90), 22, 3),
                      self.rect.topleft)
            tri = triangle_sprite(26, 1, config.C_INK)
            surf.blit(tri, tri.get_rect(center=(self.rect.x + 28, self.rect.centery)))
        text = _txt(self.label)
        max_w = self.control.x - self.rect.x - 80
        draw_text(surf, text, fit_size(text, 34, max_w), (self.rect.x + 52, self.rect.centery - 2),
                  config.C_INK, anchor="midleft")


class Slider(Row):
    def __init__(self, rect, label: Label, get: Callable[[], float],
                 set_: Callable[[float], None], step: float = 0.05):
        super().__init__(rect, label)
        self.get, self.set, self.step = get, set_, step
        self.dragging = False

    @property
    def track(self) -> pg.Rect:
        return pg.Rect(self.control.x, self.control.centery - 9, self.control.w - 110, 18)

    def handle_key(self, event) -> bool:
        if event.key in (pg.K_LEFT, pg.K_a, pg.K_RIGHT, pg.K_d):
            d = -self.step if event.key in (pg.K_LEFT, pg.K_a) else self.step
            self.set(round(max(0.0, min(1.0, self.get() + d)), 3))
            return True
        return False

    def _set_from_x(self, x: int) -> None:
        tr = self.track
        self.set(round(max(0.0, min(1.0, (x - tr.x) / tr.w)), 3))

    def press(self, pos) -> None:
        if self.control.inflate(0, 20).collidepoint(pos):
            self.dragging = True
            self._set_from_x(pos[0])

    def drag(self, pos) -> None:
        if self.dragging:
            self._set_from_x(pos[0])

    def release(self, pos) -> None:
        self.dragging = False

    def wheel(self, dy: int) -> bool:
        self.set(round(max(0.0, min(1.0, self.get() + dy * self.step)), 3))
        return True

    def draw(self, surf: pg.Surface) -> None:
        self.draw_row(surf)
        tr = self.track
        v = self.get()
        surf.blit(rounded_panel(tr.size, (215, 222, 205), (150, 170, 140), 9, 2), tr.topleft)
        fw = max(18, int(tr.w * v))
        surf.blit(rounded_panel((fw, tr.h), (120, 200, 90), (60, 130, 60), 9, 2), tr.topleft)
        kx = tr.x + int(tr.w * v)
        knob = rounded_panel((38, 38), (255, 255, 255), config.C_INK, 19, 4)
        surf.blit(knob, knob.get_rect(center=(kx, tr.centery)))
        draw_text(surf, f"{round(v * 100)}%", 30, (self.control.right - 4, self.control.centery - 2),
                  config.C_INK, anchor="midright")


class Choice(Row):
    def __init__(self, rect, label: Label, options: Sequence[tuple[object, Label]],
                 get: Callable[[], object], set_: Callable[[object], None], control_w: int = 620):
        super().__init__(rect, label, control_w)
        self.options = list(options)
        self.get, self.set = get, set_

    def _pill_rects(self) -> list[pg.Rect]:
        n = len(self.options)
        gap = 12
        w = (self.control.w - gap * (n - 1)) // n
        return [pg.Rect(self.control.x + i * (w + gap), self.control.centery - 30, w, 60)
                for i in range(n)]

    def _index(self) -> int:
        vals = [o[0] for o in self.options]
        cur = self.get()
        return vals.index(cur) if cur in vals else 0

    def handle_key(self, event) -> bool:
        if event.key in (pg.K_LEFT, pg.K_a, pg.K_RIGHT, pg.K_d):
            d = -1 if event.key in (pg.K_LEFT, pg.K_a) else 1
            i = (self._index() + d) % len(self.options)
            self.set(self.options[i][0])
            play("click")
            return True
        return False

    def activate(self) -> None:
        self.set(self.options[(self._index() + 1) % len(self.options)][0])
        play("click")

    def release(self, pos) -> None:
        for (value, _), r in zip(self.options, self._pill_rects()):
            if r.collidepoint(pos):
                if value != self.get():
                    self.set(value)
                    play("click")
                return

    def draw(self, surf: pg.Surface) -> None:
        self.draw_row(surf)
        cur = self._index()
        for i, ((_, lab), r) in enumerate(zip(self.options, self._pill_rects())):
            sel = i == cur
            fill = config.C_BUTTON_HOT if sel else (255, 255, 255)
            surf.blit(rounded_panel(r.size, fill, config.C_INK_SOFT, 20, 3), r.topleft)
            text = _txt(lab)
            draw_text(surf, text, fit_size(text, 26, r.w - 16), (r.centerx, r.centery - 1),
                      config.C_INK)


class Toggle(Row):
    def __init__(self, rect, label: Label, get: Callable[[], bool], set_: Callable[[bool], None],
                 on_text: Label = "", off_text: Label = ""):
        super().__init__(rect, label, control_w=260)
        self.get, self.set = get, set_
        self.on_text, self.off_text = on_text, off_text
        self.anim = 1.0 if get() else 0.0

    def activate(self) -> None:
        self.set(not self.get())
        play("click")

    def handle_key(self, event) -> bool:
        if event.key in (pg.K_LEFT, pg.K_a, pg.K_RIGHT, pg.K_d):
            want = event.key in (pg.K_RIGHT, pg.K_d)
            if want != self.get():
                self.set(want)
                play("click")
            return True
        return False

    def update(self, dt: float) -> None:
        super().update(dt)
        target = 1.0 if self.get() else 0.0
        self.anim += (target - self.anim) * min(1.0, dt * 14)

    def draw(self, surf: pg.Surface) -> None:
        self.draw_row(surf)
        on = self.get()
        track = pg.Rect(self.control.right - 110, self.control.centery - 24, 100, 48)
        col = (120, 200, 90) if on else (200, 205, 195)
        surf.blit(rounded_panel(track.size, col, config.C_INK_SOFT, 24, 3), track.topleft)
        kx = track.x + 24 + int(self.anim * 52)
        knob = rounded_panel((38, 38), (255, 255, 255), config.C_INK_SOFT, 19, 3)
        surf.blit(knob, knob.get_rect(center=(kx, track.centery)))
        text = _txt(self.on_text if on else self.off_text)
        if text:
            draw_text(surf, text, 28, (track.x - 18, track.centery - 2), config.C_INK,
                      bold=False, anchor="midright")


class TextInput(Widget):
    def __init__(self, rect, placeholder: Label = "", max_len: int = 16,
                 on_submit: Callable[[str], None] | None = None, prompt: Label = ""):
        super().__init__(rect)
        self.text = ""
        self.placeholder = placeholder
        self.prompt = prompt            # question of the browser's text dialog
        self.max_len = max_len
        self.on_submit = on_submit

    def handle_text(self, text: str) -> None:
        for ch in text:
            if len(self.text) >= self.max_len:
                play("denied")
                self.shake = 0.3
                break
            if ch.isprintable():
                self.text += ch

    def handle_key(self, event) -> bool:
        if event.key in (pg.K_UP, pg.K_DOWN, pg.K_TAB, pg.K_ESCAPE):
            return False
        if event.key == pg.K_BACKSPACE:
            if event.mod & pg.KMOD_CTRL:
                self.text = ""
            else:
                self.text = self.text[:-1]
        elif event.key in (pg.K_RETURN, pg.K_KP_ENTER):
            if self.on_submit:
                self.on_submit(self.text)
        return True          # swallow letters so WASD does not navigate

    def activate(self) -> None:
        if self.on_submit:
            self.on_submit(self.text)

    def press(self, pos) -> None:
        # a tap on the field asks for the on-screen keyboard (phones, browser)
        if paths.is_web():
            self.ask_web()
            return
        try:
            pg.key.start_text_input()
        except pg.error:
            pass

    def ask_web(self) -> None:
        """Browser: SDL shows no phone keyboard, so ask with the page's prompt();
        a non-empty answer is submitted right away."""
        answer = web.ask_text(_txt(self.prompt or self.placeholder), self.text)
        if answer is None:
            return
        self.text = ""
        self.handle_text(answer.strip())
        if self.text and self.on_submit:
            self.on_submit(self.text)

    def release(self, pos) -> None:
        pass

    def draw(self, surf: pg.Surface) -> None:
        r = self.rect.move(self.shake_offset(), 0)
        border = (225, 170, 40) if self.hot else config.C_INK_SOFT
        surf.blit(rounded_panel(r.size, (255, 255, 255), border, 26, 4), r.topleft)
        x = r.x + 30
        if self.text:
            size = fit_size(self.text, 42, r.right - 40 - x)       # 16 wide letters fit too
            tr = draw_text(surf, self.text, size, (x, r.centery - 2), config.C_INK, anchor="midleft")
            caret_x = tr.right + 4
        else:
            draw_text(surf, _txt(self.placeholder), 40, (x, r.centery - 2), (170, 180, 170),
                      bold=False, anchor="midleft")
            caret_x = x
        if self.hot and int(self.t * 2.2) % 2 == 0:
            pg.draw.rect(surf, config.C_INK, (caret_x, r.centery - 24, 4, 46), border_radius=2)

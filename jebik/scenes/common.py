"""Shared menu pieces: animated pond backdrop, titles, panels, MenuScene."""
from __future__ import annotations

import math
import random

import pygame as pg

from .. import config, i18n
from ..art import backdrops
from ..art.chars import fly_sprite, frog_front_sprite
from ..art.common import draw_text, fit_size, rounded_panel, text_surface
from ..ui.focus import FocusGroup
from ..ui.widgets import Button
from .base import Scene

W, H = config.SCREEN_W, config.SCREEN_H


class MenuBackdrop:
    """The pond from the menu mockup with drifting clouds, buzzing flies and a
    blinking big frog. One instance is shared by all menu screens, so the
    animation continues smoothly across transitions."""

    def __init__(self):
        self.bg = backdrops.menu_background()
        self.clouds = [[float(x), float(y), 0.6 + 0.12 * i, i % 2]
                       for i, (x, y) in enumerate(backdrops.menu_cloud_positions())]
        self.flies = [((1330, 640), "fly", 0.0), ((1690, 610), "fly", 2.1), ((1230, 720), "gold", 4.2)]
        self.t = 0.0
        self.blink = 0.0
        self.next_blink = 2.5
        self.veil = pg.Surface((W, H), pg.SRCALPHA)
        self.veil.fill((255, 255, 255, 70))

    def update(self, dt: float) -> None:
        self.t += dt
        for c in self.clouds:
            c[0] += c[2] * 9 * dt
            if c[0] > W + 60:
                c[0] = -260
        self.next_blink -= dt
        if self.next_blink <= 0:
            self.blink = 0.14
            self.next_blink = random.uniform(2.5, 5.0)
        self.blink = max(0.0, self.blink - dt)

    def draw(self, surf: pg.Surface, veil: bool = False, frog: bool = True) -> None:
        surf.blit(self.bg, (0, 0))
        ax, ay = backdrops.CLOUD_ANCHOR
        for x, y, _, var in self.clouds:
            spr = backdrops.cloud_sprite(var)
            surf.blit(spr, (round(x) - ax, round(y) - ay))
        if frog:
            breathe = 1 + 0.018 * math.sin(self.t * 2.2)
            spr = frog_front_sprite(4.2, self.blink > 0)
            w, h = spr.get_size()
            big = pg.transform.smoothscale(spr, (int(w * (2 - breathe)), int(h * breathe)))
            surf.blit(big, big.get_rect(midbottom=(1500, 830 + h * 0.44)))
        for (fx, fy), kind, ph in self.flies:
            t = self.t + ph
            x = fx + math.sin(t * 1.3) * 34 + math.sin(t * 3.1) * 8
            y = fy + math.sin(t * 1.9) * 18 + math.cos(t * 4.3) * 5
            spr = fly_sprite(1.0, kind, int(t * 22) % 2 == 1)
            surf.blit(spr, spr.get_rect(center=(round(x), round(y))))
        if veil:
            surf.blit(self.veil, (0, 0))


def draw_logo(surf: pg.Surface, center: tuple[int, int], size: int = 190, t: float = 0.0,
              subtitle: bool = True) -> None:
    bob = math.sin(t * 1.6) * 4
    img = text_surface(i18n.TITLE, size, config.C_TITLE, True, config.C_TITLE_OUTLINE,
                       max(3, size // 32))
    surf.blit(img, img.get_rect(center=(center[0], center[1] + bob)))
    if subtitle:
        sub_size = int(size * 0.24)
        draw_text(surf, i18n.SUBTITLE, sub_size, (center[0], center[1] + size * 0.66),
                  (255, 255, 255), outline=config.C_SUBTITLE_OUTLINE, outline_w=max(2, sub_size // 12))


def draw_screen_title(surf: pg.Surface, text: str, y: int = 96, size: int = 84) -> None:
    size = fit_size(text, size, 1400)
    draw_text(surf, text, size, (W // 2, y), config.C_TITLE, outline=config.C_TITLE_OUTLINE,
              outline_w=max(3, size // 22))


def draw_panel(surf: pg.Surface, rect: pg.Rect, fill=config.C_PANEL) -> None:
    surf.blit(rounded_panel(rect.size, fill, config.C_INK_SOFT, 36, 4, config.C_BUTTON_SHADOW, 8),
              rect.topleft)


def draw_hint(surf: pg.Surface, text: str | None = None, y: int = H - 34) -> None:
    text = text or i18n.t("common.hint_nav")
    draw_text(surf, text, 24, (W // 2, y), (255, 255, 255), bold=False,
              outline=(40, 90, 60), outline_w=2)


class MenuScene(Scene):
    """Base for menu screens: shared backdrop, focus group, Esc = back."""

    veil = True
    show_frog = True
    title_key: str | None = None

    def __init__(self, app, over_game: bool = False):
        super().__init__(app)
        self.over_game = over_game          # opened from the pause menu
        self.opaque = not over_game
        self.focus = FocusGroup(on_move=lambda: app.audio.play("tick"))
        self._dim = pg.Surface((W, H), pg.SRCALPHA)
        self._dim.fill((12, 30, 34, 175))

    def back_button(self, x: int = 70, y: int = H - 150, w: int = 300) -> Button:
        return Button((x, y, w, 76), lambda: i18n.t("common.back"), self.back, size=36)

    def back(self) -> None:
        self.app.scenes.pop()

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.app.audio.play("click")
            self.back()
            return
        self.focus.handle(event)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.app.backdrop.update(dt)
        self.focus.update(dt)

    def draw(self, surf: pg.Surface) -> None:
        if self.over_game:
            surf.blit(self._dim, (0, 0))
        else:
            self.app.backdrop.draw(surf, veil=self.veil, frog=self.show_frog)
        if self.title_key:
            draw_screen_title(surf, i18n.t(self.title_key))
        self.draw_content(surf)
        self.focus.draw(surf)
        self.draw_over(surf)

    def draw_content(self, surf: pg.Surface) -> None:
        pass

    def draw_over(self, surf: pg.Surface) -> None:
        pass

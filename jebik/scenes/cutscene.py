"""Story cards: a drawn illustration + typewriter text (UA / EN / RU).

Enter / Space / click / tap: finish the text, then next card. Esc skips the
whole cutscene. ``on_done`` runs once at the end (e.g. starts the level).
The ``"credits"`` card is a slow roll of the credits instead.
"""
from __future__ import annotations

import math
from typing import Callable

import pygame as pg

from .. import config, i18n
from ..art.common import draw_text, heart_sprite, rounded_panel, wrap
from ..story import Card
from .base import Scene
from .common import H, W
from .story_art import draw_card_art

TYPE_SPEED = 45           # characters per second
ART = pg.Rect(W // 2 - 620, 90, 1240, 610)
TEXT = pg.Rect(W // 2 - 620, 730, 1240, 250)
CREDITS_SPEED = 70        # px per second


class CutsceneScene(Scene):
    def __init__(self, app, cards: list[Card], on_done: Callable[[], None]):
        super().__init__(app)
        self.cards = cards or [Card("", "credits")]
        self.index = 0
        self.card_t = 0.0
        self.on_done = on_done
        self.done = False
        self.bg = pg.Surface((W, H))
        for y in range(H):
            pg.draw.line(self.bg, (int(18 + 20 * y / H), int(20 + 12 * y / H), int(40 + 20 * y / H)), (0, y), (W, y))

    @property
    def card(self) -> Card:
        return self.cards[self.index]

    def _text(self) -> str:
        return i18n.t(self.card.text_key) if self.card.text_key else ""

    @property
    def typing(self) -> bool:
        return self.card.art != "credits" and self.card_t * TYPE_SPEED < len(self._text())

    # ------------------------------------------------------------ flow
    def advance(self) -> None:
        if self.done:
            return
        if self.typing:
            self.card_t = len(self._text()) / TYPE_SPEED + 0.01
            return
        self.app.audio.play("click")
        if self.index + 1 < len(self.cards):
            self.index += 1
            self.card_t = 0.0
        else:
            self.finish()

    def finish(self) -> None:
        if not self.done:
            self.done = True
            self.on_done()

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.app.audio.play("click")
                self.finish()
            elif event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE, pg.K_RIGHT, pg.K_d):
                self.advance()
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.advance()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.card_t += dt

    # ------------------------------------------------------------ draw
    def draw(self, surf: pg.Surface) -> None:
        surf.blit(self.bg, (0, 0))
        if self.card.art == "credits":
            self._draw_credits(surf)
        else:
            self._draw_card(surf)
        for i in range(len(self.cards)):                    # page dots
            col = (255, 225, 110) if i == self.index else (110, 110, 130)
            pg.draw.circle(surf, col, (W // 2 - (len(self.cards) - 1) * 14 + i * 28, H - 70), 7)
        draw_text(surf, i18n.t("story.continue"), 22, (W // 2, H - 34), (190, 190, 210), bold=False)

    def _draw_card(self, surf: pg.Surface) -> None:
        frame = ART.inflate(16, 16)
        surf.blit(rounded_panel(frame.size, (250, 244, 225), (120, 90, 60), 30, 5), frame.topleft)
        draw_card_art(self.card, surf, ART, self.time)
        surf.blit(rounded_panel(TEXT.size, config.C_PANEL, config.C_INK_SOFT, 30, 4), TEXT.topleft)
        text = self._text()
        shown = text[:int(self.card_t * TYPE_SPEED)]
        lines = wrap(text, 40, TEXT.w - 100)
        y = TEXT.y + 60 if len(lines) < 3 else TEXT.y + 44
        left = len(shown)
        for line in lines:
            part = line[:max(0, left)]
            left -= len(line) + 1
            if part:
                draw_text(surf, part, 40, (TEXT.x + 50, y), config.C_INK, bold=False, anchor="midleft")
            y += 56
        if not self.typing and int(self.time * 2.5) % 2 == 0:
            pts = [(TEXT.right - 60, TEXT.bottom - 50), (TEXT.right - 36, TEXT.bottom - 50),
                   (TEXT.right - 48, TEXT.bottom - 34)]
            pg.draw.polygon(surf, config.C_INK, pts)

    def credit_lines(self) -> list[tuple[str, int, tuple]]:
        gold, white, soft = (255, 225, 110), (255, 255, 255), (200, 200, 225)
        return [(i18n.t("credits.title"), 96, gold), ("", 40, white), (i18n.TITLE, 72, (150, 230, 110)),
                ("", 40, white), (i18n.t("credits.made"), 36, soft), (i18n.t("credits.font"), 30, soft),
                ("", 60, white), (i18n.t("credits.thanks"), 52, gold), ("", 50, white),
                (i18n.SUBTITLE, 48, (255, 170, 205))]          # the dedication comes last

    def _draw_credits(self, surf: pg.Surface) -> None:
        lines = self.credit_lines()
        total = sum(size * 1.5 for _, size, _ in lines)
        y = H - 120 - self.card_t * CREDITS_SPEED
        y = max(y, H / 2 - total / 2)                      # stops in the middle
        for text, size, col in lines:
            if text:       # the font's wide "・" looks gappy: draw it as "·" (as in the menu)
                draw_text(surf, text.replace("・", "·"), size, (W // 2, y), col, outline=(40, 30, 60),
                          outline_w=3)
            y += size * 1.5
        for i in range(8):                                  # hearts drifting up the sides
            hy = H - ((self.time * 60 + i * 140) % (H + 80))
            hx = (160 if i % 2 else W - 160) + math.sin(self.time + i) * 40
            img = heart_sprite(34 + (i % 3) * 10, (240, 90, 130))
            surf.blit(img, img.get_rect(center=(round(hx), round(hy))))

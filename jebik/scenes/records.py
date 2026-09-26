"""Records — placeholder for Build 1 ("soon")."""
from __future__ import annotations

import math

import pygame as pg

from .. import config, i18n
from ..art.common import draw_text, render_ss, star_sprite
from .common import H, W, MenuScene, draw_hint, draw_panel


def trophy_sprite(size: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        u = size * ss / 20
        gold, dark = (250, 200, 60), (190, 135, 30)
        for sx in (-1, 1):   # handles
            pg.draw.circle(s, dark, (10 * u + sx * 6.5 * u, 6.5 * u), 3.2 * u, max(1, int(1.3 * u)))
        pg.draw.polygon(s, gold, [(4 * u, 2 * u), (16 * u, 2 * u), (14.5 * u, 9 * u), (10 * u, 12 * u),
                                  (5.5 * u, 9 * u)])
        pg.draw.ellipse(s, (255, 235, 150), (5.5 * u, 2.6 * u, 3 * u, 5 * u))
        pg.draw.rect(s, dark, (8.8 * u, 11.5 * u, 2.4 * u, 3.5 * u))
        pg.draw.rect(s, gold, (6 * u, 14.5 * u, 8 * u, 2.2 * u), border_radius=int(.8 * u))
        pg.draw.rect(s, (120, 80, 40), (5 * u, 16.5 * u, 10 * u, 2.6 * u), border_radius=int(.8 * u))
    return render_ss((size, size), draw)


class RecordsScene(MenuScene):
    title_key = "records.title"

    def __init__(self, app):
        super().__init__(app)
        self.panel = pg.Rect(W // 2 - 520, 220, 1040, 520)
        self.focus.set_widgets([self.back_button(W // 2 - 170, self.panel.bottom + 50, 340)])
        self.trophy = trophy_sprite(220)

    def draw_content(self, surf: pg.Surface) -> None:
        draw_panel(surf, self.panel)
        cx = self.panel.centerx
        bob = math.sin(self.time * 2) * 6
        surf.blit(self.trophy, self.trophy.get_rect(center=(cx, self.panel.y + 190 + bob)))
        for i in range(3):
            st = star_sprite(46)
            a = self.time * 1.4 + i * 2.09
            surf.blit(st, st.get_rect(center=(cx + math.cos(a) * 170, self.panel.y + 190 + math.sin(a) * 60)))
        draw_text(surf, i18n.t("common.soon"), 64, (cx, self.panel.y + 370), config.C_INK)
        draw_text(surf, i18n.t("records.soon"), 32, (cx, self.panel.y + 440), (90, 110, 90), bold=False)

    def draw_over(self, surf: pg.Surface) -> None:
        draw_hint(surf, y=H - 34)

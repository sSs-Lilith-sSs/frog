"""Records: top-10 per level and in total, per difficulty, across local profiles."""
from __future__ import annotations

import math
from typing import Callable

import pygame as pg

from .. import config, i18n, records
from ..art.common import draw_text, fit_size, render_ss, rounded_panel, star_sprite, triangle_sprite
from ..game.rules import DIFFICULTIES, DIFFICULTY_NAMES, EZZZ
from ..ui.widgets import Button, Widget, play
from ..worlds import catalog
from .common import H, W, MenuScene, draw_hint, draw_panel
from .overlays import fmt_time

PANEL = pg.Rect(W // 2 - 620, 300, 1240, 610)
ROW_H = 52
COLS = (90, 180, 700, 900, 1080)        # rank, name, score, time, stars (x inside panel)


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


class Selector(Widget):
    """«◀ Рівень 1-1 ▶» — left/right (keys or arrow clicks) cycles the options."""

    def __init__(self, rect, count: int, label: Callable[[int], str], on_change: Callable[[], None]):
        super().__init__(rect)
        self.count, self.label, self.on_change = count, label, on_change
        self.index = 0

    def step(self, d: int) -> None:
        self.index = (self.index + d) % self.count
        play("click")
        self.on_change()

    def handle_key(self, event) -> bool:
        if event.key in (pg.K_LEFT, pg.K_a, pg.K_RIGHT, pg.K_d):
            self.step(-1 if event.key in (pg.K_LEFT, pg.K_a) else 1)
            return True
        return False

    def activate(self) -> None:
        self.step(1)

    def release(self, pos) -> None:
        if self.rect.collidepoint(pos):
            self.step(-1 if pos[0] < self.rect.centerx else 1)

    def draw(self, surf: pg.Surface) -> None:
        r = self.rect
        fill = config.C_BUTTON_HOT if self.hot else config.C_BUTTON
        surf.blit(rounded_panel(r.size, fill, config.C_INK, r.h // 2, 4, config.C_BUTTON_SHADOW, 7), r.topleft)
        text = self.label(self.index)
        draw_text(surf, text, fit_size(text, 40, r.w - 160), (r.centerx, r.centery - 2), config.C_INK)
        bob = math.sin(self.t * 6) * 3 if self.hot else 0
        for d, x in ((3, r.x + 40 - bob), (1, r.right - 40 + bob)):
            tri = triangle_sprite(30, d, config.C_INK)
            surf.blit(tri, tri.get_rect(center=(x, r.centery)))


class RecordsScene(MenuScene):
    title_key = "records.title"
    show_frog = False

    def __init__(self, app):
        super().__init__(app)
        self.difficulty = app.difficulty if app.difficulty in DIFFICULTIES else EZZZ
        self.levels: list[str | None] = [None] + catalog.playable_levels()    # None = total
        self.selector = Selector((W // 2 - 300, 190, 600, 76), len(self.levels), self._label, self._refresh)
        pills = [Button((x, 196, 250, 64), DIFFICULTY_NAMES[d], lambda d=d: self._set_diff(d),
                        size=28, arrow=False, radius=32, shadow=0, border=3,
                        selected=lambda d=d: self.difficulty == d)          # left / right of the selector
                 for d, x in zip(DIFFICULTIES, (W // 2 - 580, W // 2 + 330))]
        self.focus.set_widgets([self.selector] + pills + [self.back_button(70, H - 130, 300)], keep=False)
        self.trophy = trophy_sprite(120)
        self.rows: list[records.RecordRow] = []
        self._refresh()

    def _label(self, i: int) -> str:
        lid = self.levels[i]
        return i18n.t("records.total") if lid is None else i18n.t("records.level", id=lid)

    def _set_diff(self, d: str) -> None:
        self.difficulty = d
        self._refresh()

    def _refresh(self) -> None:
        lid = self.levels[self.selector.index]
        data = self.app.save
        self.rows = records.total_top(data, self.difficulty) if lid is None \
            else records.level_top(data, self.difficulty, lid)

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN and event.key == pg.K_TAB:
            i = DIFFICULTIES.index(self.difficulty)
            self._set_diff(DIFFICULTIES[(i + 1) % len(DIFFICULTIES)])
            play("click")
            return
        super().handle(event)

    def draw_content(self, surf: pg.Surface) -> None:
        draw_panel(surf, PANEL)
        total = self.levels[self.selector.index] is None
        hy = PANEL.y + 40
        heads = (("#", 0), (i18n.t("records.name"), 1), (i18n.t("records.score"), 2),
                 (i18n.t("records.time"), 3), (i18n.t("records.stars"), 4))
        for text, c in heads:
            draw_text(surf, text, 26, (PANEL.x + COLS[c], hy), (110, 130, 110), anchor="midleft" if c == 1 else "center")
        pg.draw.line(surf, (200, 205, 190), (PANEL.x + 40, hy + 24), (PANEL.right - 40, hy + 24), 2)
        if not self.rows:
            bob = math.sin(self.time * 2) * 6
            surf.blit(self.trophy, self.trophy.get_rect(center=(PANEL.centerx, PANEL.centery - 20 + bob)))
            draw_text(surf, i18n.t("records.empty"), 34, (PANEL.centerx, PANEL.centery + 90), (90, 110, 90), bold=False)
            return
        me = self.app.profile.name if self.app.profile else None
        for i, row in enumerate(self.rows):
            y = hy + 60 + i * ROW_H
            if row.name == me:
                hl = pg.Rect(PANEL.x + 30, y - ROW_H // 2 + 3, PANEL.w - 60, ROW_H - 6)
                surf.blit(rounded_panel(hl.size, (255, 240, 190), None, 16), hl.topleft)
            medal = ((250, 200, 60), (190, 195, 205), (215, 150, 90))
            if i < 3:
                pg.draw.circle(surf, medal[i], (PANEL.x + COLS[0], y), 20)
            draw_text(surf, str(i + 1), 28, (PANEL.x + COLS[0], y), config.C_INK)
            draw_text(surf, row.name, fit_size(row.name, 30, 460), (PANEL.x + COLS[1], y), config.C_INK, anchor="midleft")
            draw_text(surf, str(row.score), 30, (PANEL.x + COLS[2], y), config.C_INK)
            draw_text(surf, fmt_time(row.time), 28, (PANEL.x + COLS[3], y), (80, 105, 85), bold=False)
            if total:
                st = star_sprite(28)
                surf.blit(st, st.get_rect(center=(PANEL.x + COLS[4] - 70, y)))
                draw_text(surf, f"{row.stars} · {i18n.t('records.levels', n=row.levels)}", 24,
                          (PANEL.x + COLS[4] - 50, y), (150, 110, 30), bold=False, anchor="midleft")
            else:
                for s in range(3):
                    st = star_sprite(28, s < row.stars)
                    surf.blit(st, st.get_rect(center=(PANEL.x + COLS[4] - 32 + s * 32, y)))

    def draw_over(self, surf: pg.Surface) -> None:
        draw_hint(surf, i18n.t("records.hint"), y=H - 34)

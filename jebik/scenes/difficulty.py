"""Difficulty select: EZZZ (open) and TOBI PIZDA (locked until EZZZ is done)."""
from __future__ import annotations

import math

import pygame as pg

from .. import config, i18n, progression
from ..art.common import (draw_text, heart_sprite, lock_sprite, render_ss,
                          rounded_panel, triangle_sprite)
from ..game.rules import DIFFICULTY_NAMES, EZZZ, TOBI
from ..ui.widgets import Button
from .common import W, MenuScene, draw_hint
from .flow import next_level_to_play, start_level

CARD_W, CARD_H = 600, 440


def clock_sprite(size: int, col=(60, 70, 80)) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        c = size * ss / 2
        pg.draw.circle(s, col, (c, c), c * .92)
        pg.draw.circle(s, (250, 250, 245), (c, c), c * .74)
        pg.draw.line(s, col, (c, c), (c, c * .45), max(1, int(c * .12)))
        pg.draw.line(s, col, (c, c), (c * 1.4, c * 1.15), max(1, int(c * .12)))
        pg.draw.circle(s, col, (c, c), c * .1)
    return render_ss((size, size), draw)


class DifficultyCard(Button):
    def __init__(self, rect, diff: str, on_click, locked):
        super().__init__(rect, DIFFICULTY_NAMES[diff], on_click, size=58, locked=locked,
                         radius=36, shadow=9)
        self.diff = diff
        self._clock = clock_sprite(64)

    def draw(self, surf: pg.Surface) -> None:
        fill, ink = self.colors()
        if not self.locked and not self.hot:
            fill = (250, 250, 240)
        r = self.rect.move(self.shake_offset(), 0)
        down = self.shadow if self.pressed else 0
        surf.blit(rounded_panel(r.size, fill, config.C_BUTTON_SHADOW, 36, 5,
                                None if self.pressed else config.C_BUTTON_SHADOW, 9), (r.x, r.y + down))
        r = r.move(0, down)
        draw_text(surf, DIFFICULTY_NAMES[self.diff], 60, (r.centerx, r.y + 70), ink)
        icon_y = r.y + 170
        if self.diff == EZZZ:
            for i in range(3):
                bob = math.sin(self.t * 3 + i * .8) * 4 if self.hot else 0
                hs = heart_sprite(62, config.C_HEART)
                surf.blit(hs, hs.get_rect(center=(r.centerx - 80 + i * 80, icon_y + bob)))
        else:
            ck = self._clock
            surf.blit(ck, ck.get_rect(center=(r.centerx, icon_y)))
        key = "diff.ezzz_desc" if self.diff == EZZZ else "diff.tobi_desc"
        for i, line in enumerate(i18n.t(key).split("\n")):
            draw_text(surf, line, 30, (r.centerx, r.y + 262 + i * 44), ink, bold=False)
        if self.locked:
            lk = lock_sprite(64)
            surf.blit(lk, lk.get_rect(center=(r.centerx - 110, r.bottom - 58)))
            draw_text(surf, i18n.t("diff.locked"), 34, (r.centerx + 20, r.bottom - 58),
                      (95, 105, 95))
        elif self.hot:
            bob = math.sin(self.t * 6) * 3
            tri = triangle_sprite(40, 1, ink)
            surf.blit(tri, tri.get_rect(center=(r.centerx + bob, r.bottom - 52)))


class DifficultyScene(MenuScene):
    title_key = "diff.title"

    def __init__(self, app, then: str = "play"):
        super().__init__(app)
        self.then = then
        y = 250
        ez = DifficultyCard((W // 2 - CARD_W - 30, y, CARD_W, CARD_H), EZZZ,
                            lambda: self._pick(EZZZ), False)
        # TOBI PIZDA opens after every playable EZZZ level is completed
        tobi = DifficultyCard((W // 2 + 30, y, CARD_W, CARD_H), TOBI,
                              lambda: self._pick(TOBI), self._tobi_locked)
        self.focus.set_widgets([ez, tobi, self.back_button()], keep=False)

    def _tobi_locked(self) -> bool:
        p = self.app.profile
        return not (p and progression.tobi_unlocked(p))

    def _pick(self, diff: str) -> None:
        self.app.difficulty = diff
        if self.then == "levels":
            from .level_select import LevelSelectScene
            self.app.scenes.replace(LevelSelectScene(self.app))
            return
        lid = next_level_to_play(self.app)
        if lid is None:
            from .level_select import LevelSelectScene
            self.app.scenes.replace(LevelSelectScene(self.app))
        else:
            start_level(self.app, lid, replace=True)

    def draw_over(self, surf: pg.Surface) -> None:
        draw_hint(surf)

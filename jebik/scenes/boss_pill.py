"""HUD boss pill: portrait, name and health hearts, under the top bar.

The portrait comes from ``WorldArt.boss_icon(kind, size)`` (a generic crown
if the world has none). The pill shakes and flashes on a hit, glows while
the boss is vulnerable and greys out when it is defeated.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from .. import i18n
from ..art.common import draw_text, fit_size, heart_sprite, render_ss, rounded_panel
from ..art.world_art import art_for
from ..game.enemy import Boss
from ..worlds import world_by_id

PILL_W, PILL_H = 460, 52
ICON = 44


@lru_cache(maxsize=4)
def crown_icon(size: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        u = size * ss / 20
        pts = [(2 * u, 16 * u), (2 * u, 6 * u), (6.5 * u, 10 * u), (10 * u, 3 * u), (13.5 * u, 10 * u),
               (18 * u, 6 * u), (18 * u, 16 * u)]
        pg.draw.polygon(s, (250, 200, 60), pts)
        pg.draw.polygon(s, (170, 110, 30), pts, max(1, int(1.2 * u)))
        for x in (2, 10, 18):
            pg.draw.circle(s, (240, 90, 110), (x * u, (6 if x != 10 else 3) * u), 1.6 * u)
    return render_ss((size, size), draw)


class BossPill:
    def __init__(self, boss: Boss, world_id: str):
        self.boss = boss
        self.theme = world_by_id(world_id).theme
        self.icon = art_for(world_id).boss_icon(boss.kind, ICON) or crown_icon(ICON)
        self.t = 0.0
        self.shake = 0.0
        self._hp = boss.hp

    def update(self, dt: float) -> None:
        self.t += dt
        self.shake = max(0.0, self.shake - dt)
        if self.boss.hp != self._hp:
            self.shake = 0.5
            self._hp = self.boss.hp

    def draw(self, surf: pg.Surface, center: tuple[int, int]) -> None:
        b = self.boss
        jx = math.sin(self.shake * 50) * 8 * self.shake / 0.5 if self.shake else 0
        r = pg.Rect(0, 0, PILL_W, PILL_H)
        r.center = (round(center[0] + jx), center[1])
        border = self.theme.hud_line
        if b.vulnerable:                 # glowing border: hit it now!
            v = 0.5 + 0.5 * math.sin(self.t * 10)
            border = tuple(int(c + (255 - c) * v) for c in border)
        fill = (60, 60, 60) if b.defeated else self.theme.hud_bg
        surf.blit(rounded_panel(r.size, fill, border, PILL_H // 2, 3), r.topleft)
        icon = self.icon
        if self.shake:
            icon = icon.copy()
            icon.fill((120, 40, 40), special_flags=pg.BLEND_RGB_ADD)
        surf.blit(icon, icon.get_rect(center=(r.x + 34, r.centery)))
        name = i18n.t(b.name_key)
        draw_text(surf, name, fit_size(name, 28, 200), (r.x + 66, r.centery - 1), (240, 240, 240),
                  anchor="midleft")
        for i in range(b.max_hp):
            img = heart_sprite(32, (225, 50, 65) if i < b.hp else (80, 80, 80))
            surf.blit(img, img.get_rect(center=(r.right - 40 - (b.max_hp - 1 - i) * 38, r.centery + 1)))

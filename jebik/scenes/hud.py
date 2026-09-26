"""Top HUD bar (layout from the scene.py mockup).

Colours come from the world's :class:`~jebik.worlds.base.Theme`. EZZZ shows
hearts; TOBI PIZDA shows the countdown timer in the same place. Boss levels
add a :class:`~jebik.scenes.boss_pill.BossPill` under the bar.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from .. import config, i18n
from ..art.chars import fly_sprite
from ..art.common import (arc_ring, arrow_up_sprite, draw_text, heart_sprite,
                          render_ss, text_surface)
from ..game.rules import DIFFICULTY_NAMES
from ..game.world import World
from ..worlds import world_by_id
from .boss_pill import BossPill

W = config.SCREEN_W
HB = config.HUD_H


class Hud:
    def __init__(self, world: World, profile_name: str):
        self.world = world
        self.profile_name = profile_name
        self.t = 0.0
        self.count_pulse = 0.0
        self.heart_anim = [0.0] * world.rules.max_hearts   # >0 pop, <0 loss
        self.super_shake = 0.0
        self.super_flash = 0.0
        self._last_hearts = world.hearts
        self._last_count = world.eaten
        self._was_ready = True
        self.theme = world_by_id(world.level.world).theme
        self.bar = pg.Surface((W, HB + 4))
        self.bar.fill(self.theme.hud_bg)
        pg.draw.line(self.bar, self.theme.hud_line, (0, HB), (W, HB), 4)
        self.fly_icon = fly_sprite(1.3, "fly")
        self.pause_rect = pg.Rect(W - 330, 0, 330, HB)     # click = pause
        self.time_flash = 0.0                               # golden fly +10 s
        self._last_time = world.time_left
        boss = world.boss
        self.boss_pill = BossPill(boss, world.level.world) if boss is not None else None

    def deny_super(self) -> None:
        self.super_shake = 0.35

    def update(self, dt: float) -> None:
        w = self.world
        self.t += dt
        self.count_pulse = max(0.0, self.count_pulse - dt)
        self.super_shake = max(0.0, self.super_shake - dt)
        self.super_flash = max(0.0, self.super_flash - dt)
        if w.eaten != self._last_count:
            self.count_pulse = 0.35
            self._last_count = w.eaten
        if w.hearts != self._last_hearts:
            lo, hi = sorted((w.hearts, self._last_hearts))
            sign = 1 if w.hearts > self._last_hearts else -1
            for i in range(lo, hi):
                if i < len(self.heart_anim):
                    self.heart_anim[i] = 0.5 * sign
            self._last_hearts = w.hearts
        for i, a in enumerate(self.heart_anim):
            if a > 0:
                self.heart_anim[i] = max(0.0, a - dt)
            elif a < 0:
                self.heart_anim[i] = min(0.0, a + dt)
        ready = w.frog.super_cd <= 0
        if ready and not self._was_ready:
            self.super_flash = 0.4
        self._was_ready = ready
        self.time_flash = max(0.0, self.time_flash - dt)
        if w.time_left is not None and self._last_time is not None and w.time_left > self._last_time + 0.5:
            self.time_flash = 0.6
        self._last_time = w.time_left
        if self.boss_pill:
            self.boss_pill.update(dt)

    def draw(self, surf: pg.Surface) -> None:
        w = self.world
        surf.blit(self.bar, (0, 0))
        lv = w.level
        draw_text(surf, i18n.t("game.level_name", w=lv.world_index, l=lv.level_index), 36, (40, 16),
                  config.C_HUD_TEXT, anchor="topleft")
        draw_text(surf, f"{self.profile_name} · {DIFFICULTY_NAMES[w.rules.difficulty]}", 26, (44, 64),
                  self.theme.hud_sub, bold=False, anchor="topleft")
        # fly counter
        full = w.full
        pulse = 1 + 0.25 * math.sin(self.count_pulse / 0.35 * math.pi) if self.count_pulse else 1.0
        col = config.C_GOOD if full else config.C_HUD_COUNTER
        img = text_surface(f"{w.eaten} / {w.needed}", 50, col, True)
        if pulse != 1.0:
            img = pg.transform.smoothscale(img, (int(img.get_width() * pulse), int(img.get_height() * pulse)))
        surf.blit(img, img.get_rect(center=(880, 44)))
        bob = math.sin(self.t * 5) * 2
        surf.blit(self.fly_icon, self.fly_icon.get_rect(center=(780, 48 + bob)))
        if full and not w.exit_ready:
            hint = i18n.t("game.full_boss")
        elif full:
            hint = exit_hint(lv.world)
        else:
            hint = i18n.t("game.need_exact", n=w.needed)
        draw_text(surf, hint, 22, (880, 90), config.C_GOOD if full else config.C_HUD_HINT, bold=False)
        if w.rules.uses_hearts:
            self._draw_hearts(surf)
        else:
            self._draw_timer(surf)
        self._draw_rings(surf)
        draw_text(surf, i18n.t("game.pause_hint"), 26, (W - 34, 55), config.C_HUD_MUTED, bold=False,
                  anchor="midright")
        if self.boss_pill:
            self.boss_pill.draw(surf, (W // 2, HB + 12 + 22))

    def _draw_hearts(self, surf: pg.Surface) -> None:
        w = self.world
        for i in range(w.rules.max_hearts):
            filled = i < w.hearts
            a = self.heart_anim[i]
            size = 46
            if a > 0:
                size = int(46 * (1 + 0.4 * math.sin((0.5 - a) / 0.5 * math.pi)))
            img = heart_sprite(size, config.C_HEART if filled else config.C_HEART_EMPTY)
            jx = math.sin(a * 60) * 6 if a < 0 else 0
            surf.blit(img, img.get_rect(center=(1100 + i * 58 + jx, 52)))

    def _draw_timer(self, surf: pg.Surface) -> None:
        """TOBI PIZDA countdown where the hearts would be."""
        left = self.world.time_left or 0.0
        warn = left <= config.TOBI_WARN_TIME
        col = config.C_HEART if warn else config.C_HUD_TEXT
        if self.time_flash:
            col = config.C_HUD_COUNTER
        secs = math.ceil(left)
        text = f"{secs // 60}:{secs % 60:02d}"
        size = 50
        if warn and left > 0:
            size = int(50 * (1 + 0.12 * max(0.0, math.sin(left * math.pi * 2))))
        if self.time_flash:
            size = int(50 * (1 + 0.3 * self.time_flash))
        cx, cy = 1160, 50
        clock = clock_icon(40, col)
        surf.blit(clock, clock.get_rect(center=(cx - 92, cy + 2)))
        img = text_surface(text, size, col, True)
        surf.blit(img, img.get_rect(midleft=(cx - 60, cy)))

    def _draw_rings(self, surf: pg.Surface) -> None:
        w = self.world
        # super jump ring
        frac = round(w.frog.super_ready_fraction() * 64) / 64
        ready = frac >= 1
        sx = 1360 + (math.sin(self.super_shake * 50) * 6 if self.super_shake else 0)
        col = (120, 220, 90) if ready else (95, 160, 85)
        ring = arc_ring(34, 6, frac, col, self.theme.ring_bg)
        surf.blit(ring, ring.get_rect(center=(sx, 55)))
        if self.super_flash:
            glow = arc_ring(40, 4, 1.0, (200, 255, 170), (0, 0, 0, 0))
            glow = glow.copy()
            glow.set_alpha(int(255 * self.super_flash / 0.4))
            surf.blit(glow, glow.get_rect(center=(sx, 55)))
        arrow = arrow_up_sprite(34, (235, 245, 230) if ready else (150, 170, 150))
        surf.blit(arrow, arrow.get_rect(center=(sx, 55)))
        # firefly ring
        ff = w.frog.firefly / config.FIREFLY_DURATION
        ring = arc_ring(34, 6, round(ff * 64) / 64, (255, 230, 100), self.theme.ring_bg)
        surf.blit(ring, ring.get_rect(center=(1450, 55)))
        icon = fly_sprite(1.3, "firefly")
        if ff <= 0:
            icon = icon.copy()
            icon.set_alpha(90)
        surf.blit(icon, icon.get_rect(center=(1450, 57)))


def exit_hint(world_id: str) -> str:
    """«стрибай на лотос / у нору / на веселку» — ``<world>.exit_hint`` if defined."""
    key = f"{world_id}.exit_hint"
    return i18n.t(key) if i18n.has(key) else i18n.t("game.full_sub")


@lru_cache(maxsize=8)
def clock_icon(size: int, col: tuple) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        c = size * ss / 2
        pg.draw.circle(s, col, (c, c), c * .92)
        pg.draw.circle(s, (30, 30, 30), (c, c), c * .72)
        pg.draw.line(s, col, (c, c), (c, c * .5), max(1, int(c * .14)))
        pg.draw.line(s, col, (c, c), (c * 1.35, c * 1.1), max(1, int(c * .14)))
        pg.draw.rect(s, col, (c * .8, 0, c * .4, c * .2))
    return render_ss((size, size), draw)

"""Renderers of the pike and the heron (mockup art from ``characters.py``)."""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.common import render_ss
from ....art.enemy_art import EnemyArt, register_enemy_art
from ....game.grid import DIRS
from .. import heron as hn
from .. import pike as pk
from .characters import draw_heron, draw_pike


LUNGE_SCALE = 1.45        # the leaping pike, relative to its 96x44 design size


@lru_cache(maxsize=8)
def pike_sprite(k: float) -> pg.Surface:
    """Pike leaping out of a splash ring, head toward +x."""
    w, h = int(96 * k), int(44 * k)
    return render_ss((w, h), lambda s, ss: draw_pike(s, (w * ss / 2 + 4 * k * ss, h * ss / 2), k * ss))


@lru_cache(maxsize=8)
def pike_sprite_left(k: float) -> pg.Surface:
    return pg.transform.flip(pike_sprite(k), True, False)


@lru_cache(maxsize=8)
def heron_sprite(k: float) -> pg.Surface:
    w, h = int(160 * k), int(150 * k)
    return render_ss((w, h), lambda s, ss: draw_heron(s, (w * ss / 2 - 18 * k * ss, h * ss / 2 + 51 * k * ss),
                                                      k * ss, shadow=False))


@lru_cache(maxsize=8)
def heron_shadow(k: float) -> pg.Surface:
    w, h = int(140 * k), int(110 * k)
    return render_ss((w, h), lambda s, ss: draw_heron(s, (w * ss / 2, h * ss / 2), k * ss, shadow_only=True))


@register_enemy_art("pike")
class PikeArt(EnemyArt):
    def draw(self, surf: pg.Surface, enemy, off) -> None:
        if enemy.state != pk.LUNGE or enemy.water is None or enemy.target is None:
            return
        # the lunge is drawn in the AIR layer (the pike leaps over the pad and
        # the frog on it) and big enough to read as a real threat
        u = enemy.lunge_progress()
        out = min(1.0, math.sin(math.pi * u) * 1.35)
        wx, wy = enemy.water
        tx, ty = enemy.target
        x, y = self.px((wx + (tx - wx) * out * 0.8, wy + (ty - wy) * out * 0.8 - 0.35 * math.sin(math.pi * u)), off)
        base = pike_sprite(round(self.k * LUNGE_SCALE, 3))           # head toward +x
        if tx < wx:                                   # leaping left: mirror, don't turn belly-up
            base = pike_sprite_left(round(self.k * LUNGE_SCALE, 3))
            ang = -math.degrees(math.atan2(ty - wy, wx - tx))
        else:
            ang = -math.degrees(math.atan2(ty - wy, tx - wx))
        if ty == wy:                                  # nose up on the way out, down on the way in
            ang += (0.5 - u) * 40 * (1 if tx > wx else -1)
        img = pg.transform.rotozoom(base, ang, 0.8 + 0.2 * out)
        if u < 0.2 or u > 0.85:                       # breaking / re-entering the surface
            a = min(u / 0.2, (1 - u) / 0.15) if u > 0.85 else u / 0.2
            img.set_alpha(int(120 + 135 * max(0.0, min(1.0, a))))
        surf.blit(img, img.get_rect(center=(round(x), round(y))))

    def draw_telegraph(self, surf: pg.Surface, enemy, tg, off) -> bool:
        if tg.style != "bubbles":
            return False
        k, t = self.k, self.view.t
        p = tg.progress
        for c in tg.cells:
            x, y = self.px(c, off)
            if tg.direction is not None:                  # lean toward the pad
                dx, dy = DIRS[tg.direction]
                x, y = x + dx * self.cs * 0.18, y + dy * self.cs * 0.18
            w = max(1, int(1.8 * k))
            for i, (bx, by, r) in enumerate([(-8, 4, 5), (7, -6, 7), (2, 10, 3), (12, 8, 4),
                                             (-12, -8, 3), (-2, -12, 4)][:3 + int(p * 3.5)]):
                rise = ((t * 1.6 + i * 0.37) % 1.0)
                rr = r * k * (0.7 + 0.5 * rise) * (1 + p * 0.4)
                pg.draw.circle(surf, (225, 245, 255), (x + bx * k, y + by * k - rise * 8 * k), rr, w)
            pg.draw.circle(surf, (40, 90, 110), (x, y), self.cs * (0.22 + 0.1 * p), max(1, int(2 * k)))
        return True


@register_enemy_art("heron")
class HeronArt(EnemyArt):
    def draw(self, surf: pg.Surface, enemy, off) -> None:
        if enemy.state == hn.AWAY or enemy.target is None:
            return
        u = enemy.phase()
        if enemy.state == hn.SHADOW:
            far = (1 - u) ** 1.5
            alpha = int(255 * min(1.0, u * 1.6))
        elif enemy.state == hn.STRIKE:
            far, alpha = 0.0, 255
        else:
            far, alpha = u ** 1.5, int(255 * (1 - u))
        x, y = self.px(enemy.target, off)
        x += far * self.cs * 3.0
        y -= far * self.cs * 4.0
        img = heron_sprite(self.k)
        if enemy.state == hn.STRIKE:                     # peck: a quick dip + splash marks
            y += math.sin(min(1.0, u * 2.5) * math.pi) * 8 * self.k
            for a in range(0, 360, 60):
                r = self.cs * (0.2 + 0.25 * u)
                ex = x + math.cos(math.radians(a)) * r
                ey = y + math.sin(math.radians(a)) * r * 0.6
                pg.draw.circle(surf, (235, 250, 255), (ex, ey), max(1.0, 3 * self.k * (1 - u)))
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        surf.blit(img, img.get_rect(center=(round(x + 18 * self.k), round(y - 51 * self.k))))

    def draw_telegraph(self, surf: pg.Surface, enemy, tg, off) -> bool:
        if tg.style != "shadow":
            return False
        base = heron_shadow(self.k)
        sc = 0.45 + 0.55 * tg.progress
        img = pg.transform.smoothscale(base, (max(1, int(base.get_width() * sc)),
                                              max(1, int(base.get_height() * sc))))
        for c in tg.cells:
            x, y = self.px(c, off)
            core = pg.Rect(0, 0, self.cs * (0.5 + 0.4 * tg.progress), self.cs * (0.32 + 0.25 * tg.progress))
            core.center = (round(x), round(y))
            dark = pg.Surface(core.size, pg.SRCALPHA)
            pg.draw.ellipse(dark, (10, 25, 40, int(80 + 110 * tg.progress)), dark.get_rect())
            surf.blit(img, img.get_rect(center=(round(x), round(y))))
            surf.blit(img, img.get_rect(center=(round(x), round(y))))
            surf.blit(dark, core)
            if tg.progress > 0.55:                        # blinking red rim just before the beak
                if math.sin(self.view.t * 22) > 0:
                    r = pg.Rect(0, 0, self.cs * .8, self.cs * .55)
                    r.center = (round(x), round(y))
                    pg.draw.ellipse(surf, (235, 60, 70), r, max(2, int(3 * self.k)))
        return True

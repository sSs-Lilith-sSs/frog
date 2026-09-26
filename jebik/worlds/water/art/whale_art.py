"""Renderer of Кит (mockup ``draw_whale``) and its attack warnings."""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.common import disc_sprite, render_ss
from ....art.enemy_art import EnemyArt, register_enemy_art
from ....game.grid import DIRS
from .. import whale as wh
from .characters import draw_whale

MARGIN = 1.2          # extra cells around the 6x3 body (fins, tail, hearts)


@lru_cache(maxsize=16)
def whale_sprite(cs: int, surfaced: bool, hp: int, flip: bool) -> pg.Surface:
    """The whale over a 6x3-cell rect (head left unless ``flip``)."""
    w, h = int(cs * (6 + 2 * MARGIN)), int(cs * (3 + 2 * MARGIN))
    k = cs / 64

    def draw(s: pg.Surface, ss: float) -> None:
        rect = (MARGIN * cs * ss, MARGIN * cs * ss, 6 * cs * ss, 3 * cs * ss)
        draw_whale(s, rect, k * ss, surfaced=surfaced, hp=hp)
    img = render_ss((w, h), draw, ss=2)
    return pg.transform.flip(img, True, False) if flip else img


@lru_cache(maxsize=8)
def whale_icon(size: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        pg.draw.circle(s, (40, 110, 160), (size * ss / 2, size * ss / 2), size * ss * .48)
        draw_whale(s, (size * ss * .12, size * ss * .3, size * ss * .8, size * ss * .42),
                   size * ss / 260, hearts=False)
    return render_ss((size, size), draw)


@register_enemy_art("whale")
class WhaleArt(EnemyArt):
    def draw(self, surf: pg.Surface, enemy, off) -> None:
        surfaced = enemy.surfaced
        img = whale_sprite(self.cs, surfaced, enemy.hp, enemy.facing > 0)
        x, y = self.px(enemy.pos, off)
        if surfaced:
            y += math.sin(self.view.t * 2.2) * 2 * self.k
            if enemy.state == wh.DIVE_WARN:                  # sinking: bob + fade blink
                p = 1 - enemy.timer / max(1e-6, enemy.warn_total)
                y += p * 6 * self.k + math.sin(self.view.t * 30) * 2 * self.k
                img = img.copy()
                img.set_alpha(int(255 - 90 * p * (0.5 + 0.5 * math.sin(self.view.t * 14))))
            if enemy.hit_flash > 0:
                img = img.copy()
                v = int(160 * enemy.hit_flash / 0.6)
                img.fill((v, v, v, 0), special_flags=pg.BLEND_RGBA_ADD)
        elif enemy.state == wh.SURF_WARN:                    # rising: darker silhouette
            p = 1 - enemy.timer / max(1e-6, enemy.warn_total)
            img = img.copy()
            img.set_alpha(int(150 + 105 * p))
        surf.blit(img, img.get_rect(center=(round(x), round(y))))
        if enemy.state == wh.DIVE_WARN:
            self._dive_bubbles(surf, enemy, off)

    def _dive_bubbles(self, surf, enemy, off) -> None:
        t = self.view.t
        for i, c in enumerate(sorted(enemy.back)):
            if (i * 7) % 3:
                continue
            x, y = self.px(c, off)
            a = t * 3 + i
            d = disc_sprite(max(1.5, round(3 * self.k * 2) / 2), (235, 250, 255))
            surf.blit(d, d.get_rect(center=(round(x + math.sin(a) * self.cs * .3),
                                            round(y - ((t + i * .3) % 1.0) * self.cs * .4))))

    # ------------------------------------------------------------ warnings
    def draw_telegraph(self, surf: pg.Surface, enemy, tg, off) -> bool:
        if tg.style == "dive":
            return True                                     # drawn with the body
        if tg.style == "jet":
            self._jet(surf, tg, off)
            return True
        if tg.style == "wave":
            self._wave(surf, tg, off)
            return True
        if tg.style == "gulp":
            self._gulp(surf, enemy, tg, off)
            return True
        return False

    def _jet(self, surf, tg, off) -> None:
        if not tg.cells:
            return
        k, cs, t = self.k, self.cs, self.view.t
        a = self.px(tg.cells[0], off)
        b = self.px(tg.cells[-1], off)
        horiz = tg.direction in (1, 3)
        wid = cs * (0.55 + 0.1 * math.sin(t * 25))
        if horiz:
            r = pg.Rect(a[0] - cs / 2, a[1] - wid / 2, b[0] - a[0] + cs, wid)
        else:
            r = pg.Rect(a[0] - wid / 2, a[1] - cs / 2, wid, b[1] - a[1] + cs)
        layer = pg.Surface(r.size, pg.SRCALPHA)
        lr = layer.get_rect()
        pg.draw.rect(layer, (150, 215, 245, 190), lr, border_radius=int(wid / 2))
        pg.draw.rect(layer, (240, 252, 255, 230), lr.inflate(-wid * .5 if horiz else -wid * .55,
                                                             -wid * .55 if horiz else 0),
                     border_radius=int(wid / 4))
        surf.blit(layer, r)
        for c in tg.cells[::2]:
            x, y = self.px(c, off)
            for i in range(2):
                ph = t * 9 + i * 2 + c[0] + c[1]
                d = disc_sprite(max(1.5, round((2.5 + i) * k * 2) / 2), (245, 252, 255))
                dx = math.sin(ph) * wid * .6 if not horiz else math.sin(ph) * cs * .4
                dy = math.cos(ph) * wid * .6 if horiz else math.cos(ph) * cs * .4
                surf.blit(d, d.get_rect(center=(round(x + dx), round(y + dy))))

    def _wave(self, surf, tg, off) -> None:
        if not tg.cells:
            return
        k, cs, t = self.k, self.cs, self.view.t
        dx, dy = DIRS[tg.direction or 0]
        for c in tg.cells:
            x, y = self.px(c, off)
            for j, (col, back) in enumerate((((60, 150, 200), .3), ((170, 225, 245), .1), ((250, 255, 255), -.05))):
                rx = cs * (0.28 if dx else 0.55) - j * 3 * k
                ry = cs * (0.55 if dx else 0.28) - j * 3 * k
                cx, cy = x - dx * back * cs, y - dy * back * cs
                wob = math.sin(t * 8 + (c[1] if dx else c[0])) * 3 * k
                pg.draw.ellipse(surf, col, (cx - rx + (0 if dx else wob), cy - ry + (wob if dx else 0), 2 * rx, 2 * ry))

    def _gulp(self, surf, enemy, tg, off) -> None:
        k, cs, t = self.k, self.cs, self.view.t
        dx, dy = DIRS[tg.direction or 0]
        mx, my = self.px((enemy.mouth[0] - dx * 0.55, enemy.mouth[1] - dy * 0.55), off)
        open_ = min(1.0, 0.3 + tg.progress * 1.2) if enemy.state == wh.GULP_WARN else 1.0
        rw = cs * (1.6 if dy else 0.9) * open_
        rh = cs * (0.9 if dy else 1.6) * open_
        pg.draw.ellipse(surf, (25, 45, 80), (mx - rw / 2, my - rh / 2, rw, rh))
        pg.draw.ellipse(surf, (200, 80, 100), (mx - rw / 3, my - rh / 3, rw * 2 / 3, rh * 2 / 3))
        pg.draw.ellipse(surf, (215, 242, 250), (mx - rw / 2, my - rh / 2, rw, rh), max(2, int(3 * k)))
        if enemy.state != wh.GULP:
            return
        for i in range(10):                                 # swirling streaks toward the mouth
            u = (t * 1.3 + i / 10) % 1.0
            dist = (1 - u) * 5.5 * cs
            side = ((i * 37) % 11 - 5) / 5 * cs * 1.6 * (1 - u * .7)
            x = mx - dx * dist + (side if dy else 0)
            y = my - dy * dist + (side if dx else 0)
            ln = cs * .35
            pg.draw.line(surf, (225, 245, 255), (x, y), (x + dx * ln, y + dy * ln), max(1, int(2 * k)))

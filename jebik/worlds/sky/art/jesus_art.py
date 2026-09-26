"""Renderer of the boss «Ісус»: cached pose sprites, cloud, halo boomerang,
palm beams and the cloud-rebuild warning."""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.common import render_ss
from ....art.enemy_art import EnemyArt, register_enemy_art
from ..jesus import bezier
from .birds import blit_c
from .field import cloud_sprite
from .jesus_figure import HALO_Y, HEAD_Y, boss_cloud, draw_jesus, halo_flat, halo_ring, palm_rays
from .paint import burst, comic_stars, dashed_line, glow, sparkle

GOLD_BAND = (255, 210, 80)
FIG_W, FIG_H, FIG_BASE = 180, 150, 136          # sprite box in units; robe/cloud line at FIG_BASE


@lru_cache(maxsize=16)
def figure_sprite(u: float, arms: str, face: str) -> tuple[pg.Surface, tuple]:
    """Pose sprite + palm offsets (px, relative to the robe/cloud anchor)."""
    w, h = int(FIG_W * u), int(FIG_H * u)
    palms: list = []

    def draw(s: pg.Surface, ss: float) -> None:
        palms.extend(draw_jesus(s, w * ss / 2, FIG_BASE * u * ss, u * ss, arms, face))
    img = render_ss((w, h), draw, ss=3)
    offs = tuple((px / 3 - w / 2, py / 3 - FIG_BASE * u) for px, py in palms)
    return img, offs


@lru_cache(maxsize=4)
def cloud_img(u: float) -> pg.Surface:
    w, h = int(200 * u), int(90 * u)
    return render_ss((w, h), lambda s, ss: boss_cloud(s, w * ss / 2, 40 * u * ss, u * ss), ss=3)


@lru_cache(maxsize=8)
def halo_img(u: float, dim: bool = False, tilt: int = 0) -> pg.Surface:
    size = int(60 * u)
    return render_ss((size, size), lambda s, ss: halo_flat(s, size * ss / 2, size * ss / 2, u * ss, dim, tilt), ss=3)


@lru_cache(maxsize=4)
def ring_img(u: float) -> pg.Surface:
    size = int(56 * u)
    return render_ss((size, size), lambda s, ss: halo_ring(s, size * ss / 2, size * ss / 2, u * ss), ss=3)


@lru_cache(maxsize=4)
def burst_img(r: int) -> pg.Surface:
    size = int(r * 2.8)
    return render_ss((size, size), lambda s, ss: burst(s, size * ss / 2, size * ss / 2, r * ss, seed=5), ss=3)


POSES = {"idle": ("open", "smile"), "beams": ("open", "smile"), "multiply": ("up", "happy"),
         "halo": ("point", "wink"), "rebuild": ("open", "smile"), "hit": ("open", "ouch"),
         "sad": ("down", "sad")}


@register_enemy_art("jesus")
class JesusArt(EnemyArt):
    def __init__(self, view):
        super().__init__(view)
        lv = view.level
        self.u = round(max(0.55, min(1.3, lv.top_reserve / 167 if lv.top_reserve else .7)), 3)
        self.ru = round(1.25 * self.cs / 50, 3)           # halo ring size on the field
        self.rot: dict = {}
        self.layer: pg.Surface | None = None

    # ------------------------------------------------------------ helpers
    def anchor(self, boss, off) -> tuple[float, float]:
        hx, hy = self.px(boss.pos, off)
        bob = math.sin(self.view.t * 1.6) * 3 * self.u if not boss.defeated else 0
        return hx, hy - HEAD_Y * self.u + bob

    def _pose(self, boss) -> tuple[str, str]:
        if boss.defeated:
            return POSES["sad"]
        if boss.state == "halo" and boss.halo_phase == "bonk":
            return ("open", "surprised")
        if boss.state == "idle" and (self.view.t % 4.0) < 0.15:
            return ("open", "happy")                       # a blink now and then
        return POSES.get(boss.state, POSES["idle"])

    def _alpha_layer(self) -> pg.Surface:
        if self.layer is None:
            self.layer = pg.Surface(self.view_size(), pg.SRCALPHA)
        return self.layer

    def view_size(self) -> tuple[int, int]:
        from .... import config
        return config.SCREEN_W, config.SCREEN_H

    def _line_ends(self, cells, off):
        a, b = self.px(cells[0], off), self.px(cells[-1], off)
        cs = self.cs
        if cells[0][1] == cells[-1][1]:                    # row
            return (a[0] - cs * .4, a[1]), (b[0] + cs * .4, b[1]), True
        return (a[0], a[1] - cs * .4), (b[0], b[1] + cs * .4), False

    # ------------------------------------------------------------ draw
    def draw(self, surf, boss, off) -> None:
        u, t = self.u, self.view.t
        cx, cy = self.anchor(boss, off)
        arms, face = self._pose(boss)
        img, palm_offs = figure_sprite(u, arms, face)
        palms = [(cx + dx, cy + dy) for dx, dy in palm_offs]
        glow(surf, cx, cy - 70 * u, 120 * u, (255, 245, 210), 90)
        if boss.state == "hit":
            b = burst_img(int(46 * u))
            blit_c(surf, b, cx - 70 * u, cy - 120 * u)
        surf.blit(img, (round(cx - img.get_width() / 2), round(cy - FIG_BASE * u)))
        if boss.state == "beams" and boss.beam_cells:
            self._palm_beams(surf, boss, palms, off)
        cl = cloud_img(u)
        surf.blit(cl, (round(cx - cl.get_width() / 2), round(cy + 15 * u * .88 - 40 * u)))
        head = (cx, cy + HALO_Y * u)
        if boss.defeated:
            blit_c(surf, halo_img(u, True, -14), head[0] + 6 * u, head[1] + 3 * u)
        elif boss.state == "hit":
            blit_c(surf, halo_img(u, False, -22), head[0] + 10 * u, head[1] - 4 * u)
            comic_stars(surf, cx, cy + (HEAD_Y - 30) * u, u, n=4, rad=34, t=t * 3)
        elif boss.halo_phase == "home":
            glow(surf, head[0], head[1], 34 * u, (255, 235, 150), 110)
            blit_c(surf, halo_img(u), head[0], head[1] + math.sin(t * 2.5) * 1.5 * u)
        if boss.state == "beams" or (boss.state == "rebuild" and not boss.defeated):
            for px, py in palms:
                palm_rays(surf, px, py, u, t, 1.0 if boss.beam_on else .5)
        if boss.state == "multiply":
            for i, (px, py) in enumerate(palms):
                for k in range(3):
                    a = t * 3 + k * 2.1 + i
                    sparkle(surf, px + math.cos(a) * 16 * u, py - 14 * u + math.sin(a) * 10 * u, 5 * u)
        if boss.defeated:
            for i in range(3):
                a = t * .7 + i * 2.1
                sparkle(surf, cx + math.cos(a) * 80 * u, cy - 60 * u + math.sin(a * 1.3) * 30 * u, 4 * u,
                        (255, 235, 245))
        if boss.halo_phase != "home":
            self._flying_halo(surf, boss, off)

    def _palm_beams(self, surf, boss, palms, off) -> None:
        layer = self._alpha_layer()
        layer.fill((0, 0, 0, 0))
        on = boss.beam_on
        for axis, idx in boss.lines:
            cells = [c for c in boss.beam_cells if (c[1] == idx if axis == "row" else c[0] == idx)]
            if not cells:
                continue
            a, b, row = self._line_ends(cells, off)
            ends = (a, b) if row else (a, a)
            for (px, py), (tx, ty) in zip(palms, ends):
                d = 22 * self.k
                quad = [(px - 6, py), (px + 6, py), (tx + d, ty), (tx - d, ty)] if row else \
                    [(px - 6, py), (px + 6, py), (tx + d, ty), (tx - d, ty)]
                pg.draw.polygon(layer, (255, 235, 140, 150 if on else 70), quad)
            if on:
                cs = self.cs
                rect = pg.Rect(0, 0, abs(b[0] - a[0]) + 2 if row else cs * .9, cs * .9 if row else abs(b[1] - a[1]) + 2)
                rect.center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                pg.draw.rect(layer, (255, 230, 120, 190), rect, border_radius=int(cs * .4))
                core = rect.inflate(-cs * .5 if not row else 0, -cs * .5 if row else 0)
                pg.draw.rect(layer, (255, 255, 235, 235), core, border_radius=int(cs * .2))
        surf.blit(layer, (0, 0))

    def _flying_halo(self, surf, boss, off) -> None:
        t, ru = self.view.t, self.ru
        x, y = self.px(boss.halo_pos, off)
        if boss.halo_phase in ("out", "back"):             # dotted trail behind it
            total = 1.5
            k = min(1.0, boss.halo_t / total)
            for i in range(8):
                kk = max(0.0, k - (i + 1) * .035)
                p = bezier(boss.halo_from, boss.halo_ctrl, boss.halo_to,
                           1 - (1 - kk) ** 2 if boss.halo_phase == "out" else kk * kk)
                qx, qy = self.px(p, off)
                pg.draw.circle(surf, (255, 240, 170), (qx, qy), max(1.0, 4 * self.k * (1 - i / 9)))
        glow(surf, x, y, 36 * ru, (255, 235, 150), 130)
        spin = int((t * 540 if boss.halo_phase == "bonk" else t * 220) / 15) * 15 % 360
        key = ("ring", spin)
        img = self.rot.get(key)
        if img is None:
            img = self.rot[key] = pg.transform.rotozoom(ring_img(ru), spin, 1.0)
        blit_c(surf, img, x, y)
        if boss.halo_phase == "hover":
            r = self.cs * (.55 + .08 * math.sin(t * 8))
            pg.draw.circle(surf, (255, 250, 210), (x, y), r, max(1, int(2 * self.k)))

    # ------------------------------------------------------------ warnings
    def draw_telegraph(self, surf, boss, tg, off) -> bool:
        v, cs, k = self.view, self.cs, self.k
        p = tg.progress
        blink = .5 + .5 * math.sin(v.t * (8 + 16 * p))
        if tg.style == "line" and tg.cells:
            a, b, row = self._line_ends(list(tg.cells), off)
            rect = pg.Rect(0, 0, abs(b[0] - a[0]) if row else cs, cs if row else abs(b[1] - a[1]))
            rect.center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            lay = pg.Surface(rect.size, pg.SRCALPHA)
            lay.fill((*GOLD_BAND, int(60 + 60 * p * blink)))
            surf.blit(lay, rect)
            dashed_line(surf, a, b, (255, 185, 40), max(2, int(4 * k)), 22 * k, 12 * k, phase=v.t * 2)
            return True
        if tg.style == "zone":
            for c in tg.cells:                              # clouds about to vanish
                x, y = v.to_px(c)
                x, y = x + off[0], y + off[1]
                r = pg.Rect(0, 0, cs - 8, cs - 8)
                r.center = (round(x), round(y))
                lay = pg.Surface(r.size, pg.SRCALPHA)
                pg.draw.rect(lay, (80, 40, 110, int(60 + 90 * p * blink)), lay.get_rect(), border_radius=int(cs * .25))
                surf.blit(lay, r)
                pg.draw.rect(surf, (255, 255, 255), r, max(1, int(2 * k)), border_radius=int(cs * .25))
            ghost = cloud_sprite(self.cs, 0).copy()
            ghost.set_alpha(int(50 + 130 * p))
            for c in getattr(boss, "appear", ()):         # clouds about to appear
                x, y = v.to_px(c)
                blit_c(surf, ghost, x + off[0], y + off[1])
                sparkle(surf, x + off[0] + cs * .3, y + off[1] - cs * .3, 5 * k * (0.6 + blink * .6), (255, 255, 255))
            return True
        return False


@lru_cache(maxsize=4)
def jesus_portrait(size: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        u = size * ss / 62
        draw_jesus(s, size * ss / 2, size * ss / 2 - (HEAD_Y + 2) * u, u, "open", "smile")
    return render_ss((size, size), draw, ss=3)

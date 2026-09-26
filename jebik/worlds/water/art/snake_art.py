"""Smooth snake renderer: the mockup look built from anti-aliased discs.

The body follows the (interpolated) segment positions, tapers toward the tail
and slithers with a small sideways wave; the head sprite is rotated to the
direction of travel and flicks its forked tongue now and then.
"""
from __future__ import annotations

import math

import pygame as pg

from ....art.common import disc_sprite
from ....art.enemy_art import EnemyArt, register_enemy_art
from .characters import (SNAKE_BELLY, SNAKE_BODY, SNAKE_SHADOW, SNAKE_SPOT,
                         snake_head_sprite)

Point = tuple[float, float]


def _q(r: float) -> float:
    return max(1.0, round(r * 2) / 2)          # 0.5 px radius steps for caching


def _blit_disc(surf: pg.Surface, col, r: float, p: Point, alpha: int = 255) -> None:
    img = disc_sprite(_q(r), col)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, img.get_rect(center=(round(p[0]), round(p[1]))))


class SnakeArt:
    def __init__(self, cell: int):
        self.cell = cell
        self.k = cell / 64

    def _samples(self, pts: list[Point], anim: float) -> list[tuple[Point, float]]:
        """Points along the body polyline with a slither offset + taper."""
        k, cell = self.k, self.cell
        seglens = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        total = sum(seglens) or 1.0
        spacing = max(1.5, 2.2 * k)
        out: list[tuple[Point, float]] = []
        dist_along = 0.0
        for i, L in enumerate(seglens):
            if L < 1e-6:
                continue
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            tx, ty = (x1 - x0) / L, (y1 - y0) / L
            n = max(1, int(L / spacing))
            for j in range(n):
                f = j / n
                s = dist_along + L * f
                u = s / total
                amp = cell * 0.075 * min(1.0, s / (cell * 0.7))
                wave = math.sin(s / (cell * 0.95) * 2 * math.pi - anim * 7.0) * amp
                x = x0 + (x1 - x0) * f - ty * wave
                y = y0 + (y1 - y0) * f + tx * wave
                out.append(((x, y), u))
            dist_along += L
        last = pts[-1]
        out.append((last, 1.0))
        return out

    def draw(self, surf: pg.Surface, pts: list[Point], head_dir: Point, anim: float,
             alpha: int = 255) -> None:
        if len(pts) < 2:
            pts = [pts[0], (pts[0][0] - head_dir[0], pts[0][1] - head_dir[1])]
        k = self.k
        samples = self._samples(pts, anim)
        sh = (3 * k, 5 * k)

        def radius(u: float) -> float:
            return 11 * k * (1 - 0.42 * u ** 1.4)
        # draw tail -> head so the head end overlaps nicely
        seq = samples[::-1]
        for (x, y), u in seq:
            _blit_disc(surf, SNAKE_SHADOW, radius(u) + 1 * k, (x + sh[0], y + sh[1]), alpha)
        for (x, y), u in seq:
            _blit_disc(surf, SNAKE_BODY, radius(u), (x, y), alpha)
        for (x, y), u in seq:
            _blit_disc(surf, SNAKE_BELLY, radius(u) * 0.52, (x, y), alpha)
        # spots every ~half cell along the body
        total = len(samples)
        step = max(1, int(total / max(1, (len(pts) - 1) * 2)))
        for idx in range(step // 2 + step, total - 2, step):
            (x, y), u = samples[idx]
            _blit_disc(surf, SNAKE_SPOT, 4 * k * (1 - 0.35 * u), (x, y), alpha)
        # head
        hx, hy = samples[0][0]
        ang = -math.degrees(math.atan2(head_dir[1], head_dir[0]))
        tongue = (anim % 1.6) < 0.35
        head = pg.transform.rotozoom(snake_head_sprite(k, tongue), ang, 1.0)
        if alpha < 255:
            head.set_alpha(alpha)
        _blit_disc(surf, SNAKE_SHADOW, 14 * k, (hx + sh[0], hy + sh[1]), alpha)
        surf.blit(head, head.get_rect(center=(round(hx), round(hy))))


@register_enemy_art("snake")
class SnakeRenderer(EnemyArt):
    def __init__(self, view):
        super().__init__(view)
        self.art = SnakeArt(self.cs)

    def draw(self, surf: pg.Surface, enemy, off: tuple[int, int]) -> None:
        pts = [self.px(p, off) for p in enemy.segment_positions()]
        self.art.draw(surf, pts, enemy.head_dir(), enemy.anim)

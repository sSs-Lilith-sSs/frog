"""Generic looks for enemy warnings (:class:`~jebik.game.enemy.Telegraph`).

World art may draw its own (``EnemyArt.draw_telegraph``); these defaults make
every attack readable from day one.
"""
from __future__ import annotations

import math

import pygame as pg

from ..art.common import disc_sprite, triangle_sprite
from ..game.enemy import Telegraph

RED = (235, 60, 70)


def _cell_rect(view, cell, off) -> pg.Rect:
    x, y = view.to_px(cell)
    r = pg.Rect(0, 0, view.cs - 6, view.cs - 6)
    r.center = (round(x + off[0]), round(y + off[1]))
    return r


def draw_telegraph(surf: pg.Surface, view, tg: Telegraph, off: tuple[int, int]) -> None:
    p = max(0.0, min(1.0, tg.progress))
    blink = 0.5 + 0.5 * math.sin(view.t * (8 + 18 * p))
    if tg.style == "zone":
        layer = pg.Surface(surf.get_size(), pg.SRCALPHA)
        for c in tg.cells:
            r = _cell_rect(view, c, off)
            pg.draw.rect(layer, (*RED, int(50 + 90 * p * blink)), r, border_radius=int(view.cs * .18))
            pg.draw.rect(layer, (*RED, 220), r, max(2, int(3 * view.k)), border_radius=int(view.cs * .18))
        surf.blit(layer, (0, 0))
    elif tg.style == "line":
        for c in tg.cells:
            x, y = view.to_px(c)
            for i in range(3):
                d = disc_sprite(max(1.5, round(3 * view.k * 2) / 2), RED)
                a = (i / 3 + view.t * 1.5) % 1.0
                dx = (a - .5) * view.cs if tg.direction in (1, 3) else 0
                dy = (a - .5) * view.cs if tg.direction in (0, 2) else 0
                surf.blit(d, d.get_rect(center=(round(x + dx + off[0]), round(y + dy + off[1]))))
    elif tg.style == "arrow" and tg.cells:
        x, y = view.to_px(tg.cells[0])
        size = int(view.cs * (0.5 + 0.2 * blink))
        tri = triangle_sprite(size, tg.direction or 0, RED)
        surf.blit(tri, tri.get_rect(center=(round(x + off[0]), round(y + off[1]))))
    elif tg.style == "shadow":
        for c in tg.cells:
            r = _cell_rect(view, c, off).inflate(-view.cs * (1 - p) * .5, -view.cs * (1 - p) * .5)
            sh = pg.Surface(r.size, pg.SRCALPHA)
            pg.draw.ellipse(sh, (10, 20, 30, int(70 + 100 * p)), sh.get_rect())
            surf.blit(sh, r)
    else:                         # "bubbles", "shake" and unknown styles: rising dots
        for c in tg.cells:
            x, y = view.to_px(c)
            for i in range(4):
                a = view.t * 3 + i * 1.7
                d = disc_sprite(max(1.5, round((2 + i % 2) * view.k * 2) / 2), (235, 245, 255))
                surf.blit(d, d.get_rect(center=(round(x + math.sin(a) * view.cs * .25 + off[0]),
                                                round(y + math.cos(a * 1.3) * view.cs * .2 + off[1]))))

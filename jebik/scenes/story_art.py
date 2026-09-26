"""Generic story-card illustrations (placeholder art, refine later).

``draw_card_art(card, surf, rect, t)`` draws into ``rect``; a world's art
package is asked first (``WorldArt.draw_story``). Static parts are rendered
once per (art id, size) and cached; only small sprites move per frame.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame as pg

from ..art.chars import fly_sprite, frog_front_sprite, frog_sprite
from ..art.common import heart_sprite, lerp, render_ss, star_sprite
from ..art.world_art import art_for
from ..story import Card


@lru_cache(maxsize=8)
def _sky(size: tuple[int, int], top: tuple, bottom: tuple, seed: int) -> pg.Surface:
    w, h = size
    s = pg.Surface(size)
    for y in range(h):
        pg.draw.line(s, lerp(top, bottom, y / h), (0, y), (w, y))
    rnd = random.Random(seed)
    for _ in range(40):
        pg.draw.circle(s, (255, 250, 230), (rnd.randint(0, w), rnd.randint(0, h // 2)), rnd.choice((1, 1, 2)))
    return s


@lru_cache(maxsize=8)
def _pond(size: tuple[int, int]) -> pg.Surface:
    w, h = size

    def draw(s: pg.Surface, ss: float) -> None:
        pg.draw.ellipse(s, (60, 140, 175), (-w * .1 * ss, h * .55 * ss, w * 1.2 * ss, h * .7 * ss))
        for cx, cy, r in ((.5, .78, .16), (.2, .86, .09), (.82, .84, .1)):
            pg.draw.ellipse(s, (40, 110, 60), ((cx - r) * w * ss, (cy - r * .45 + .02) * h * ss,
                                               2 * r * w * ss, r * .9 * h * ss))
            pg.draw.ellipse(s, (95, 190, 90), ((cx - r) * w * ss, (cy - r * .45) * h * ss,
                                               2 * r * w * ss, r * .9 * h * ss))
    return render_ss(size, draw, ss=2)


def _put(surf: pg.Surface, img: pg.Surface, c: tuple[float, float]) -> None:
    surf.blit(img, img.get_rect(center=(round(c[0]), round(c[1]))))


def draw_card_art(card: Card, surf: pg.Surface, rect: pg.Rect, t: float) -> None:
    if card.world and art_for(card.world).draw_story(card, surf, rect, t):
        return
    clip = surf.get_clip()
    surf.set_clip(rect)
    w, h = rect.size
    cx = rect.centerx
    if card.art in ("intro", "rule", "world"):
        surf.blit(_sky(rect.size, (40, 50, 110), (240, 160, 150), 3), rect.topleft)
        surf.blit(_pond(rect.size), rect.topleft)
        frog_y = rect.y + h * .74 - abs(math.sin(t * 2.2)) * 14
        _put(surf, frog_front_sprite(2.0, int(t * 10) % 37 == 0), (cx, frog_y))
        if card.art == "intro":
            for i in range(3):
                a = t * 1.3 + i * 2.1
                _put(surf, fly_sprite(1.5, "fly", int(t * 20 + i) % 2 == 1),
                     (cx + math.cos(a) * w * .28, rect.y + h * .38 + math.sin(a * 1.4) * h * .1))
        elif card.art == "rule":
            for i in range(5):
                _put(surf, fly_sprite(1.3, "fly", int(t * 18 + i) % 2 == 1),
                     (cx - w * .3 + i * w * .15, rect.y + h * .25 + math.sin(t * 3 + i) * 6))
            _put(surf, heart_sprite(60, (225, 50, 65)), (cx + w * .32, rect.y + h * .55))
        else:
            icon = art_for(card.world).icon(int(h * .34)) if card.world else None
            if icon is not None:
                _put(surf, icon, (cx, rect.y + h * .3 + math.sin(t * 1.6) * 8))
    elif card.art == "final":
        surf.blit(_sky(rect.size, (60, 40, 110), (255, 190, 170), 9), rect.topleft)
        for i in range(12):
            a = t * .5 + i * .52
            _put(surf, star_sprite(26 + (i % 3) * 8), (cx + math.cos(a) * w * .38, rect.y + h * .45 + math.sin(a) * h * .3))
        _put(surf, frog_sprite(2.2, 0, "happy"), (cx, rect.y + h * .55 - abs(math.sin(t * 3)) * 16))
        for i in range(3):
            _put(surf, heart_sprite(44, (240, 90, 120)), (cx - 70 + i * 70, rect.y + h * .2 + math.sin(t * 2 + i) * 8))
    surf.set_clip(clip)

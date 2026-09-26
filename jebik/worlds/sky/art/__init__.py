"""Sky-world art: sunset field with pink clouds, swallow / hawk / crow, «Ісус».

Importing this package registers the enemy renderers.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame as pg

from ....art.chars import frog_front_sprite
from ....art.common import render_ss
from ....art.world_art import WorldArt
from . import birds, jesus_art  # noqa: F401  (register the enemy renderers)
from .field import SkyField, cloud_sprite
from .jesus_art import jesus_portrait
from .paint import SKY_STOPS, cloud, far_bird, rainbow_arch, vgrad


@lru_cache(maxsize=4)
def story_picture(w: int, h: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        W, H = w * ss, h * ss
        vgrad(s, s.get_rect(), stops=SKY_STOPS)
        pg.draw.circle(s, (255, 240, 200), (W * .18, H * .28), H * .11)
        rainbow_arch(s, W * .78, H * .95, H * .55, H * .035, alpha=150)
        for i, (x, y) in enumerate([(.2, .72), (.36, .8), (.52, .7), (.68, .82), (.84, .74), (.44, .58)]):
            cloud(s, W * x, H * y, H * .22, ss=ss)
        for x, y in [(.3, .25), (.62, .18), (.7, .32)]:
            far_bird(s, W * x, H * y, H * .03, lw=max(1, int(ss * 2)))
    return render_ss((w, h), draw, ss=2)


class SkyArt(WorldArt):
    field_cls = SkyField

    def icon(self, size: int) -> pg.Surface:
        def draw(s: pg.Surface, ss: float) -> None:
            cloud(s, size * ss / 2, size * ss * .52, size * ss * .95, ss=ss)
        return render_ss((size, size), draw)

    def boss_icon(self, kind: str, size: int) -> pg.Surface | None:
        return jesus_portrait(size) if kind == "jesus" else None

    def draw_story(self, card, surf: pg.Surface, rect: pg.Rect, t: float) -> bool:
        pic = story_picture(rect.w, rect.h)
        surf.blit(pic, rect)
        k = rect.h / 400
        fx, fy = rect.x + rect.w * .52, rect.y + rect.h * .6 + math.sin(t * 2) * 4 * k
        frog = frog_front_sprite(round(1.4 * k, 2), blink=(t % 3.5) < .12)
        surf.blit(frog, frog.get_rect(center=(round(fx), round(fy))))
        return True


ART = SkyArt()

__all__ = ["ART", "SkyArt", "SkyField", "cloud_sprite"]

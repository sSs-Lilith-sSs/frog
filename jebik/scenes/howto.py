"""How to play: six cards with small drawn illustrations."""
from __future__ import annotations

import math

import pygame as pg

from .. import config, i18n
from ..art.chars import (fly_sprite, frog_shadow, frog_sprite)
from ..art.common import (draw_text, heart_sprite, rounded_panel, triangle_sprite, wrap)
from ..art.snake_art import SnakeArt
from ..art.water import exit_sprite, glow_sprite, pad_sprite
from .common import H, W, MenuScene, draw_panel

CARD_W, CARD_H, GAP = 850, 190, 22
ILL_W, ILL_H = 270, 160
K = 0.85                       # sprite scale in the illustrations


def keycap(surf: pg.Surface, rect: pg.Rect, direction: int | None = None, label: str = "") -> None:
    surf.blit(rounded_panel(rect.size, (250, 250, 245), (90, 100, 95), 8, 2, (90, 100, 95), 4),
              rect.topleft)
    if direction is not None:
        tri = triangle_sprite(int(rect.h * .55), direction, (60, 70, 65))
        surf.blit(tri, tri.get_rect(center=rect.center))
    if label:
        draw_text(surf, label, 18, rect.center, (60, 70, 65))


def water_box(holes: list[pg.Rect] = ()) -> pg.Surface:
    s = pg.Surface((ILL_W, ILL_H), pg.SRCALPHA)
    s.blit(rounded_panel((ILL_W, ILL_H), (88, 175, 198), (40, 100, 110), 18, 3), (0, 0))
    for r in holes:
        s.blit(rounded_panel(r.size, (22, 62, 100), (190, 232, 238), min(r.w, r.h) // 3, 3), r.topleft)
    return s


def put(surf: pg.Surface, img: pg.Surface, center: tuple[float, float]) -> None:
    surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


def pad(surf: pg.Surface, center, r: float = 26, a: float = 0.6) -> None:
    put(surf, pad_sprite(r, a, False, K), center)


def ill_move() -> pg.Surface:
    s = water_box()
    pad(s, (82, 80), 34)
    put(s, frog_shadow(K), (82, 86))
    put(s, frog_sprite(K, 0), (82, 80))
    for d, (x, y) in ((0, (196, 48)), (3, (152, 100)), (2, (196, 100)), (1, (240, 100))):
        keycap(s, pg.Rect(x - 20, y - 20, 40, 40), d)
    return s


def ill_super() -> pg.Surface:
    s = water_box([pg.Rect(98, 40, 74, 84)])
    pad(s, (48, 84), 30, 2.0)
    pad(s, (222, 84), 30, 4.0)
    for i in range(1, 12):
        t = i / 12
        x = 48 + (222 - 48) * t
        y = 84 - math.sin(math.pi * t) * 62
        pg.draw.circle(s, (255, 255, 255), (x, y), 3)
    put(s, frog_shadow(K * .8), (135, 96))
    put(s, frog_sprite(K * .9, 1, "jump"), (135, 42))
    return s


def ill_tongue() -> pg.Surface:
    s = water_box()
    for x in (48, 135, 222):
        pad(s, (x, 84), 30, x / 50)
    put(s, frog_shadow(K), (48, 90))
    pg.draw.rect(s, (225, 75, 100), (58, 80, 150, 9), border_radius=4)
    pg.draw.circle(s, (235, 95, 120), (210, 84), 7)
    put(s, frog_sprite(K, 1), (48, 84))
    put(s, fly_sprite(K * 1.1, "fly"), (218, 80))
    return s


def ill_goal() -> pg.Surface:
    s = water_box()
    pill = pg.Rect(14, 52, 136, 56)
    s.blit(rounded_panel(pill.size, config.C_HUD_BG, config.C_HUD_LINE, 20, 3), pill.topleft)
    put(s, fly_sprite(1.0, "fly"), (pill.x + 28, pill.centery))
    draw_text(s, "5 / 5", 30, (pill.x + 88, pill.centery - 2), config.C_GOOD)
    put(s, glow_sprite(70, max_alpha=150), (206, 80))
    put(s, exit_sprite(K), (206, 80))
    return s


def ill_flies() -> pg.Surface:
    s = water_box()
    xs = (36, 102, 168, 234)
    for x, kind in zip(xs, ("fly", "dragon", "gold", "firefly")):
        if kind == "firefly":
            put(s, glow_sprite(34, max_alpha=120), (x, 58))
        put(s, fly_sprite(1.1 if kind != "dragon" else 1.0, kind), (x, 58))
    draw_text(s, "+1", 28, (xs[0], 124), (255, 255, 255), outline=(30, 70, 90), outline_w=3)
    draw_text(s, "+2", 28, (xs[1], 124), (255, 255, 255), outline=(30, 70, 90), outline_w=3)
    put(s, heart_sprite(34, config.C_HEART), (xs[2], 124))
    pg.draw.rect(s, (225, 75, 100), (xs[3] - 26, 119, 44, 9), border_radius=4)
    pg.draw.circle(s, (235, 95, 120), (xs[3] + 20, 123), 7)
    return s


def ill_danger() -> pg.Surface:
    s = water_box([pg.Rect(186, 26, 64, 108)])
    for x, y in ((40, 50), (100, 50), (40, 112), (100, 112), (160, 112)):
        pad(s, (x, y), 26, x / 40 + y)
    SnakeArt(int(64 * K)).draw(s, [(160, 112), (100, 112), (100, 50), (40, 50)], (1, 0), 0.25)
    for r in (10, 18, 26):
        pg.draw.ellipse(s, (210, 240, 250), (218 - r, 80 - r * .45, r * 2, r * .9), 2)
    return s


CARDS = [("howto.move", "howto.move_keys", ill_move),
         ("howto.super", "howto.super_keys", ill_super),
         ("howto.tongue", "howto.tongue_keys", ill_tongue),
         ("howto.goal", "howto.goal_sub", ill_goal),
         ("howto.flies", "howto.bonus", ill_flies),
         ("howto.danger", "howto.danger_sub", ill_danger)]


class HowToScene(MenuScene):
    title_key = "howto.title"
    show_frog = False

    def __init__(self, app):
        super().__init__(app)
        self.images = [fn() for _, _, fn in CARDS]
        x0 = (W - 2 * CARD_W - GAP) // 2
        self.cards = [pg.Rect(x0 + (i % 2) * (CARD_W + GAP), 180 + (i // 2) * (CARD_H + GAP),
                              CARD_W, CARD_H) for i in range(len(CARDS))]
        self.focus.set_widgets([self.back_button(W // 2 - 170, H - 170, 340)])

    def draw_content(self, surf: pg.Surface) -> None:
        for (tk, sk, _), img, r in zip(CARDS, self.images, self.cards):
            draw_panel(surf, r)
            surf.blit(img, (r.x + 16, r.centery - ILL_H // 2 - 2))
            tx = r.x + 16 + ILL_W + 24
            max_w = r.right - tx - 22
            title = wrap(i18n.t(tk), 30, max_w, bold=True)
            sub = wrap(i18n.t(sk), 25, max_w, bold=False)
            total = len(title) * 38 + len(sub) * 32 + 8
            y = r.centery - total // 2 - 2
            for line in title:
                draw_text(surf, line, 30, (tx, y), config.C_INK, anchor="topleft")
                y += 38
            y += 8
            for line in sub:
                draw_text(surf, line, 25, (tx, y), (80, 105, 85), bold=False, anchor="topleft")
                y += 32
        draw_text(surf, i18n.t("howto.pause"), 30, (W // 2, H - 48), (255, 255, 255),
                  outline=(40, 90, 60), outline_w=3)

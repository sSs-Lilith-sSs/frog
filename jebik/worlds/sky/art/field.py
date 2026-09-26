"""Sky field: sunset backdrop with cloud banks, purple abyss, pink cloud tiles,
melting clouds, drifting rows and the rainbow exit (ported from the mockups)."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame as pg

from .... import config, i18n
from ....art.common import lerp, render_ss, triangle
from ....art.field import FieldRenderer
from ....game.events import TILE_WARN
from ....game.tiles import WARNING, Tile
from . import paint as P

W, H = config.SCREEN_W, config.SCREEN_H
HUD_H = config.HUD_H


@lru_cache(maxsize=32)
def cloud_sprite(cs: int, variant: int, streak: int = 0) -> pg.Surface:
    """Cloud tile; ``variant`` 0..2 picks the bump layout, ``streak`` = -1/+1
    adds wind streaks for a row drifting left / right."""
    bumps = list(P.DEFAULT_BUMPS) + ([] if variant == 0 else [((-.25, .25)[variant - 1], -.1, .45)])
    w, h = int(cs * (2.3 if streak else 1.6)), int(cs * 1.6)

    def draw(s: pg.Surface, ss: float) -> None:
        cx, cy, C = w * ss / 2, h * ss / 2, cs * ss
        if streak:
            for k in range(3):
                x0 = cx - streak * (C * .55 + (6 + k * 5) * ss * cs / 75)
                y = cy + (-12 + k * 12) * ss * cs / 75
                pg.draw.line(s, (255, 240, 250, 190), (x0, y), (x0 - streak * C * .28, y), max(1, int(3 * ss * cs / 75)))
        P.cloud(s, cx, cy, C, bumps=bumps, ss=ss)
    return render_ss((w, h), draw, ss=3)


@lru_cache(maxsize=8)
def melting_sprite(cs: int) -> pg.Surface:
    size = int(cs * 1.6)
    return render_ss((size, size), lambda s, ss: P.melting(s, size * ss / 2, size * ss / 2, cs * ss, ss=ss), ss=3)


def puff_cloud(b, cx, cy, w, col, shade, ss) -> None:
    """Soft distant cloud with a flat bottom."""
    n = 5
    for c, dy in ((shade, 6), (col, 0)):
        pg.draw.ellipse(b, c, ((cx - w / 2) * ss, (cy - w * .08 + dy) * ss, w * ss, w * .22 * ss))
        for i in range(n):
            t = i / (n - 1)
            x = cx - w * .38 + t * w * .76
            r = w * (.12 + .1 * math.sin(t * math.pi)) * (1 + ((i * 7 + int(cx)) % 7) / 40)
            pg.draw.circle(b, c, (x * ss, (cy + dy - r * .35) * ss), r * ss)


def cloud_bank(b, x, y, w, h, side, rnd, cols, ss) -> None:
    """Layered distant cloud mass at a screen side (the 'shore')."""
    for li, (col, sh) in enumerate(cols):
        n = int(h / 70) + 3
        radii = [rnd.uniform(.45, .62) for _ in range(n)]
        for colour, dx, dy in ((sh, side * -6, 10), (col, 0, 0)):
            for i in range(n):
                t = i / (n - 1)
                reach = w * (math.sin(t * math.pi) * .35 + .65) * (1 - li * .2)
                cx = (x + reach * .5) if side < 0 else (x - reach * .5)
                pg.draw.circle(b, colour, ((cx + dx) * ss, (y + t * h + dy) * ss), radii[i] * reach * ss)


class SkyField(FieldRenderer):
    fill = (98, 72, 162)
    grid_color = (255, 255, 255, 45)
    # sounds from tools/gen_audio_sky.py; volumes balance the files' loudness,
    # a third value = min gap (several clouds popping in at once -> one sound)
    event_sounds = {
        "sky.swallow_warn": ("sky.whistle", .87),
        "sky.swallow_go": ("sky.swallow", 1.17),
        "sky.hawk_windup": ("sky.hawk", .9),
        "sky.caw": ("sky.caw", 1.4),
        "sky.peck": ("sky.peck", 1.3),
        "sky.crow_eat": ("sky.crow_eat", .9),
        TILE_WARN: ("sky.melt", .64, .3),
        "sky.beam": ("sky.beam", 1.06),
        "sky.multiply": ("sky.multiply", 1.2),
        "sky.halo_throw": ("sky.halo", 1.17),
        "sky.halo_caught": ("sky.halo_catch", .98),
        "sky.rebuild_warn": ("sky.rebuild", 1.1),
        "sky.cloud_new": ("sky.cloud_pop", 1.08, .25),
    }
    tell_sounds = {"beams": ("sky.beam_charge", .95)}

    # ------------------------------------------------------------ backdrop
    def build_static(self) -> pg.Surface:
        ss = config.SS_BACKDROP
        lv, r = self.level, self.rect
        rnd = random.Random(lv.seed * 31 + lv.width * 7 + lv.height)
        b = pg.Surface((W * ss, H * ss))
        P.vgrad(b, b.get_rect(), stops=P.SKY_STOPS)
        boss = lv.boss is not None
        sun = (W // 2, r.y - 200) if boss else (118, 300)
        P.glow(b, sun[0] * ss, sun[1] * ss, 420 * ss, (255, 235, 190), 170)
        P.glow(b, sun[0] * ss, sun[1] * ss, 170 * ss, (255, 245, 215), 200)
        if not boss:
            pg.draw.circle(b, (255, 240, 200), (sun[0] * ss, sun[1] * ss), 62 * ss)
            pg.draw.circle(b, (255, 250, 230), ((sun[0] - 8) * ss, (sun[1] - 8) * ss), 48 * ss)
        rx, ry, rr = (150, 900, 330) if boss else (1840, 760, 300)
        lay = pg.Surface(b.get_size(), pg.SRCALPHA)
        P.rainbow_arch(lay, rx * ss, ry * ss, rr * ss, rr * .06 * ss)
        lay.set_alpha(95)
        b.blit(lay, (0, 0))
        left, right = r.left - 12, r.right + 12
        for _ in range(16):                                   # distant flat clouds
            y = rnd.uniform(HUD_H + 20, H - 40)
            x = rnd.choice([rnd.uniform(-40, left - 20), rnd.uniform(right + 20, W + 40)])
            col = lerp((255, 205, 205), (190, 140, 205), (y - HUD_H) / (H - HUD_H))
            puff_cloud(b, x, y, rnd.uniform(110, 190), col, lerp(col, (120, 80, 160), .35), ss)
        for _ in range(90):                                    # dusk stars
            x, y = rnd.uniform(0, W), rnd.uniform(H * .55, H)
            if not r.inflate(30, 30).collidepoint(x, y):
                pg.draw.circle(b, (255, 250, 240), (x * ss, y * ss), rnd.uniform(.8, 2.0) * ss)
        cols = [((235, 170, 200), (200, 130, 180)), ((250, 205, 222), (220, 160, 200)),
                ((255, 236, 242), (235, 190, 215))]
        cloud_bank(b, -50, H * .5, left * .55 + 40, H * .62, -1, random.Random(lv.width + 3), cols, ss)
        cloud_bank(b, W + 50, H * .56, (W - right) * .55 + 40, H * .56, 1, random.Random(lv.width + 4), cols, ss)
        for _ in range(9):                                     # far birds
            x = rnd.choice([rnd.uniform(20, left - 30), rnd.uniform(right + 30, W - 20)])
            P.far_bird(b, x * ss, rnd.uniform(HUD_H + 30, H * .6) * ss, rnd.uniform(8, 13) * ss, lw=2 * ss)
        if boss:                                               # holy light behind him
            P.glow(b, W / 2 * ss, (r.y - 150) * ss, 330 * ss, (255, 240, 200), 150)
        self._frame(b, ss, rnd)
        return pg.transform.smoothscale(b, (W, H))

    def _frame(self, b: pg.Surface, ss: int, rnd: random.Random) -> None:
        r, lv, cs = self.rect, self.level, self.cs
        outer = pg.Rect((r.x - 12) * ss, (r.y - 12) * ss, (r.w + 24) * ss, (r.h + 24) * ss)
        pg.draw.rect(b, P.FRAME_D, outer.move(0, 6 * ss), border_radius=20 * ss)
        pg.draw.rect(b, P.FRAME, outer, border_radius=20 * ss)
        pg.draw.rect(b, P.FRAME_L, outer, 2 * ss, border_radius=20 * ss)
        inner = pg.Rect(r.x * ss, r.y * ss, r.w * ss, r.h * ss)
        sub = b.subsurface(inner)
        P.vgrad(sub, sub.get_rect(), P.ABYSS_TOP, P.ABYSS_BOT)
        for _ in range(int(lv.width * lv.height * .9)):
            pg.draw.circle(sub, (255, 255, 255), (rnd.uniform(0, inner.w), rnd.uniform(0, inner.h)),
                           rnd.uniform(1, 2.2) * ss / 1.4)
        moving = {m.row for m in lv.moving_rows}
        for (x, y) in lv.cells():
            if (x, y) not in lv.pads and y not in moving:
                P.gap_decor(sub, (x + .5) * cs * ss, (y + .5) * cs * ss, cs * ss, rnd)
        for m in lv.moving_rows:                               # chevrons at both ends
            y = (r.y + (m.row + .5) * cs) * ss
            for x in (r.x - 6, r.right + 6):
                triangle(b, (x * ss, y), 9 * ss, 1 if m.direction > 0 else 3, (255, 240, 250))

    # ------------------------------------------------------------ tiles
    def tile_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        streak = next((m.direction for m in self.level.moving_rows if m.row == cell[1]), 0)
        return cloud_sprite(self.cs, (tile.id * 7 + 3) % 5 % 3, streak)

    def tile_image(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        if tile.unstable is not None and tile.unstable.state == WARNING:
            return melting_sprite(self.cs)
        return self.sprite(tile, cell)

    # ------------------------------------------------------------ exit
    def draw_exit(self, surf: pg.Surface, center: tuple[float, float], age: float) -> None:
        super().draw_exit(surf, center, age)
        img = rainbow_exit_sprite = P.rainbow_exit_sprite(self.cs)
        grow = min(1.0, age / 0.5)
        if grow < 1:
            k = grow * (1 + .15 * math.sin(grow * math.pi))
            img = pg.transform.smoothscale(rainbow_exit_sprite, (max(1, int(img.get_width() * k)),
                                                                 max(1, int(img.get_height() * k))))
        bob = math.sin(self.t * 2.2) * 1.5 * self.k
        surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1] + bob))))

    # ------------------------------------------------------------ events
    def on_event(self, event, view, effects, audio) -> bool:
        kind, k = event.kind, self.k
        self.event_sound(event, audio)
        if not kind.startswith("sky."):
            return False
        pos = event.pos if event.pos is not None else event.cell
        x, y = view.to_px(pos) if pos is not None else (self.rect.centerx, self.rect.centery)
        outline = (130, 40, 90)
        if kind == "sky.caw":
            effects.popup(i18n.t("sky.caw"), x + 40 * k, y - 40 * k, (255, 255, 255), 30, (200, 60, 90))
            for i in range(3):
                effects.ring(x, y - 8 * k, 20 * k, (60 + 22 * i) * k, 0.7 + .15 * i, (255, 255, 255), 3, 1.0)
        elif kind == "sky.crow_eat":
            effects.burst(x, y, (60, 60, 80), n=8, speed=140 * k, size=3.5 * k, life=0.4)
        elif kind == "sky.peck":
            effects.popup(i18n.t("sky.peck"), x, y - 34 * k, (255, 240, 240), 26, outline)
        elif kind == "sky.multiply":
            cx, cy = self.rect.centerx, self.rect.y + self.rect.h * .45
            effects.popup(i18n.t("sky.multiply"), cx, cy, (255, 245, 200), 40, outline, life=1.6)
            effects.burst(cx, cy, (255, 250, 210), n=24, speed=520 * k, size=6 * k, life=1.0, kind="star")
        elif kind == "sky.rebuild_warn":
            effects.popup(i18n.t("sky.rebuild"), self.rect.centerx, self.rect.y + 30 * k,
                          (255, 235, 250), 34, outline)
        elif kind == "sky.cloud_new":
            effects.burst(x, y, (255, 250, 246), n=10, speed=160 * k, size=5 * k, life=0.6, kind="star")
        elif kind == "sky.beam":
            effects.shake(5)
        elif kind == "sky.halo_caught":
            effects.burst(x, y, (255, 225, 110), n=12, speed=220 * k, size=5 * k, life=0.6, kind="star")
        return False

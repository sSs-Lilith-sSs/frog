"""Enemy renderers of the earth world: hedgehog, fox, mole, boar."""
from __future__ import annotations

import math

import pygame as pg

from ....art.enemy_art import EnemyArt, register_enemy_art
from .. import boar as boar_logic
from .. import hedgehog as hh
from .. import mole as ml
from . import sprites as sp

LANE_RED = (240, 70, 50)


def _blit(surf, img, x, y) -> None:
    surf.blit(img, img.get_rect(center=(round(x), round(y))))


@register_enemy_art("hedgehog")
class HedgehogArt(EnemyArt):
    def draw(self, surf, e, off) -> None:
        k = self.k
        x, y = self.px(e.pos, off)
        if e.state in (hh.CURL, hh.ROLL):
            if e.state == hh.ROLL:
                trail = sp.oriented(sp.roll_trail(round(k * 1.1, 3)), e.roll_dir)
                w = trail.get_width() if e.roll_dir[1] == 0 else trail.get_height()
                shift = w * .22
                _blit(surf, trail, x - e.roll_dir[0] * shift, y - e.roll_dir[1] * shift)
                frame = int(e.spin * 2) % sp.SPIN_FRAMES
            else:
                frame = 0
                x += math.sin(self.view.t * 60) * 1.5 * k
            _blit(surf, sp.shadow(int(40 * k), int(30 * k), 80), x + 3 * k, y + 5 * k)
            img = sp.ball(round(k * 1.1, 3), frame)
            if e.roll_dir[0] < 0:
                img = pg.transform.flip(img, True, False)
            _blit(surf, img, x, y)
            return
        step = int(e.anim * 5) % 2 if e.next_cell is not None else 0
        _blit(surf, sp.shadow(int(54 * k), int(44 * k), 70), x + 2 * k, y + 6 * k)
        img = sp.oriented(sp.hedgehog(round(k * 1.1, 3), step), e.facing)
        _blit(surf, img, x, y)
        if e.state == hh.REST:
            _blit(surf, sp.stars(round(k * .55, 3), int(self.view.t * 10) % 16), x, y - 20 * k)


@register_enemy_art("fox")
class FoxArt(EnemyArt):
    def draw(self, surf, e, off) -> None:
        k = self.k
        x, y = self.px(e.pos, off)
        if e.jumping:
            p = e.jump_progress
            lift = math.sin(p * math.pi) * 22 * k
            _blit(surf, sp.shadow(int(62 * k), int(22 * k), 55), x, y + 6 * k)
            img = sp.oriented(sp.fox(round(k * 1.2, 3), "jump", 1.0), e.facing)
            _blit(surf, img, x, y - lift)
            return
        bob = abs(math.sin(e.anim * 14)) * 2 * k if e.next_cell is not None else 0
        _blit(surf, sp.shadow(int(70 * k), int(26 * k), 70), x, y + 5 * k)
        img = sp.oriented(sp.fox(round(k * 1.2, 3), "run", 1.0), e.facing)
        fx = -6 * k * e.facing[0]
        fy = -6 * k * e.facing[1]
        _blit(surf, img, x + fx, y + fy - bob)
        if e.recover > 0:
            _blit(surf, sp.stars(round(k * .6, 3), int(self.view.t * 12) % 16), x, y - 18 * k)


@register_enemy_art("mole")
class MoleArt(EnemyArt):
    def draw(self, surf, e, off) -> None:
        k = self.k
        x, y = self.px(e.pos, off)
        if e.state == ml.TREMOR:
            return                                        # the tremor telegraph shows it
        if e.state == ml.OUT:
            grow = min(1.0, (1.3 - max(0.0, e.timer)) / 0.2 + 0.3)
            img = sp.mole(round(k * 1.05, 3))
            if grow < 1:
                img = pg.transform.smoothscale(img, (max(1, int(img.get_width() * grow)),
                                                     max(1, int(img.get_height() * grow))))
            _blit(surf, img, x, y)
            return
        img = sp.oriented(sp.mound(round(k * 1.2, 3), 3), e.facing)
        wob = math.sin(e.anim * 9) * 1.2 * k
        _blit(surf, img, x - 36 * k * e.facing[0] + wob, y - 36 * k * e.facing[1])

    def draw_telegraph(self, surf, e, tg, off) -> bool:
        if tg.style != "shake" or not tg.cells:
            return False
        k = self.k
        x, y = self.px(tg.cells[0], off)
        amp = (1 + 3 * tg.progress) * k
        img = sp.tremor(round(k, 3), self.cs)
        _blit(surf, img, x + math.sin(self.view.t * 50) * amp, y + math.cos(self.view.t * 43) * amp * .6)
        return True


@register_enemy_art("boar")
class BoarArt(EnemyArt):
    def __init__(self, view):
        super().__init__(view)
        self._lanes: dict[tuple, tuple[pg.Surface, pg.Rect]] = {}

    def draw(self, surf, e, off) -> None:
        k = self.k
        x, y = self.px(e.center(), off)
        mode = "stunned" if (e.stunned > 0 or e.defeated) else \
            "charge" if e.state in (boar_logic.TELL, boar_logic.CHARGE) else "idle"
        if e.state == boar_logic.STOMP:
            x += math.sin(self.view.t * 70) * 3 * k
            y -= abs(math.sin(self.view.t * 9)) * 6 * k
        if e.state == boar_logic.CHARGE:
            d = e.dir
            for i in range(3):
                a = (self.view.t * 3 + i / 3) % 1
                r = (10 + 12 * a) * k
                px = x - d[0] * (70 + 40 * a) * k + d[1] * (i - 1) * 30 * k
                py = y - d[1] * (60 + 40 * a) * k + d[0] * (i - 1) * 30 * k
                dust_img = sp.shadow(int(r * 2), int(r * 1.6), int(110 * (1 - a)))
                _blit(surf, dust_img, px, py)
        _blit(surf, sp.shadow(int(146 * k), int(124 * k), 85), x + 6 * k, y + 10 * k)
        img = sp.oriented(sp.boar(round(k * 1.1, 3), mode), e.dir)
        if e.hit_flash > 0 and int(e.hit_flash * 20) % 2 == 0:
            img = img.copy()
            img.fill((110, 60, 50), special_flags=pg.BLEND_RGB_ADD)
        if e.defeated:
            img = img.copy()
            img.set_alpha(200)
        _blit(surf, img, x, y)
        if e.stunned > 0 and not e.defeated:
            _blit(surf, sp.stars(round(k * 1.1, 3), int(self.view.t * 12) % 16), x + e.dir[0] * 40 * k,
                  y + e.dir[1] * 40 * k - 10 * k)
        if not e.defeated:                                  # hp hearts above the boar
            size = int(24 * k)
            for i in range(e.max_hp if e.hp <= e.max_hp else e.hp):
                _blit(surf, sp.hp_heart(size, i < e.hp), x + (i - 1) * 25 * k, y - self.cs - 16 * k)
        if e.vulnerable:
            pulse = 0.5 + 0.5 * math.sin(self.view.t * 10)
            r = pg.Rect(0, 0, self.cs * 2 + 8, self.cs * 2 + 8)
            r.center = (round(x), round(y))
            pg.draw.rect(surf, (255, 225, 90), r, max(2, int((2 + 2 * pulse) * k)), border_radius=int(self.cs * .4))

    def draw_telegraph(self, surf, e, tg, off) -> bool:
        if tg.style == "shake":
            return True                      # drawn as the boar bouncing
        if tg.style != "zone" or not tg.cells:
            return False
        key = (tg.cells, tg.direction)
        if key not in self._lanes:
            if len(self._lanes) > 12:
                self._lanes.clear()
            self._lanes[key] = self._lane(tg.cells, tg.direction)
        img, rect = self._lanes[key]
        blink = 0.55 + 0.45 * math.sin(self.view.t * (8 + 14 * tg.progress))
        img.set_alpha(int(150 + 105 * blink))
        surf.blit(img, rect.move(off))
        return True

    def _lane(self, cells, direction) -> tuple[pg.Surface, pg.Rect]:
        """Red lane with a dashed border and chevrons pointing along the charge."""
        cs, k, q = self.cs, self.k, 3
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        f = self.view.field
        rect = pg.Rect(f.x + min(xs) * cs + 4, f.y + min(ys) * cs + 4,
                       (max(xs) - min(xs) + 1) * cs - 8, (max(ys) - min(ys) + 1) * cs - 8)
        big = pg.Surface((rect.w * q, rect.h * q), pg.SRCALPHA)
        L = big.get_rect()
        pg.draw.rect(big, (*LANE_RED, 62), L, border_radius=int(cs * .3 * q))
        horiz = direction in (1, 3)
        step = int(14 * q * k) or q
        length = L.w if horiz else L.h
        for a in range(int(20 * q * k), length - int(20 * q * k), step * 2):
            if horiz:
                segs = (((a, 2 * q), (a + step, 2 * q)), ((a, L.h - 2 * q), (a + step, L.h - 2 * q)))
            else:
                segs = (((2 * q, a), (2 * q, a + step)), ((L.w - 2 * q, a), (L.w - 2 * q, a + step)))
            for p0, p1 in segs:
                pg.draw.line(big, (255, 120, 70, 230), p0, p1, max(1, int(4 * q * k)))
        n = (len(set(xs)) if horiz else len(set(ys)))
        sz = cs * .32 * q
        sign = 1 if direction in (1, 2) else -1
        for i in range(n):                     # chevrons fade away from the boar
            along = (i + .5) * cs * q if sign > 0 else length - (i + .5) * cs * q
            al = max(40, int(255 - i * 14))
            for o in (0, sz * .55):
                pts = [(-sz * .5 - o, 0), (sz * .2 - o, -sz), (sz * .5 - o, -sz),
                       (-sz * .2 - o, 0), (sz * .5 - o, sz), (sz * .2 - o, sz)]
                pts = [(-px, py) for px, py in pts] if sign > 0 else pts   # base shape points left
                if horiz:
                    pts2 = [(along + px, L.h / 2 + py) for px, py in pts]
                else:
                    pts2 = [(L.w / 2 + py, along + px) for px, py in pts]
                pg.draw.polygon(big, (150, 40, 30, al // 2), [(a + 2 * q, b + 3 * q) for a, b in pts2])
                pg.draw.polygon(big, (255, 248, 230, al), pts2)
        return pg.transform.smoothscale(big, rect.size), rect

"""Renders a running :class:`~jebik.game.world.World` (field, actors).

World-specific drawing is delegated to the world's art package
(:func:`~jebik.art.world_art.art_for`): its :class:`FieldRenderer` draws the
backdrop, tiles and exit; registered :class:`EnemyArt` classes draw enemies.
Draw order: static -> "under" enemies -> rings -> tiles -> grid ->
telegraphs -> exit -> "ground" enemies -> resting flies -> frog -> flying
flies -> "air" enemies -> particles.
"""
from __future__ import annotations

import math

import pygame as pg

from ..art.chars import fly_sprite, frog_shadow, frog_sprite, small_shadow
from ..art.common import disc_sprite
from ..art.enemy_art import EnemyArt, enemy_art_class
from ..art.glow import additive_glow
from ..art.world_art import art_for
from ..game import frog as fs
from ..game.enemy import AIR, GROUND, UNDER
from ..game.flies import RESTING
from ..game.grid import DIRS, Level
from ..game.world import World
from .layout import cell_size, field_rect
from .telegraphs import draw_telegraph

__all__ = ["GameView", "cell_size", "field_rect"]


class GameView:
    def __init__(self, level: Level):
        self.level = level
        self.cs = cell_size(level)
        self.k = self.cs / 64
        self.field = field_rect(level, self.cs)
        self.art = art_for(level.world)
        self.field_art = self.art.field(level, self.cs, self.field)
        self.static = self.field_art.static()
        self.enemy_art: dict[str, EnemyArt] = {}
        self.firefly_glow = additive_glow(30 * self.k, (170, 150, 40))
        self.exit_t: float | None = None
        self.land_t = 1.0
        self.land_strength = 1.0
        self.t = 0.0
        self.grid = self._grid_surface()

    # ------------------------------------------------------------ helpers
    def to_px(self, pos: tuple[float, float]) -> tuple[float, float]:
        return (self.field.x + pos[0] * self.cs + self.cs / 2,
                self.field.y + pos[1] * self.cs + self.cs / 2)

    def _grid_surface(self) -> pg.Surface:
        g = pg.Surface(self.field.size, pg.SRCALPHA)
        col = self.field_art.grid_color
        for x in range(1, self.level.width):
            pg.draw.line(g, col, (x * self.cs, 0), (x * self.cs, self.field.h), 1)
        for y in range(1, self.level.height):
            pg.draw.line(g, col, (0, y * self.cs), (self.field.w, y * self.cs), 1)
        return g

    def art_of(self, kind: str) -> EnemyArt:
        art = self.enemy_art.get(kind)
        if art is None:
            art = self.enemy_art[kind] = enemy_art_class(kind)(self)
        return art

    def dip(self, cell: tuple[int, int], strength: float = 1.0) -> None:
        self.field_art.dip(cell, strength)
        self.land_t = 0.0
        self.land_strength = strength

    def show_exit(self) -> None:
        self.exit_t = 0.0

    # ------------------------------------------------------------ update
    def update(self, dt: float, effects, world: World | None = None) -> None:
        self.t += dt
        self.land_t += dt
        if self.exit_t is not None:
            self.exit_t += dt
        self.field_art.tick(dt)
        if world is not None:
            self.field_art.update(dt, world, effects, self)
        for art in self.enemy_art.values():
            art.update(dt)

    # ------------------------------------------------------------ draw
    def draw(self, surf: pg.Surface, world: World, effects, show_grid: bool) -> None:
        off = effects.shake_offset()
        ox, oy = off
        if ox or oy:
            surf.fill(self.field_art.fill)
        surf.blit(self.static, off)
        self._draw_enemies(surf, world, UNDER, off)
        effects.draw_rings(surf, off)
        exit_cell = world.exit_cell if self.exit_t is not None else None
        self.field_art.draw_tiles(surf, world, off, skip=exit_cell)
        if show_grid:
            surf.blit(self.grid, (self.field.x + ox, self.field.y + oy))
        for enemy in world.enemies:
            tgs = enemy.telegraphs()
            if tgs:
                art = self.art_of(enemy.kind)
                for tg in tgs:
                    if not art.draw_telegraph(surf, enemy, tg, off):
                        draw_telegraph(surf, self, tg, off)
        if exit_cell is not None:
            x, y = self.to_px(exit_cell)
            self.field_art.draw_exit(surf, (x + ox, y + oy), self.exit_t or 0.0)
        self._draw_enemies(surf, world, GROUND, off)
        frog = world.frog
        high = frog.state == fs.SUPER
        caught_id = frog.tongue.fly_id if frog.tongue else None
        for fly in world.flies.flies:
            if fly.state == RESTING and fly.id != caught_id:
                self._draw_fly(surf, fly, off, False, world)
        if not high:
            self._draw_frog(surf, world, off)
        for fly in world.flies.flies:
            if fly.state != RESTING or fly.id == caught_id:
                self._draw_fly(surf, fly, off, fly.id == caught_id, world)
        if high:
            self._draw_frog(surf, world, off)
        self._draw_enemies(surf, world, AIR, off)
        effects.draw_particles(surf, off)

    def _draw_enemies(self, surf: pg.Surface, world: World, layer: str, off) -> None:
        for enemy in world.enemies:
            if enemy.layer == layer and enemy.alive:
                self.art_of(enemy.kind).draw(surf, enemy, off)

    def _draw_fly(self, surf: pg.Surface, fly, off, caught: bool, world: World) -> None:
        k = self.k
        x, y = self.to_px(fly.pos)
        if fly.state == RESTING and not caught:        # riding a moving row
            x += world.tiles.row_offset(fly.cell[1]) * self.cs
        x, y = x + off[0], y + off[1]
        scale = 1.15 if fly.kind == "dragon" else 1.0
        if caught:
            lift, bob, wing = 0.0, 0.0, int(self.t * 30) % 2 == 1
        elif fly.state == RESTING:
            lift, bob = 2 * k, 0.0
            wing = math.sin(self.t * 3 + fly.phase) > 0.93 and int(self.t * 30) % 2 == 1
        else:
            lift = 13 * k
            bob = math.sin(self.t * 6 + fly.phase) * 3 * k
            wing = int(self.t * 26 + fly.phase * 3) % 2 == 1
        if not caught:
            sw = int((16 if fly.state == RESTING else 13) * k * scale)
            sh = small_shadow(max(4, sw), max(3, int(sw * .5)), 70 if fly.state == RESTING else 45)
            surf.blit(sh, sh.get_rect(center=(round(x), round(y + 6 * k))))
        py = y - lift + bob
        if fly.kind == "firefly":
            lv = 0.65 + 0.35 * math.sin(self.t * 5 + fly.phase)
            glow = self.firefly_glow[max(0, int(lv * len(self.firefly_glow)) - 1)]
            surf.blit(glow, glow.get_rect(center=(round(x), round(py + 3 * k))),
                      special_flags=pg.BLEND_RGB_ADD)
        img = fly_sprite(round(k * scale, 3), fly.kind, wing)
        if fly.kind == "dragon":
            ang = -math.degrees(fly.heading) - 90
            img = pg.transform.rotozoom(img, ang, 1.0)
        surf.blit(img, img.get_rect(center=(round(x), round(py))))

    def _frog_mode(self, frog) -> str:
        if frog.state == fs.DEAD:
            return "sad"
        if frog.state == fs.WON:
            return "happy"
        if frog.state in (fs.HOP, fs.SUPER) and 0.08 < frog.hop_t < 0.92:
            return "jump"
        if frog.state == fs.HIT:
            return "blink"
        if frog.state == fs.IDLE and frog.idle_time > 1.0 and (frog.idle_time % 3.7) < 0.13:
            return "blink"
        return "idle"

    def _draw_frog(self, surf: pg.Surface, world: World, off) -> None:
        frog = world.frog
        if frog.state == fs.SPLASH:
            return
        k = self.k
        x, y = self.to_px(frog.pos())
        carry = world.tiles.row_offset(frog.cell[1]) * self.cs if frog.grounded else 0.0
        x, y = x + off[0] + carry, y + off[1]
        h = frog.height()
        lift = h * (0.3 if frog.state == fs.HOP else 0.85) * self.cs
        sh = frog_shadow(k)
        ss = 1 - 0.35 * h
        if ss < 0.999:
            sh = pg.transform.smoothscale(sh, (int(sh.get_width() * ss), int(sh.get_height() * ss)))
        surf.blit(sh, sh.get_rect(center=(round(x), round(y + 5 * k))))
        # squash & stretch
        along, perp = 1.0, 1.0
        if frog.state in (fs.HOP, fs.SUPER):
            along, perp = 1 + 0.16 * h, 1 - 0.08 * h
        elif self.land_t < 0.16:
            q = math.sin(self.land_t / 0.16 * math.pi) * 0.14 * self.land_strength
            along, perp = 1 - q, 1 + q * 0.8
        elif frog.state == fs.TONGUE:
            along, perp = 1.06, 0.97
        elif frog.state == fs.WON:
            b = abs(math.sin(self.t * 7))
            along, perp = 1 + 0.08 * b, 1 - 0.04 * b
            lift = b * 0.18 * self.cs
        else:
            along = perp = 1 + 0.015 * math.sin(self.t * 2.6)
        img = frog_sprite(round(k, 3), frog.facing, self._frog_mode(frog))
        vertical = frog.facing in (0, 2)
        sx, sy = (perp, along) if vertical else (along, perp)
        if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
            img = pg.transform.smoothscale(img, (int(img.get_width() * sx), int(img.get_height() * sy)))
        if frog.state == fs.HIT or (frog.state == fs.DEAD and world.hearts == 0):
            img = img.copy()
            img.fill((70, 0, 0), special_flags=pg.BLEND_RGB_ADD)
        if frog.invuln > 0 and frog.state != fs.DEAD and int(frog.invuln * 9) % 2 == 0:
            img = img.copy()
            img.set_alpha(80)
        if frog.tongue is not None:
            self._draw_tongue(surf, frog, (off[0] + carry, off[1]))
        surf.blit(img, img.get_rect(center=(round(x), round(y - lift))))

    def _draw_tongue(self, surf: pg.Surface, frog, off) -> None:
        t = frog.tongue
        if t.length <= 0.05:
            return
        k = self.k
        dx, dy = DIRS[t.direction]
        ox, oy = self.to_px(frog.pos())
        ox, oy = ox + off[0] + dx * 12 * k, oy + off[1] + dy * 12 * k
        tx, ty = self.to_px(t.tip(frog.pos()))
        tx, ty = tx + off[0], ty + off[1]
        w = max(4, int(7 * k))
        rect = pg.Rect(min(ox, tx), min(oy, ty), abs(tx - ox), abs(ty - oy)).inflate(
            w if dx == 0 else 0, w if dy == 0 else 0)
        pg.draw.rect(surf, (185, 50, 80), rect.move(0, 2), border_radius=w // 2)
        pg.draw.rect(surf, (225, 75, 100), rect, border_radius=w // 2)
        tip = disc_sprite(round(6.5 * k * 2) / 2, (235, 95, 120))
        surf.blit(tip, tip.get_rect(center=(round(tx), round(ty))))

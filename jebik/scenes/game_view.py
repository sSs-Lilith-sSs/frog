"""Renders a running :class:`~jebik.game.world.World` (field, actors)."""
from __future__ import annotations

import math
import random

import pygame as pg

from .. import config
from ..art import backdrops, water
from ..art.chars import fly_sprite, frog_shadow, frog_sprite, small_shadow
from ..art.common import disc_sprite
from ..art.snake_art import SnakeArt
from ..game import frog as fs
from ..game.flies import RESTING
from ..game.grid import DIRS, Level
from ..game.world import World

W, H = config.SCREEN_W, config.SCREEN_H
_CACHE: dict[tuple[str, int], tuple[pg.Surface, list]] = {}


def cell_size(level: Level) -> int:
    fit_w = (W - 2 * config.FIELD_MARGIN_X) // level.width
    fit_h = (H - config.HUD_H - 2 * config.FIELD_MARGIN_Y) // level.height
    cs = min(config.MAX_CELL, fit_w, fit_h)
    return max(40, cs - cs % 2)


def field_rect(level: Level, cs: int) -> pg.Rect:
    fw, fh = level.width * cs, level.height * cs
    return pg.Rect((W - fw) // 2, config.HUD_H + (H - config.HUD_H - fh) // 2, fw, fh)


def build_static(level: Level) -> tuple[pg.Surface, list]:
    """Backdrop + field water (rendered once per level and cached)."""
    cs = cell_size(level)
    key = (level.id + str(hash(level.pads)), cs)
    if key not in _CACHE:
        rect = field_rect(level, cs)
        holes = set(level.holes)
        static = backdrops.pond_backdrop(rect, seed=21 + level.seed)
        static.blit(water.water_background(level.width, level.height, cs, holes, seed=level.seed + 4),
                    rect.topleft)
        k = cs / 64
        pads = [(spec, water.pad_frames(spec, k))
                for spec in water.pad_layout(level.width, level.height, cs, holes, seed=level.seed + 4)]
        _CACHE[key] = (static, pads)
    return _CACHE[key]


class GameView:
    def __init__(self, level: Level):
        self.level = level
        self.cs = cell_size(level)
        self.k = self.cs / 64
        self.field = field_rect(level, self.cs)
        self.static, self.pads = build_static(level)
        self.pad_index = {spec.cell: i for i, (spec, _) in enumerate(self.pads)}
        self.dips: dict[tuple[int, int], float] = {}
        self.snake_art = SnakeArt(self.cs)
        self.exit_img = water.exit_sprite(self.k)
        self.exit_glow = water.glow_sprite(64 * self.k, max_alpha=170)
        self.firefly_glow = water.glow_sprite(26 * self.k, (255, 240, 120), max_alpha=150)
        self.exit_t: float | None = None
        self.land_t = 1.0
        self.land_strength = 1.0
        self.t = 0.0
        self.grid = self._grid_surface()
        self.rng = random.Random()
        self.ambient_t = 0.5

    # ------------------------------------------------------------ helpers
    def to_px(self, pos: tuple[float, float]) -> tuple[float, float]:
        return (self.field.x + pos[0] * self.cs + self.cs / 2,
                self.field.y + pos[1] * self.cs + self.cs / 2)

    def _grid_surface(self) -> pg.Surface:
        g = pg.Surface(self.field.size, pg.SRCALPHA)
        for x in range(1, self.level.width):
            pg.draw.line(g, (255, 255, 255, 55), (x * self.cs, 0), (x * self.cs, self.field.h), 1)
        for y in range(1, self.level.height):
            pg.draw.line(g, (255, 255, 255, 55), (0, y * self.cs), (self.field.w, y * self.cs), 1)
        return g

    def dip(self, cell: tuple[int, int], strength: float = 1.0) -> None:
        self.dips[cell] = 0.0
        self.land_t = 0.0
        self.land_strength = strength

    def show_exit(self) -> None:
        self.exit_t = 0.0

    # ------------------------------------------------------------ update
    def update(self, dt: float, effects) -> None:
        self.t += dt
        self.land_t += dt
        if self.exit_t is not None:
            self.exit_t += dt
        for c in list(self.dips):
            self.dips[c] += dt
            if self.dips[c] > 0.5:
                del self.dips[c]
        self.ambient_t -= dt
        if self.ambient_t <= 0:        # lazy ripples on open water
            self.ambient_t = self.rng.uniform(0.35, 0.9)
            holes = sorted(self.level.holes)
            if holes and self.rng.random() < 0.75:
                cx, cy = self.rng.choice(holes)
                pos = (cx + self.rng.uniform(-.25, .25), cy + self.rng.uniform(-.25, .25))
            else:
                pos = (self.rng.uniform(-.5, self.level.width - .5), self.rng.uniform(-.5, self.level.height - .5))
            x, y = self.to_px(pos)
            effects.ring(x, y, 3 * self.k, 20 * self.k, 1.6, (185, 230, 240), 2, 0.45)

    # ------------------------------------------------------------ draw
    def draw(self, surf: pg.Surface, world: World, effects, show_grid: bool) -> None:
        ox, oy = effects.shake_offset()
        if ox or oy:
            surf.fill(config.C_POND_BOTTOM)
        surf.blit(self.static, (ox, oy))
        fx, fy = self.field.x + ox, self.field.y + oy
        effects.draw_rings(surf, (ox, oy))
        exit_cell = world.exit_cell if self.exit_t is not None else None
        for spec, frames in self.pads:
            if spec.cell == exit_cell:
                continue
            ph = math.sin(self.t * 0.9 + spec.phase)
            img = frames[min(len(frames) - 1, int((ph + 1) / 2 * len(frames)))]
            if spec.cell in self.dips:
                d = self.dips[spec.cell]
                sc = 1 - 0.09 * math.sin(min(1.0, d / 0.5) * math.pi) * (1 - d / 0.5 * 0.5)
                img = pg.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
            surf.blit(img, img.get_rect(center=(round(fx + spec.cx), round(fy + spec.cy))))
        if show_grid:
            surf.blit(self.grid, (fx, fy))
        if exit_cell is not None:
            self._draw_exit(surf, exit_cell, (ox, oy))
        for enemy in world.enemies:
            pts = [self.to_px(p) for p in enemy.segment_positions()]
            pts = [(x + ox, y + oy) for x, y in pts]
            self.snake_art.draw(surf, pts, enemy.head_dir(), enemy.anim)
        frog = world.frog
        high = frog.state == fs.SUPER
        caught_id = frog.tongue.fly_id if frog.tongue else None
        for fly in world.flies.flies:
            if fly.state == RESTING and fly.id != caught_id:
                self._draw_fly(surf, fly, (ox, oy), False)
        if not high:
            self._draw_frog(surf, world, (ox, oy))
        for fly in world.flies.flies:
            if fly.state != RESTING or fly.id == caught_id:
                self._draw_fly(surf, fly, (ox, oy), fly.id == caught_id)
        if high:
            self._draw_frog(surf, world, (ox, oy))
        effects.draw_particles(surf, (ox, oy))

    def _draw_exit(self, surf: pg.Surface, cell, off) -> None:
        cx, cy = self.to_px(cell)
        cx, cy = cx + off[0], cy + off[1]
        t = self.exit_t or 0.0
        pulse = 0.85 + 0.15 * math.sin(self.t * 3)
        glow = self.exit_glow.copy()
        glow.set_alpha(int(255 * pulse * min(1.0, t / 0.4)))
        surf.blit(glow, glow.get_rect(center=(round(cx), round(cy))))
        if t < 0.5:
            u = t / 0.5
            sc = max(0.05, 1 + math.sin(u * math.pi * 1.4) * (1 - u) * 0.5 - (1 - u) * 0.6)
            img = pg.transform.rotozoom(self.exit_img, (1 - u) * 40, sc)
        else:
            img = self.exit_img
        surf.blit(img, img.get_rect(center=(round(cx), round(cy))))

    def _draw_fly(self, surf: pg.Surface, fly, off, caught: bool) -> None:
        k = self.k
        x, y = self.to_px(fly.pos)
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
            glow = self.firefly_glow.copy()
            glow.set_alpha(int(180 + 75 * math.sin(self.t * 5 + fly.phase)))
            surf.blit(glow, glow.get_rect(center=(round(x), round(py + 3 * k))))
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
        x, y = x + off[0], y + off[1]
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
            self._draw_tongue(surf, frog, off)
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

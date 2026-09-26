"""Water field: numpy pools + bobbing lily pads (style B) + lotus exit."""
from __future__ import annotations

import math
import random

import pygame as pg

from ....art.field import FieldRenderer
from ....game import events as ev
from ....game.tiles import Tile
from . import backdrop
from .pads import PadSpec, exit_sprite, pad_frames, pad_layout, water_background


class WaterField(FieldRenderer):
    fill = backdrop.POND_BOTTOM
    # sounds from tools/gen_audio_water.py; volumes balance the files' loudness
    event_sounds = {
        "water.pike_bubbles": ("water.pike_bubbles", .85),
        "water.pike_lunge": ("water.pike_lunge", 1.4),
        "water.heron_shadow": ("water.heron_whoosh", .95),
        "water.heron_strike": ("water.heron_strike", 1.3),
        "water.whale_surface": ("water.whale_surface", 1.0),
        "water.jet": ("water.jet", 1.3),
        "water.wave": ("water.wave", 1.2),
        "water.gulp": ("water.gulp", .85),
        ev.TILE_WARN: ("water.sink", .95, .3),
    }
    tell_sounds = {"surface": ("water.whale_song", .9)}

    def __init__(self, level, cs, rect):
        super().__init__(level, cs, rect)
        cache = self.level_cache()
        if "specs" not in cache:
            specs = pad_layout(level.width, level.height, cs, set(level.holes) | set(level.obstacles),
                               seed=level.seed + 4)
            cache["specs"] = {s.cell[1] * level.width + s.cell[0]: s for s in specs}
            cache["frames"] = {}
        self.specs: dict[int, PadSpec] = cache["specs"]
        self.frames: dict[int, list[pg.Surface]] = cache["frames"]
        self.exit_img = exit_sprite(self.k * 1.3)
        self.rng = random.Random()
        self.ambient_t = 0.5

    # ------------------------------------------------------------ static
    def build_static(self) -> pg.Surface:
        lv = self.level
        static = backdrop.pond_backdrop(self.rect, seed=21 + lv.seed)
        static.blit(water_background(lv.width, lv.height, self.cs, set(lv.holes), seed=lv.seed + 4),
                    self.rect.topleft)
        return static

    # ------------------------------------------------------------ tiles
    def _spec(self, tile: Tile, cell: tuple[int, int]) -> PadSpec:
        spec = self.specs.get(tile.id)
        if spec is None:            # a tile that had no pad at start (e.g. rebuilt)
            spec = PadSpec(cell, cell[0] * self.cs + self.cs / 2, cell[1] * self.cs + self.cs / 2,
                           self.cs * 0.4, tile.id * 0.7, False, tile.id * 1.3)
            self.specs[tile.id] = spec
        return spec

    def _frames(self, tile: Tile, cell: tuple[int, int]) -> list[pg.Surface]:
        frames = self.frames.get(tile.id)
        if frames is None:
            frames = self.frames[tile.id] = pad_frames(self._spec(tile, cell), self.k)
        return frames

    def tile_sprite(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        frames = self._frames(tile, cell)
        return frames[len(frames) // 2]

    def tile_image(self, tile: Tile, cell: tuple[int, int]) -> pg.Surface:
        frames = self._frames(tile, cell)
        ph = math.sin(self.t * 0.9 + self._spec(tile, cell).phase)
        return frames[min(len(frames) - 1, int((ph + 1) / 2 * len(frames)))]

    def tile_center(self, tile: Tile, cell: tuple[int, int]) -> tuple[float, float]:
        spec = self._spec(tile, cell)
        return (spec.cx + (cell[0] - spec.cell[0]) * self.cs,
                spec.cy + (cell[1] - spec.cell[1]) * self.cs)

    # ------------------------------------------------------------ exit
    def draw_exit(self, surf: pg.Surface, center: tuple[float, float], age: float) -> None:
        super().draw_exit(surf, center, age)          # glow + sparkles
        if age < 0.5:
            u = age / 0.5
            sc = max(0.05, 1 + math.sin(u * math.pi * 1.4) * (1 - u) * 0.5 - (1 - u) * 0.6)
            img = pg.transform.rotozoom(self.exit_img, (1 - u) * 40, sc)
        else:
            img = self.exit_img
        surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))

    # ------------------------------------------------------------ ambience
    def update(self, dt: float, world, effects, view) -> None:
        self.ambient_t -= dt
        if self.ambient_t > 0:
            return
        self.ambient_t = self.rng.uniform(0.35, 0.9)       # lazy ripples on open water
        holes = sorted(self.level.holes)
        if holes and self.rng.random() < 0.75:
            cx, cy = self.rng.choice(holes)
            pos = (cx + self.rng.uniform(-.25, .25), cy + self.rng.uniform(-.25, .25))
        else:
            pos = (self.rng.uniform(-.5, self.level.width - .5), self.rng.uniform(-.5, self.level.height - .5))
        x, y = view.to_px(pos)
        effects.ring(x, y, 3 * self.k, 20 * self.k, 1.6, (185, 230, 240), 2, 0.45)

    def on_event(self, event: ev.Event, view, effects, audio) -> bool:
        self.event_sound(event, audio)
        if event.kind == "water.pike_lunge" and event.cell is not None:   # out of the water
            x, y = view.to_px(event.cell)
            effects.burst(x, y, (225, 245, 255), n=10, speed=200 * self.k, size=4 * self.k, life=0.5,
                          gravity=700 * self.k, up=180 * self.k)
            return True
        if event.kind == "water.whale_surface":           # the whale breaks the surface
            x, y = view.to_px(event.cell)
            for i in range(3):
                effects.ring(x, y, 20 * self.k, (70 + i * 30) * self.k, 0.7 + i * .2, (225, 248, 255), 3)
            effects.burst(x, y, (225, 245, 255), n=18, speed=240 * self.k, size=4 * self.k, life=0.7)
            effects.shake(6)
            return True
        if event.kind == "water.jet":
            for c in (event.value or [])[::2]:
                x, y = view.to_px(c)
                effects.burst(x, y, (235, 250, 255), n=3, speed=90 * self.k, size=3 * self.k, life=0.4)
            return True
        if event.kind in (ev.TILE_GONE, ev.HOLE_OPEN):     # the pad sinks
            x, y = view.to_px(event.cell)
            for i in range(2):
                effects.ring(x, y, 8 * self.k, (34 + i * 18) * self.k, 0.8 + i * .2, (215, 245, 255), 2)
            return True
        if event.kind == ev.TILE_WARN:                    # bubbles around the pad
            x, y = view.to_px(event.cell)
            effects.burst(x, y, (225, 245, 255), n=6, speed=60 * self.k, size=3 * self.k, life=0.6)
            return True
        return False

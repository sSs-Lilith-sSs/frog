"""Studio splash «21th MANGO CAT» (a loving parody of the 20th Century Fox logo).

Timeline (~6.8 s, ``config.STUDIO_*``): fade in from black, searchlights
sweep behind the golden monument while the camera slowly pushes in
(parallax: sky still, city a little, monument most), fade to black, then the
profile screen. Any key / click / tap skips. Plays ``intro_custom.ogg|wav``
if the user dropped one into the audio folder, else the generated fanfare.

The browser build draws it at half resolution (``splash_layers.WEB_SCALE``,
pre-baked layers) and upscales each frame: full-screen additive / alpha blits
are far slower in WebAssembly.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from .. import config, paths
from ..art import splash_art as art
from ..art.splash_layers import WEB_SCALE, layers
from .base import Scene

W, H = config.SCREEN_W, config.SCREEN_H
# searchlights: (x, base angle, sweep amplitude, speed, phase) — angles in degrees, 0 = up
BEAMS = ((0.17, -24, 20, 0.55, 0.0), (0.33, -8, 24, 0.7, 1.9), (0.5, 4, 18, 0.45, 3.6),
         (0.67, 10, 24, 0.66, 0.8), (0.83, 26, 20, 0.52, 2.7))
BEAM_Y = art.HORIZON + 40
SKIP_EVENTS = (pg.KEYDOWN, pg.MOUSEBUTTONDOWN, pg.FINGERDOWN)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class SplashScene(Scene):
    touch_native = True          # a finger tap skips directly

    def __init__(self, app, next_scene_factory=None):
        super().__init__(app)
        self.next_factory = next_scene_factory
        lay = layers(WEB_SCALE if paths.is_web() else 1.0)
        self.k = k = lay.k                  # image scale; coordinates stay full-res
        self.sky, self.beam, self.flare = lay.sky, lay.beam, lay.flare
        self.city, self.lights, self.city_box = lay.city, lay.lights, lay.city_box
        self.logo, self.logo_rect = lay.logo, lay.logo_rect
        self.floor, self.vignette, self.ground = lay.floor, lay.vignette, lay.ground
        self.size = (round(W * k), round(H * k))
        self.buf = pg.Surface(self.size) if k != 1.0 else None
        self.black = pg.Surface(self.size)
        self.done = False
        self.rng = random.Random(3)

    # ------------------------------------------------------------ flow
    def enter(self) -> None:
        self.app.audio.stop_music()
        self.app.audio.play_intro()

    def finish(self) -> None:
        if self.done:
            return
        self.done = True
        self.app.audio.stop_intro(fade_ms=400)
        self.app.audio.play_music(force=True)
        if self.next_factory is not None:
            self.app.scenes.reset(self.next_factory(), fade=True)

    def handle(self, event: pg.event.Event) -> None:
        if event.type in SKIP_EVENTS and self.time > 0.15:
            self.finish()

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.time >= config.STUDIO_TIME:
            self.finish()

    # ------------------------------------------------------------ camera
    @property
    def progress(self) -> float:
        return min(1.0, self.time / config.STUDIO_TIME)

    def zoom(self, depth: float) -> float:
        """Current zoom of a layer; depth 0 = far sky, 1 = the monument."""
        z0, z1 = config.STUDIO_ZOOM
        return 1.0 + (z0 - 1.0 + (z1 - z0) * ease(self.progress * 1.05)) * depth

    def _place(self, pos: tuple[float, float], z: float) -> tuple[float, float]:
        return (W / 2 + (pos[0] - W / 2) * z, H / 2 + (pos[1] - H / 2) * z)

    # ------------------------------------------------------------ draw
    def draw(self, surf: pg.Surface) -> None:
        if self.buf is None:
            self._draw(surf)
        else:
            self._draw(self.buf)
            pg.transform.scale(self.buf, surf.get_size(), surf)

    def _draw(self, surf: pg.Surface) -> None:
        k = self.k
        surf.blit(self.sky, (0, 0))
        self._draw_beams(surf, self.zoom(0.35))
        # city layer: rendered at CITY_ZOOM about the screen centre
        zc = self.zoom(0.6)
        f = zc / art.CITY_ZOOM
        box = self.city_box
        ox = W / 2 + (box.x - W * art.CITY_ZOOM / 2) * f
        oy = H / 2 + (box.y - H * art.CITY_ZOOM / 2) * f
        city = pg.transform.smoothscale(self.city, (round(box.w * f * k), round(box.h * f * k)))
        surf.blit(city, (round(ox * k), round(oy * k)))
        for i, (lx, ly) in enumerate(self.lights):          # blinking red spire lights
            if (self.time * 1.3 + i * 0.37) % 1.0 < 0.5:
                pg.draw.circle(surf, (255, 70, 60), (round((ox + lx * f) * k), round((oy + ly * f) * k)),
                               max(1, round(3 * k)))
        # monument layer: rect in screen coords at LOGO_ZOOM about the centre
        zl = self.zoom(1.0)
        gy = H / 2 + (self.ground - H / 2) * zl
        surf.blit(self.floor, (0, round(gy * k) - 2))
        f = zl / art.LOGO_ZOOM
        r = self.logo_rect
        logo = self.logo if abs(f - 1) < 1e-3 else pg.transform.smoothscale(
            self.logo, (round(r.w * f * k), round(r.h * f * k)))
        lx, ly = W / 2 + (r.x - W / 2) * f, H / 2 + (r.y - H / 2) * f
        surf.blit(logo, (round(lx * k), round(ly * k)))
        surf.blit(self.vignette, (0, 0))
        self._draw_fade(surf)

    def _draw_beams(self, surf: pg.Surface, z: float) -> None:
        t = self.time
        L = self.beam.get_height()
        for i, (fx, base, amp, speed, phase) in enumerate(BEAMS):
            ang = base + amp * math.sin(t * speed + phase)
            src = self._place((fx * W, BEAM_Y), z)
            src = (src[0] * self.k, src[1] * self.k)
            img = pg.transform.rotate(self.beam, -ang)
            vec = pg.math.Vector2(0, L / 2).rotate(ang)       # centre -> source, rotated
            rect = img.get_rect(center=(src[0] - vec.x, src[1] - vec.y))
            flicker = 0.85 + 0.15 * math.sin(t * 7 + i * 2)
            if flicker < 0.99:
                img.fill((int(255 * flicker),) * 3, special_flags=pg.BLEND_RGB_MULT)
            surf.blit(img, rect, special_flags=pg.BLEND_RGB_ADD)
            surf.blit(self.flare, self.flare.get_rect(center=src), special_flags=pg.BLEND_RGB_ADD)

    def _draw_fade(self, surf: pg.Surface) -> None:
        t = self.time
        a = 0.0
        if t < config.STUDIO_FADE_IN:
            a = 1 - t / config.STUDIO_FADE_IN
        elif t > config.STUDIO_TIME - config.STUDIO_FADE_OUT:
            a = (t - (config.STUDIO_TIME - config.STUDIO_FADE_OUT)) / config.STUDIO_FADE_OUT
        if a > 0:
            self.black.set_alpha(int(255 * min(1.0, a)))
            surf.blit(self.black, (0, 0))

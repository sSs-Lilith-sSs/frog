"""Application shell: display, main loop, shared services (save, audio, i18n)."""
from __future__ import annotations

import asyncio
import os
import time

import pygame as pg

from . import config, i18n, save
from .audio import Audio
from .game.rules import EZZZ
from .ui import touch, widgets


class App:
    def __init__(self, splash: bool | None = None) -> None:
        """``splash``: show the studio splash first (default: yes, unless the
        ``JEBIK_NO_SPLASH`` environment variable is set)."""
        pg.mixer.pre_init(44100, -16, 2, 512)
        pg.init()
        pg.display.set_caption("жэбик")
        self.screen = pg.display.set_mode((config.SCREEN_W, config.SCREEN_H),
                                          pg.SCALED | pg.RESIZABLE)
        self._set_icon()
        self.clock = pg.time.Clock()
        self.save = save.load()
        self.settings = self.save.settings
        i18n.set_lang(self.settings["lang"])
        self.audio = Audio(self.settings)
        widgets.set_sound_hook(self.audio.play)
        self.difficulty = EZZZ
        self.running = True
        self.touch_seen = False       # a finger event arrived (touch mode "auto")

        from .scenes.base import SceneManager
        from .scenes.common import MenuBackdrop
        from .scenes.profile import ProfileScene
        self.backdrop = MenuBackdrop()
        self.scenes = SceneManager(self)
        if splash is None:
            splash = not os.environ.get("JEBIK_NO_SPLASH")
        if self.settings.get("fullscreen"):
            self.set_fullscreen(True)
        if splash:
            from .scenes.splash import SplashScene
            self.scenes.reset(SplashScene(self, lambda: ProfileScene(self)), fade=False)
        else:
            self.scenes.reset(ProfileScene(self), fade=False)
            self.audio.play_music()

    # ------------------------------------------------------------ services
    def _set_icon(self) -> None:
        try:
            from .art.chars import frog_front_sprite
            icon = pg.Surface((64, 64), pg.SRCALPHA)
            spr = frog_front_sprite(1.0)
            icon.blit(spr, spr.get_rect(center=(32, 34)))
            pg.display.set_icon(icon)
        except pg.error:
            pass

    @property
    def profile(self):
        return self.save.profile

    def persist(self) -> None:
        self.save.save()

    def set_lang(self, code: str) -> None:
        self.settings["lang"] = code
        i18n.set_lang(code)
        self.persist()

    @property
    def touch_controls(self) -> bool:
        """Show on-screen buttons and read swipes/taps in the game."""
        mode = self.settings.get("touch", "auto")
        return mode == "on" or (mode == "auto" and self.touch_seen)

    def is_fullscreen(self) -> bool:
        try:
            return bool(pg.display.is_fullscreen())
        except (AttributeError, pg.error):
            return bool(self.screen.get_flags() & pg.FULLSCREEN)

    def set_fullscreen(self, on: bool) -> None:
        self.settings["fullscreen"] = on
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            return
        try:
            if self.is_fullscreen() != on:
                pg.display.toggle_fullscreen()
        except pg.error:
            pass

    # ------------------------------------------------------------ loop
    def frame(self, dt: float, events: list[pg.event.Event]) -> None:
        for event in events:
            if touch.is_touch_mouse(event):
                continue                  # the finger events are handled instead
            if event.type in touch.FINGER_EVENTS:
                self.touch_seen = True
                event = touch.localize(event)
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN and event.key == pg.K_F11:
                self.set_fullscreen(not self.is_fullscreen())
                self.persist()
            else:
                self.scenes.handle(event)
        self.scenes.update(dt)
        self.audio.update(dt)
        self.scenes.draw(self.screen)

    async def run(self) -> None:
        """Main loop; yields to asyncio every frame so pygbag (browser) works."""
        autoquit = float(os.environ.get("JEBIK_AUTOQUIT", "0") or 0)
        start = time.monotonic()
        while self.running:
            dt = min(self.clock.tick(config.FPS) / 1000.0, config.MAX_DT)
            self.frame(dt, pg.event.get())
            pg.display.flip()
            if autoquit and time.monotonic() - start > autoquit:
                self.running = False
            await asyncio.sleep(0)
        self.persist()
        pg.quit()

    def quit(self) -> None:
        self.running = False


async def main() -> None:
    await App().run()

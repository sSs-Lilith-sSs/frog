"""Music + sound effects. Degrades silently if no audio device is available."""
from __future__ import annotations

import pygame as pg

from . import config

# per-effect loudness trim (frequent sounds are quieter)
SFX_TRIM = {"jump": 0.35, "tongue": 0.45, "eat": 0.8, "splash": 0.8, "hit": 0.9,
            "win": 0.8, "lose": 0.8, "superjump": 0.6, "powerup": 0.7, "click": 0.5,
            "overeat": 0.9, "full": 0.7, "denied": 0.45, "tick": 0.35}


class Audio:
    def __init__(self, settings: dict):
        self.settings = settings
        self.enabled = False
        self.sounds: dict[str, pg.mixer.Sound] = {}
        self.track: str | None = None
        self.duck = 1.0            # temporary music ducking (win/lose stingers)
        self._duck_target = 1.0
        self._duck_hold = 0.0
        try:
            if not pg.mixer.get_init():
                pg.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
        except pg.error:
            self.enabled = False
            return
        for name in config.SFX_NAMES:
            path = config.AUDIO_DIR / f"sfx_{name}.wav"
            try:
                self.sounds[name] = pg.mixer.Sound(str(path))
            except (pg.error, FileNotFoundError):
                pass
        pg.mixer.set_num_channels(16)

    # ------------------------------------------------------------ music
    def play_music(self, track: str | None = None, force: bool = False) -> None:
        track = track or self.settings.get("music_track", "B")
        if not self.enabled or (track == self.track and not force and pg.mixer.music.get_busy()):
            return
        path = config.AUDIO_DIR / config.MUSIC_FILES.get(track, "music_b.wav")
        try:
            pg.mixer.music.load(str(path))
            pg.mixer.music.play(-1, fade_ms=400)
            self.track = track
            self.apply_volume()
        except (pg.error, FileNotFoundError):
            self.track = None

    def apply_volume(self) -> None:
        if self.enabled:
            pg.mixer.music.set_volume(float(self.settings.get("music_volume", .6)) * self.duck * 0.7)

    def duck_music(self, level: float = 0.25, hold: float = 2.5) -> None:
        self._duck_target = level
        self._duck_hold = hold

    def update(self, dt: float) -> None:
        if not self.enabled:
            return
        if self._duck_hold > 0:
            self._duck_hold -= dt
            target = self._duck_target
        else:
            target = 1.0
        if abs(self.duck - target) > 1e-3:
            speed = 6.0 if target < self.duck else 0.8
            self.duck += (target - self.duck) * min(1.0, dt * speed)
            self.apply_volume()

    # ------------------------------------------------------------ sfx
    def play(self, name: str, volume: float = 1.0) -> None:
        snd = self.sounds.get(name)
        if not self.enabled or snd is None:
            return
        vol = float(self.settings.get("sfx_volume", .8)) * SFX_TRIM.get(name, .7) * volume
        if vol <= 0.001:
            return
        ch = snd.play()
        if ch is not None:
            ch.set_volume(vol)

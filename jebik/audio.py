"""Music + sound effects. Degrades silently if no audio device is available.

Core effects live in ``assets/audio/sfx_<name>.wav``. World packages ship
their own in ``jebik/worlds/<id>/audio/<name>.wav`` and play them as
``audio.play("<id>.<name>")`` — loaded lazily on first use.
"""
from __future__ import annotations

import pygame as pg

from . import config, paths

# per-effect loudness trim, balanced on the files' loudness (frequent sounds are
# quieter); world sounds default to 0.7 and pass their own volume
SFX_TRIM = {"jump": 0.55, "tongue": 0.47, "eat": 1.0, "splash": 0.92, "hit": 1.0,
            "win": 1.0, "lose": 0.66, "superjump": 0.49, "powerup": 0.7, "click": 0.59,
            "overeat": 1.0, "full": 0.81, "denied": 0.71, "tick": 0.51}


class Audio:
    def __init__(self, settings: dict):
        self.settings = settings
        self.enabled = False
        self.sounds: dict[str, pg.mixer.Sound] = {}
        self.track: str | None = None
        self.duck = 1.0            # temporary music ducking (win/lose stingers)
        self._duck_target = 1.0
        self._duck_hold = 0.0
        self.intro_channel: pg.mixer.Channel | None = None
        self._missing: set[str] = set()
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

    def stop_music(self, fade_ms: int = 0) -> None:
        if self.enabled:
            if fade_ms:
                pg.mixer.music.fadeout(fade_ms)
            else:
                pg.mixer.music.stop()
        self.track = None

    # ------------------------------------------------------------ studio intro
    def intro_path(self):
        """The user's ``intro_custom.ogg|wav`` if present, else the generated fanfare.
        In the packaged game it may also sit next to ``jebik.exe``."""
        dirs = [config.AUDIO_DIR] + ([paths.app_dir()] if paths.is_frozen() else [])
        for folder in dirs:
            for name in config.INTRO_CUSTOM:
                path = folder / name
                if path.is_file():
                    return path
        path = config.AUDIO_DIR / config.INTRO_FANFARE
        return path if path.is_file() else None

    def play_intro(self) -> None:
        path = self.intro_path()
        if not self.enabled or path is None:
            return
        try:
            snd = pg.mixer.Sound(str(path))
        except (pg.error, FileNotFoundError):
            return
        self.intro_channel = snd.play()
        if self.intro_channel is not None:
            self.intro_channel.set_volume(max(float(self.settings.get("music_volume", .6)),
                                              float(self.settings.get("sfx_volume", .8))))

    def stop_intro(self, fade_ms: int = 300) -> None:
        if self.intro_channel is not None:
            self.intro_channel.fadeout(fade_ms)
            self.intro_channel = None

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
    def _world_sound(self, name: str) -> pg.mixer.Sound | None:
        """``"earth.stomp"`` -> ``jebik/worlds/earth/audio/stomp.wav`` (cached, None if missing)."""
        if name in self._missing:
            return None
        world, _, rest = name.partition(".")
        path = config.WORLDS_DIR / world / "audio" / f"{rest}.wav"
        try:
            snd = pg.mixer.Sound(str(path))
        except (pg.error, FileNotFoundError):
            self._missing.add(name)
            return None
        self.sounds[name] = snd
        return snd

    def play(self, name: str, volume: float = 1.0) -> bool:
        """Play an effect; False if it does not exist (or audio is off), so a
        caller can fall back: ``audio.play("sky.boss_hit") or audio.play("hit")``."""
        if not self.enabled:
            return False
        snd = self.sounds.get(name)
        if snd is None and "." in name:
            snd = self._world_sound(name)
        if snd is None:
            return False
        vol = float(self.settings.get("sfx_volume", .8)) * SFX_TRIM.get(name, .7) * volume
        if vol > 0.001:
            ch = snd.play()
            if ch is not None:
                ch.set_volume(min(1.0, vol))
        return True

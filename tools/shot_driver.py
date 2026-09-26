"""Headless driver for screenshots: scripted input into a real :class:`App`.

Importing this module switches SDL to the dummy drivers and points the save
directory at a throw-away folder, so import it before pygame / jebik.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["JEBIK_SAVE_DIR"] = tempfile.mkdtemp(prefix="jebik_shots_")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame as pg  # noqa: E402

from jebik.app import App  # noqa: E402

DT = 1 / 60
ARROW = {0: pg.K_UP, 1: pg.K_RIGHT, 2: pg.K_DOWN, 3: pg.K_LEFT}


class Driver:
    def __init__(self, out: Path, splash: bool = True):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.app = App(splash=splash)
        self.shots: list[str] = []

    # ------------------------------------------------------------ primitives
    def run(self, seconds: float, events=()) -> None:
        events = list(events)
        for i in range(max(1, int(round(seconds / DT)))):
            self.app.frame(DT, events if i == 0 else [])

    def key(self, key: int, mod: int = 0, hold: float = 0.0, wait: float = 0.05) -> None:
        down = pg.event.Event(pg.KEYDOWN, key=key, mod=mod, unicode="", scancode=0)
        up = pg.event.Event(pg.KEYUP, key=key, mod=mod, unicode="", scancode=0)
        self.run(max(DT, hold), [down])
        self.run(wait, [up])

    def type_text(self, text: str) -> None:
        self.run(0.05, [pg.event.Event(pg.TEXTINPUT, text=text)])

    def settle(self, seconds: float = 0.6) -> None:
        self.run(seconds)

    def shot(self, name: str) -> None:
        path = self.out / f"{name}.png"
        pg.image.save(self.app.screen, str(path))
        self.shots.append(path.name)
        print("saved", path)

    # ------------------------------------------------------------ helpers for hooks
    @property
    def top(self):
        return self.app.scenes.top

    @property
    def game(self):
        from jebik.scenes.game_scene import GameScene
        for s in reversed(self.app.scenes.stack):
            if isinstance(s, GameScene):
                return s
        return None

    def go_menu(self) -> None:
        from jebik.scenes.flow import go_menu
        go_menu(self.app)
        self.settle(0.5)

    def play(self, level_id: str, seed: int = 7, level=None, settle: float = 2.0):
        """Push a GameScene (no cutscene) from the main menu and let it start."""
        from jebik.scenes.game_scene import GameScene
        self.go_menu()
        self.app.scenes.push(GameScene(self.app, level_id, seed=seed, level=level))
        self.settle(settle)
        return self.game

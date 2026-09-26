"""Scene stack with cross-fade transitions."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pygame as pg

from .. import config

if TYPE_CHECKING:
    from ..app import App


class Scene:
    opaque = True          # non-opaque scenes (overlays) draw the scene below first
    music = True           # keep menu/game music running

    def __init__(self, app: "App"):
        self.app = app
        self.time = 0.0

    def enter(self) -> None:
        """Called when the scene becomes the top of the stack."""

    def leave(self) -> None:
        """Called when the scene stops being the top of the stack."""

    def handle(self, event: pg.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self, surf: pg.Surface) -> None:
        pass


class SceneManager:
    def __init__(self, app: "App"):
        self.app = app
        self.stack: list[Scene] = []
        self._snapshot: pg.Surface | None = None
        self._fade = 0.0
        self._fade_time = config.TRANSITION_TIME

    @property
    def top(self) -> Scene | None:
        return self.stack[-1] if self.stack else None

    def _change(self, fn: Callable[[], None], fade: bool = True, time: float | None = None) -> None:
        if fade and self.stack:
            self._snapshot = self.app.screen.copy()
            self._fade_time = time or config.TRANSITION_TIME
            self._fade = self._fade_time
        if self.top:
            self.top.leave()
        fn()
        if self.top:
            self.top.enter()

    def push(self, scene: Scene, fade: bool = True, time: float | None = None) -> None:
        self._change(lambda: self.stack.append(scene), fade, time)

    def pop(self, fade: bool = True, time: float | None = None) -> None:
        self._change(lambda: self.stack.pop() if self.stack else None, fade, time)

    def replace(self, scene: Scene, fade: bool = True) -> None:
        def fn():
            if self.stack:
                self.stack.pop()
            self.stack.append(scene)
        self._change(fn, fade)

    def reset(self, scene: Scene, fade: bool = True) -> None:
        def fn():
            self.stack.clear()
            self.stack.append(scene)
        self._change(fn, fade)

    def pop_to(self, cls: type, fade: bool = True) -> None:
        def fn():
            while len(self.stack) > 1 and not isinstance(self.stack[-1], cls):
                self.stack.pop()
        self._change(fn, fade)

    @property
    def transitioning(self) -> bool:
        return self._fade > 0

    def handle(self, event: pg.event.Event) -> None:
        if self.top and not (self.transitioning and event.type in
                             (pg.KEYDOWN, pg.MOUSEBUTTONDOWN, pg.TEXTINPUT)):
            self.top.handle(event)

    def update(self, dt: float) -> None:
        if self._fade > 0:
            self._fade = max(0.0, self._fade - dt)
            if self._fade == 0:
                self._snapshot = None
        if self.top:
            self.top.update(dt)

    def draw(self, surf: pg.Surface) -> None:
        first = 0
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].opaque:
                first = i
                break
        for scene in self.stack[first:]:
            scene.draw(surf)
        if self._snapshot is not None and self._fade > 0:
            t = self._fade / self._fade_time
            self._snapshot.set_alpha(int(255 * (t * t * (3 - 2 * t))))
            surf.blit(self._snapshot, (0, 0))

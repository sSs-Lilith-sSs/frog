"""In-game overlays: pause, win and lose panels (drawn over the frozen game)."""
from __future__ import annotations

import math

import pygame as pg

from .. import config, i18n
from ..art.chars import frog_sprite
from ..art.common import draw_text, fit_size, star_sprite, text_surface
from ..save import next_level_id
from ..game.grid import level_exists
from ..ui.focus import FocusGroup
from ..ui.widgets import Button
from .base import Scene
from .common import H, W, draw_panel
from .flow import go_level_select, go_menu, start_level


def fmt_time(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


class Overlay(Scene):
    opaque = False
    panel_size = (720, 600)
    animate_game = True        # keep particles/popups of the game running

    def __init__(self, app, game):
        super().__init__(app)
        self.game = game
        self.focus = FocusGroup(on_move=lambda: app.audio.play("tick"))
        self.panel = pg.Rect(0, 0, *self.panel_size)
        self.panel.center = (W // 2, H // 2 + 40)
        self.dim = pg.Surface((W, H), pg.SRCALPHA)
        self.dim.fill(config.C_DIM)

    def column(self, items, top: int, w: int = 460, h: int = 80, step: int = 96) -> list[Button]:
        out = []
        for i, (key, fn) in enumerate(items):
            r = pg.Rect(0, 0, w, h)
            r.center = (self.panel.centerx, top + i * step)
            out.append(Button(r, lambda k=key: i18n.t(k), fn, size=38))
        return out

    def row(self, items, y: int, w: int = 210, h: int = 80, gap: int = 22) -> list[Button]:
        total = len(items) * w + (len(items) - 1) * gap
        x0 = self.panel.centerx - total // 2
        return [Button((x0 + i * (w + gap), y, w, h), lambda k=key: i18n.t(k), fn, size=34, arrow=False)
                for i, (key, fn) in enumerate(items)]

    def handle(self, event: pg.event.Event) -> None:
        self.focus.handle(event)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.focus.update(dt)
        if self.animate_game:
            self.game.effects.update(dt)       # let popups/particles finish
            self.game.view.t += dt             # pads keep bobbing

    def draw(self, surf: pg.Surface) -> None:
        surf.blit(self.dim, (0, 0))
        draw_panel(surf, self.panel)
        self.draw_content(surf)
        self.focus.draw(surf)

    def draw_content(self, surf: pg.Surface) -> None:
        pass

    # shared actions
    def restart(self) -> None:
        self.app.scenes.pop(fade=False)
        self.game.restart()

    def menu(self) -> None:
        go_menu(self.app)


class PauseScene(Overlay):
    panel_size = (640, 560)
    animate_game = False

    def __init__(self, app, game):
        super().__init__(app, game)
        top = self.panel.y + 170
        self.focus.set_widgets(self.column([
            ("pause.resume", self.resume), ("pause.restart", self.restart),
            ("pause.settings", self.settings), ("pause.menu", self.menu)], top), keep=False)
        self.app.audio.duck_music(0.45, 1e9)

    def resume(self) -> None:
        self.app.audio.duck_music(1.0, 0)
        self.app.scenes.pop(time=0.15)

    def restart(self) -> None:
        self.app.audio.duck_music(1.0, 0)
        super().restart()

    def menu(self) -> None:
        self.app.audio.duck_music(1.0, 0)
        super().menu()

    def settings(self) -> None:
        from .settings import SettingsScene
        self.app.scenes.push(SettingsScene(self.app, over_game=True), time=0.15)

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN and event.key in (pg.K_ESCAPE, pg.K_p):
            self.app.audio.play("click")
            self.resume()
            return
        super().handle(event)

    def draw_content(self, surf: pg.Surface) -> None:
        draw_text(surf, i18n.t("pause.title"), 72, (self.panel.centerx, self.panel.y + 84), config.C_INK)


class WinScene(Overlay):
    panel_size = (820, 700)

    def __init__(self, app, game):
        super().__init__(app, game)
        self.result = game.world.result
        self.new_best = game.new_best
        y = self.panel.bottom - 120
        self.focus.set_widgets(self.row([("win.next", self.next), ("win.again", self.restart),
                                         ("win.menu", self.menu)], y, w=230), keep=False)
        self.star_times = [0.45 + i * 0.35 for i in range(3)]
        self._stars_played = 0

    def next(self) -> None:
        nxt = next_level_id(self.result.level_id) if self.result else None
        if nxt and level_exists(nxt):
            self.app.scenes.pop(fade=False)
            start_level(self.app, nxt, replace=True)
        else:
            go_level_select(self.app)

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.result and self._stars_played < self.result.stars \
                and self.time >= self.star_times[self._stars_played]:
            self._stars_played += 1
            self.app.audio.play("click", 1.5)

    def draw_content(self, surf: pg.Surface) -> None:
        p = self.panel
        bounce = abs(math.sin(self.time * 3)) * 10
        frog = frog_sprite(1.7, 0, "happy")
        surf.blit(frog, frog.get_rect(center=(p.centerx, p.y - 20 - bounce)))
        draw_text(surf, i18n.t("win.title"), 76, (p.centerx, p.y + 110), config.C_GOOD,
                  outline=config.C_TITLE_OUTLINE, outline_w=5)
        res = self.result
        if res is None:
            return
        for i in range(3):
            t0 = self.star_times[i]
            got = i < res.stars and self.time >= t0
            size = 96
            if got and self.time - t0 < 0.3:
                u = (self.time - t0) / 0.3
                size = int(96 * (1 + 0.5 * math.sin(u * math.pi)))
            st = star_sprite(size, got)
            lift = 14 if i == 1 else 0
            surf.blit(st, st.get_rect(center=(p.centerx - 120 + i * 120, p.y + 225 - lift)))
        shown = int(res.score * min(1.0, max(0.0, (self.time - 0.3) / 0.9)))
        draw_text(surf, f"{i18n.t('win.score')}: {shown}", 44, (p.centerx, p.y + 330), config.C_INK)
        draw_text(surf, f"{i18n.t('win.time')}: {fmt_time(res.time)}", 34, (p.centerx, p.y + 385),
                  (80, 105, 85), bold=False)
        # star criteria
        crit = [(2, i18n.t("win.no_damage")), (3, i18n.t("win.par", t=fmt_time(self.game.level.par_time)))]
        y = p.y + 440
        for n, text in crit:
            size = fit_size(text, 24, 420, bold=False)
            img = text_surface(text, size, (90, 110, 90), False)
            total = n * 26 + 10 + img.get_width()
            x = p.centerx - total // 2
            for j in range(n):
                s = star_sprite(24, res.stars >= n)
                surf.blit(s, (x + j * 26, y - 12))
            surf.blit(img, img.get_rect(midleft=(x + n * 26 + 10, y)))
            y += 34
        if self.new_best and self.time > 1.3:
            wob = math.sin(self.time * 4) * 4
            badge = text_surface(i18n.t("win.best"), 34, (255, 235, 120), True, (170, 70, 40), 4)
            badge = pg.transform.rotozoom(badge, 8 + wob, 1.0)
            surf.blit(badge, badge.get_rect(center=(p.right - 150, p.y + 318)))


class LoseScene(Overlay):
    panel_size = (720, 440)

    def __init__(self, app, game):
        super().__init__(app, game)
        y = self.panel.bottom - 120
        self.focus.set_widgets(self.row([("win.again", self.restart), ("win.menu", self.menu)], y, w=260),
                               keep=False)

    def draw_content(self, surf: pg.Surface) -> None:
        p = self.panel
        frog = frog_sprite(1.7, 0, "sad")
        surf.blit(frog, frog.get_rect(center=(p.centerx, p.y - 10)))
        draw_text(surf, i18n.t("lose.title"), 76, (p.centerx, p.y + 120), (235, 120, 120),
                  outline=(120, 40, 50), outline_w=5)
        draw_text(surf, i18n.t("lose.sub"), 34, (p.centerx, p.y + 210), (80, 105, 85), bold=False)

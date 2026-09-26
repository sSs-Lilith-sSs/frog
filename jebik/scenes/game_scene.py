"""Gameplay scene: input -> World, World events -> view/effects/audio.

TOBI PIZDA: a hit / fall / extra fly restarts the level automatically after a
short «Ой!»; running out of time shows the lose panel.
"""
from __future__ import annotations

import pygame as pg

from .. import config, i18n, progression
from ..art.common import heart_sprite
from ..game import events as ev
from ..game.grid import Level, load_level
from ..game.rules import rules_for
from ..game.world import LOST, WON, World
from ..worlds import world_by_id
from .base import Scene
from .effects import Effects
from .game_view import GameView
from .hud import Hud, exit_hint
from .touch_hud import draw_touch_buttons, make_touchpad

DIR_KEYS = {pg.K_UP: 0, pg.K_w: 0, pg.K_RIGHT: 1, pg.K_d: 1,
            pg.K_DOWN: 2, pg.K_s: 2, pg.K_LEFT: 3, pg.K_a: 3}
FIRST_REPEAT = 0.2          # a held key starts auto-hopping after this
TONGUE_CHORD = 0.06         # Space waits this long for an arrow (Space + arrow = aim)


class GameScene(Scene):
    def __init__(self, app, level_id: str, seed: int | None = None, level: Level | None = None):
        """``level`` overrides loading ``level_id`` (tests, screenshot mocks)."""
        super().__init__(app)
        self.level_id = level_id
        self.level = level or load_level(level_id)
        self.seed = seed
        self.world = World(self.level, rules_for(app.difficulty, self.level), seed=seed)
        self.theme = world_by_id(self.level.world).theme
        self.view = GameView(self.level)
        self.effects = Effects()
        profile = app.profile
        self.hud = Hud(self.world, profile.name if profile else "?")
        self.held: list[int] = []
        self.repeat = 0.0
        self.tongue_pending = 0.0
        self.new_best = False
        self.overlay_shown = False
        self.touch = make_touchpad()
        self.restart_timer: float | None = None       # TOBI PIZDA auto restart
        self.effects.banner(i18n.t("game.go", n=self.level.flies_needed), "",
                            (255, 255, 255), self.theme.text_outline, life=1.8, size=96)

    # ------------------------------------------------------------ lifecycle
    @property
    def touch_native(self) -> bool:
        return self.app.touch_controls

    def enter(self) -> None:
        self.held.clear()
        self.touch.reset()
        self.app.audio.play_music()

    def restart(self) -> None:
        self.app.scenes.replace(GameScene(self.app, self.level_id, level=self.level))

    @property
    def auto_restart(self) -> bool:
        """TOBI PIZDA: any damage restarts at once (time-out shows the panel)."""
        w = self.world
        return w.rules.one_hit and w.state == LOST and w.lose_reason != "timeout"

    def pause(self) -> None:
        if self.world.state == "playing" and not self.overlay_shown:
            from .overlays import PauseScene
            self.app.audio.play("click")
            self.app.scenes.push(PauseScene(self.app, self), time=0.15)

    # ------------------------------------------------------------ input
    def handle(self, event: pg.event.Event) -> None:
        w = self.world
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_ESCAPE, pg.K_p):
                self.pause()
            elif event.key in DIR_KEYS:
                d = DIR_KEYS[event.key]
                if d in self.held:
                    self.held.remove(d)
                self.held.append(d)
                self.repeat = FIRST_REPEAT
                if self.tongue_pending > 0 or pg.key.get_pressed()[pg.K_SPACE]:
                    # holding Space: arrows aim the tongue instead of hopping
                    self.tongue_pending = 0.0
                    w.request_tongue(d)
                else:
                    w.request_move(d, bool(event.mod & pg.KMOD_SHIFT))
            elif event.key == pg.K_SPACE:
                self.tongue_pending = TONGUE_CHORD
        elif event.type == pg.KEYUP and event.key in DIR_KEYS:
            d = DIR_KEYS[event.key]
            if d in self.held and not any(pg.key.get_pressed()[k] for k, v in DIR_KEYS.items() if v == d):
                self.held.remove(d)
        elif event.type == pg.WINDOWFOCUSLOST:
            self.pause()
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1 \
                and self.hud.pause_rect.collidepoint(event.pos):
            self.pause()
        elif event.type in (pg.FINGERDOWN, pg.FINGERMOTION, pg.FINGERUP):
            self._handle_finger(event)

    def _handle_finger(self, event: pg.event.Event) -> None:
        fn = {pg.FINGERDOWN: self.touch.down, pg.FINGERMOTION: self.touch.motion,
              pg.FINGERUP: self.touch.up}[event.type]
        for action in fn(event.finger_id, event.pos, self.time):
            if action[0] == "move":
                self.world.request_move(action[1], action[2])
            elif action[0] == "tongue":
                self.world.request_tongue()
            elif action[0] == "arm":
                self.app.audio.play("tick")
            elif action[0] == "pause":
                self.pause()

    def _auto_repeat(self, dt: float) -> None:
        if self.tongue_pending > 0:
            self.tongue_pending -= dt
            if self.tongue_pending <= 0:
                self.world.request_tongue()
        self.repeat -= dt
        f = self.world.frog
        if not self.held or self.repeat > 0 or not f.can_act or f.buffered is not None:
            return
        pressed = pg.key.get_pressed()
        d = self.held[-1]
        if pressed[pg.K_SPACE]:
            return
        shift = bool(pg.key.get_mods() & pg.KMOD_SHIFT)
        if shift and f.super_cd > 0:
            return
        self.world.request_move(d, shift)
        self.repeat = (config.SUPERJUMP_TIME if shift else config.HOP_TIME) + config.HOLD_REPEAT_DELAY

    # ------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        super().update(dt)
        self._auto_repeat(dt)
        self.world.update(dt)
        self._handle_events(self.world.drain_events())
        self.view.update(dt, self.effects, self.world)
        self.effects.update(dt)
        self.hud.update(dt)
        if self.restart_timer is not None:
            self.restart_timer -= dt
            if self.restart_timer <= 0:
                self.restart_timer = None
                self.restart()
            return
        if self.world.show_result and not self.overlay_shown:
            self.overlay_shown = True
            from .overlays import LoseScene, WinScene
            if self.world.state == WON:
                self.app.scenes.push(WinScene(self.app, self), time=0.3)
            elif self.world.state == LOST:
                self.app.scenes.push(LoseScene(self.app, self), time=0.3)

    def _handle_events(self, events: list[ev.Event]) -> None:
        audio, fx, view, k = self.app.audio, self.effects, self.view, self.view.k
        kinds = {e.kind for e in events}
        for e in events:
            if view.field_art.on_event(e, view, fx, audio):
                continue
            if e.kind == ev.HOP:
                audio.play("jump")
                x, y = view.to_px(self.world.frog.hop_from)
                fx.ring(x, y, 10 * k, 30 * k, 0.5)
            elif e.kind == ev.SUPERJUMP:
                audio.play("superjump")
                x, y = view.to_px(self.world.frog.hop_from)
                fx.ring(x, y, 12 * k, 44 * k, 0.6, (230, 250, 255), 3)
                fx.burst(x, y, (230, 250, 230), n=8, speed=160 * k, size=4 * k, life=0.4)
            elif e.kind == ev.SUPER_DENIED:
                audio.play("denied")
                self.hud.deny_super()
            elif e.kind == ev.BUMP:
                audio.play("tick")
            elif e.kind == ev.LAND:
                strong = e.value and e.value > config.HOP_TIME
                view.dip(e.cell, 1.6 if strong else 1.0)
                x, y = view.to_px(e.cell)
                fx.ring(x, y, 18 * k, (48 if strong else 38) * k, 0.55)
                if strong:
                    fx.shake(3)
            elif e.kind == ev.TONGUE:
                audio.play("tongue")
            elif e.kind == ev.EAT:
                self._on_eat(e, overeat=ev.OVEREAT in kinds)
            elif e.kind == ev.OVEREAT:
                audio.play("overeat")
                x, y = view.to_px(e.pos)
                fx.popup(i18n.t("game.overeat"), x, y - 30 * k, config.C_RED_TEXT, 44, (255, 255, 255),
                         life=1.4)
                fx.shake(8)
            elif e.kind == ev.FULL:
                audio.play("full")
                sub = exit_hint(self.level.world) if self.world.exit_ready else i18n.t("game.full_boss")
                fx.banner(i18n.t("game.full"), sub, (255, 225, 110), (120, 60, 20))
            elif e.kind == ev.EXIT_SPAWN:
                x, y = view.to_px(e.cell)
                view.show_exit()
                fx.burst(x, y, (255, 200, 225), n=18, speed=260 * k, size=6 * k, life=0.9)
                fx.burst(x, y, (255, 240, 150), n=10, speed=200 * k, size=5 * k, life=0.8, kind="star")
                fx.ring(x, y, 20 * k, 80 * k, 0.9, (255, 235, 170), 4)
            elif e.kind == ev.SPLASH:
                audio.play("splash")
                x, y = view.to_px(e.cell)
                fx.splash(x, y, k)
                fx.shake(5)
            elif e.kind == ev.HIT:
                audio.play("hit")
                x, y = view.to_px(e.pos)
                fx.burst(x, y, (255, 120, 120), n=12, speed=240 * k, size=5 * k, life=0.5)
                fx.shake(12)
            elif e.kind == ev.RESPAWN:
                x, y = view.to_px(e.cell)
                fx.burst(x, y, (255, 255, 255), n=14, speed=150 * k, size=4 * k, life=0.6, kind="star")
                fx.ring(x, y, 10 * k, 46 * k, 0.6, (255, 255, 255), 3)
                view.dip(e.cell, 1.3)
            elif e.kind == ev.HEART_GAIN:
                audio.play("powerup")
                x, y = view.to_px(e.pos)
                fx.popup("+1", x, y - 30 * k, (255, 255, 255), 42, config.C_HEART,
                         icon=heart_sprite(40, config.C_HEART))
            elif e.kind == ev.HEART_FULL:
                audio.play("powerup")
                x, y = view.to_px(e.pos)
                fx.popup(i18n.t("game.max_hearts"), x, y - 30 * k, (255, 230, 120), 32, (120, 60, 20))
            elif e.kind == ev.FIREFLY:
                audio.play("powerup")
                x, y = view.to_px(e.pos)
                fx.popup(i18n.t("game.long_tongue"), x, y - 30 * k, (255, 245, 150), 34, (120, 80, 20))
            elif e.kind == ev.TIME_BONUS:
                audio.play("powerup")
                x, y = view.to_px(e.pos)
                fx.popup(i18n.t("game.time_bonus", n=int(e.value)), x, y - 30 * k, (255, 230, 120), 42,
                         (120, 60, 20))
            elif e.kind in (ev.BOSS_HIT, ev.BOSS_DEFEATED):
                self._on_boss(e)
            elif e.kind == ev.WIN:
                self._on_win()
            elif e.kind == ev.LOSE:
                self._on_lose(e.value)

    def _on_eat(self, e: ev.Event, overeat: bool) -> None:
        kind, value = e.value
        k = self.view.k
        x, y = self.view.to_px(e.pos)
        fx = self.effects
        colors = {"fly": (70, 70, 80), "dragon": (90, 180, 240), "gold": (255, 215, 80),
                  "firefly": (255, 245, 140)}
        fx.burst(x, y, colors[kind], n=10, speed=180 * k, size=4 * k, life=0.45)
        if kind in ("gold", "firefly"):
            fx.burst(x, y, (255, 240, 150), n=8, speed=160 * k, size=5 * k, life=0.7, kind="star")
            return
        self.app.audio.play("eat")
        if not overeat:
            fx.popup(f"+{value}", x, y - 26 * k, (255, 230, 120) if value > 1 else (255, 255, 255),
                     46 if value > 1 else 40, self.theme.text_outline)

    def _on_boss(self, e: ev.Event) -> None:
        k, fx = self.view.k, self.effects
        x, y = self.view.to_px(e.pos)
        boss = self.world.boss
        if e.kind == ev.BOSS_HIT:
            self.app.audio.play("hit")
            fx.shake(14)
            fx.burst(x, y, (255, 240, 150), n=16, speed=320 * k, size=6 * k, life=0.8, kind="star")
            key = boss.hit_text_key if boss else None
            if key:
                fx.popup(i18n.t(key), x, y - 40 * k, (255, 245, 120), 72, (150, 30, 60), life=1.6)
        else:
            self.app.audio.play("win")
            fx.burst(x, y, (255, 200, 120), n=30, speed=400 * k, size=7 * k, life=1.2, kind="star")
            fx.banner(i18n.t("game.boss_defeated"), exit_hint(self.level.world) if self.world.full else "",
                      (255, 225, 110), (120, 60, 20))

    def _on_lose(self, reason: str) -> None:
        audio = self.app.audio
        audio.play("lose")
        audio.duck_music(0.2, 3.0)
        if self.auto_restart:
            self.overlay_shown = True
            self.restart_timer = config.TOBI_RESTART_DELAY
            self.effects.banner(i18n.t("game.oops"), i18n.t("game.again"), (255, 150, 150),
                                (120, 30, 40), life=config.TOBI_RESTART_DELAY + 0.3, size=120)

    def _on_win(self) -> None:
        audio = self.app.audio
        audio.play("win")
        audio.duck_music(0.2, 3.5)
        x, y = self.view.to_px(self.world.frog.pos())
        k = self.view.k
        self.effects.burst(x, y, (255, 120, 150), n=14, speed=300 * k, size=6 * k, life=1.1, kind="heart")
        self.effects.burst(x, y, (255, 240, 150), n=16, speed=340 * k, size=6 * k, life=1.1, kind="star")
        res = self.world.result
        profile = self.app.profile
        if res and profile:
            self.new_best = profile.record_result(res.difficulty, res.level_id, res.score, res.stars, res.time)
            progression.refresh_unlocks(profile)
            self.app.persist()

    # ------------------------------------------------------------ draw
    def draw(self, surf: pg.Surface) -> None:
        self.view.draw(surf, self.world, self.effects, bool(self.app.settings.get("show_grid")))
        self.effects.draw_popups(surf)
        self.effects.draw_banners(surf, self.view.field.center)
        self.hud.draw(surf)
        if self.app.touch_controls:
            draw_touch_buttons(surf, self.touch, self.world.frog.super_ready_fraction(), self.time)

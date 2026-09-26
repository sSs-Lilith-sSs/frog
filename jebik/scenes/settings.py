"""Settings: volumes, music choice (with preview), fullscreen, grid, language."""
from __future__ import annotations

import pygame as pg

from .. import i18n
from ..ui.widgets import Choice, Slider, Toggle
from .common import W, MenuScene, draw_hint, draw_panel

ROW_W, ROW_H, ROW_STEP = 1160, 84, 98


class SettingsScene(MenuScene):
    title_key = "settings.title"

    def __init__(self, app, over_game: bool = False):
        super().__init__(app, over_game)
        s = app.settings
        x = W // 2 - ROW_W // 2
        y = 230
        rows = []

        def row(i: int) -> tuple[int, int, int, int]:
            return (x, y + i * ROW_STEP, ROW_W, ROW_H)

        rows.append(Slider(row(0), lambda: i18n.t("settings.music_volume"),
                           lambda: s["music_volume"], self._set_music_volume))
        rows.append(Slider(row(1), lambda: i18n.t("settings.sfx_volume"),
                           lambda: s["sfx_volume"], self._set_sfx_volume))
        rows.append(Choice(row(2), lambda: i18n.t("settings.music"),
                           [("A", lambda: "A · " + i18n.t("settings.music_a")),
                            ("B", lambda: "B · " + i18n.t("settings.music_b")),
                            ("C", lambda: "C · " + i18n.t("settings.music_c"))],
                           lambda: s["music_track"], self._set_track, control_w=700))
        rows.append(Toggle(row(3), lambda: i18n.t("settings.fullscreen"),
                           lambda: bool(s["fullscreen"]), self._set_fullscreen,
                           lambda: i18n.t("settings.on"), lambda: i18n.t("settings.off")))
        rows.append(Toggle(row(4), lambda: i18n.t("settings.grid"),
                           lambda: bool(s["show_grid"]), self._set_grid,
                           lambda: i18n.t("settings.on"), lambda: i18n.t("settings.off")))
        rows.append(Choice(row(5), lambda: i18n.t("settings.language"),
                           [(c, i18n.LANG_LABELS[c]) for c in i18n.LANGS],
                           lambda: s["lang"], self.app.set_lang, control_w=420))
        self.panel = pg.Rect(x - 30, y - 30, ROW_W + 60, 6 * ROW_STEP + 44)
        self.back_btn = self.back_button(W // 2 - 170, self.panel.bottom + 34, 340)
        self.focus.set_widgets(rows + [self.back_btn], keep=False)
        self._sfx_preview = 0.0

    # ------------------------------------------------------------ setters
    def _set_music_volume(self, v: float) -> None:
        self.app.settings["music_volume"] = v
        self.app.audio.apply_volume()

    def _set_sfx_volume(self, v: float) -> None:
        self.app.settings["sfx_volume"] = v
        if self._sfx_preview <= 0:
            self.app.audio.play("eat")
            self._sfx_preview = 0.18

    def _set_track(self, track: object) -> None:
        self.app.settings["music_track"] = track
        self.app.audio.play_music(str(track), force=True)       # preview

    def _set_fullscreen(self, on: bool) -> None:
        self.app.set_fullscreen(on)

    def _set_grid(self, on: bool) -> None:
        self.app.settings["show_grid"] = on

    # ------------------------------------------------------------ scene
    def update(self, dt: float) -> None:
        super().update(dt)
        self._sfx_preview -= dt

    def leave(self) -> None:
        self.app.persist()

    def draw_content(self, surf: pg.Surface) -> None:
        draw_panel(surf, self.panel)

    def draw_over(self, surf: pg.Surface) -> None:
        draw_hint(surf)

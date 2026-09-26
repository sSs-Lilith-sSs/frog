"""Main menu — the approved mockup, animated."""
from __future__ import annotations

import pygame as pg

from .. import config, i18n
from ..art.chars import frog_front_sprite
from ..art.common import draw_text, font, rounded_panel, triangle_sprite
from ..ui.widgets import Button
from .common import MenuScene, draw_logo
from .lang import lang_pills


class ProfilePill(Button):
    """'Гравець: Кыця ▾' pill in the top-left corner."""

    def __init__(self, app, on_click):
        self.app = app
        super().__init__((40, 36, 470, 70), "", on_click, size=32, arrow=False, shadow=0, border=0)
        self._resize()

    def _text(self) -> str:
        p = self.app.profile
        return i18n.t("menu.player", name=p.name if p else "?")

    def _resize(self) -> None:
        self.rect.w = min(760, 100 + font(32).size(self._text())[0] + 70)

    def draw(self, surf: pg.Surface) -> None:
        self._resize()
        r = self.rect.move(self.shake_offset(), 3 if self.pressed else 0)
        fill = (255, 240, 190) if self.hot else (255, 255, 255)
        surf.blit(rounded_panel(r.size, fill, (225, 190, 90) if self.hot else None, 35, 3), r.topleft)
        spr = frog_front_sprite(1.0)
        surf.blit(spr, spr.get_rect(center=(r.x + 50, r.centery + 3)))
        tr = draw_text(surf, self._text(), 32, (r.x + 100, r.centery - 1), config.C_INK_SOFT,
                       anchor="midleft")
        tri = triangle_sprite(22, 2, config.C_INK_SOFT)
        surf.blit(tri, tri.get_rect(center=(tr.right + 30, r.centery + 1)))


class MainMenuScene(MenuScene):
    veil = False

    def __init__(self, app):
        super().__init__(app)
        self._build()

    def _build(self) -> None:
        items = [("menu.play", self._play), ("menu.levels", self._levels),
                 ("menu.records", self._records), ("menu.settings", self._settings),
                 ("menu.howto", self._howto), ("menu.quit", self.app.quit)]
        buttons = []
        for i, (key, fn) in enumerate(items):
            r = pg.Rect(0, 0, 480, 86)
            r.center = (620, 470 + i * 100)
            buttons.append(Button(r, lambda k=key: i18n.t(k), fn, size=40))
        self.quit_button = buttons[-1]
        widgets = buttons + [ProfilePill(self.app, self._profiles)] + lang_pills(self.app)
        self.focus.set_widgets(widgets, keep=False)

    # ------------------------------------------------------------ actions
    def _play(self) -> None:
        from .difficulty import DifficultyScene
        self.app.scenes.push(DifficultyScene(self.app))

    def _levels(self) -> None:
        from .level_select import LevelSelectScene
        self.app.scenes.push(LevelSelectScene(self.app))

    def _records(self) -> None:
        from .records import RecordsScene
        self.app.scenes.push(RecordsScene(self.app))

    def _settings(self) -> None:
        from .settings import SettingsScene
        self.app.scenes.push(SettingsScene(self.app))

    def _howto(self) -> None:
        from .howto import HowToScene
        self.app.scenes.push(HowToScene(self.app))

    def _profiles(self) -> None:
        from .profile import ProfileScene
        self.app.scenes.push(ProfileScene(self.app, from_menu=True))

    def back(self) -> None:
        if self.focus.focused is self.quit_button:
            self.app.quit()
        else:
            self.focus.focus(self.quit_button, sound=True)

    def enter(self) -> None:
        self.app.audio.play_music()

    def draw_content(self, surf: pg.Surface) -> None:
        draw_logo(surf, (620, 220), 190, self.time)

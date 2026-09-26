"""Profile select / create / delete — the first screen."""
from __future__ import annotations

import pygame as pg

from .. import config, i18n, progression
from ..art.chars import frog_front_sprite
from ..art.common import draw_text, fit_size, star_sprite
from ..game.rules import EZZZ
from ..save import MAX_NAME_LEN
from ..ui.widgets import Button, TextInput
from .common import W, MenuScene, draw_hint, draw_logo, draw_panel
from .lang import lang_pills

MAX_PROFILES = 6
ROW_W, ROW_H, ROW_STEP = 620, 76, 90
PANEL = pg.Rect(W // 2 - 430, 300, 860, 0)


def _cross_icon(surf: pg.Surface, r: pg.Rect) -> None:
    c = r.center
    for dx in (-1, 1):
        pg.draw.line(surf, (190, 60, 70), (c[0] - 13, c[1] - 13 * dx), (c[0] + 13, c[1] + 13 * dx), 6)


def _plus_icon(surf: pg.Surface, r: pg.Rect) -> None:
    x, y = r.x + 52, r.centery
    pg.draw.rect(surf, config.C_INK, (x - 14, y - 4, 28, 8), border_radius=4)
    pg.draw.rect(surf, config.C_INK, (x - 4, y - 14, 8, 28), border_radius=4)


class ProfileScene(MenuScene):
    title_key = None

    def __init__(self, app, from_menu: bool = False):
        super().__init__(app)
        self.from_menu = from_menu
        self.mode = "list"          # list | create | confirm
        self.error = ""
        self.to_delete: str | None = None
        self.input = TextInput((0, 0, ROW_W, 90), lambda: i18n.t("profile.placeholder"),
                               MAX_NAME_LEN, self._create)
        self._build()

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        profiles = self.app.save.profiles
        if self.mode == "list" and not profiles:
            self.mode = "create"
        x = W // 2 - ROW_W // 2 - 44
        y = PANEL.y + 40
        widgets = []
        if self.mode == "list":
            y += 50
            for p in profiles:
                name = p.name
                row = Button((x, y, ROW_W, ROW_H), name, lambda n=name: self._select(n),
                             size=38, arrow=False, icon=self._profile_icon(name))
                dele = Button((x + ROW_W + 16, y, ROW_H, ROW_H), "", lambda n=name: self._ask_delete(n),
                              arrow=False, icon=_cross_icon, shadow=6)
                row.profile_name = name
                widgets += [row, dele]
                y += ROW_STEP
            if len(profiles) < MAX_PROFILES:
                widgets.append(Button((x, y + 6, ROW_W, ROW_H), lambda: i18n.t("profile.new"),
                                      self._start_create, size=36, arrow=False, icon=_plus_icon,
                                      fill=(225, 245, 210)))
                y += ROW_STEP + 6
        elif self.mode == "create":
            self.input.rect.topleft = (x + 44, y + 70)
            widgets.append(self.input)
            bw = (ROW_W - 20) // 2 if profiles else ROW_W
            widgets.append(Button((x + 44, y + 215, bw, ROW_H), lambda: i18n.t("profile.create"),
                                  lambda: self._create(self.input.text), size=36, arrow=False))
            if profiles:
                widgets.append(Button((x + 44 + bw + 20, y + 215, bw, ROW_H),
                                      lambda: i18n.t("common.cancel"), self._cancel_create,
                                      size=36, arrow=False))
            y += 320
        else:   # confirm delete
            bw = (ROW_W - 20) // 2
            widgets.append(Button((x + 44, y + 120, bw, ROW_H), lambda: i18n.t("common.yes"),
                                  self._do_delete, size=36, arrow=False))
            widgets.append(Button((x + 44 + bw + 20, y + 120, bw, ROW_H), lambda: i18n.t("common.no"),
                                  self._cancel_delete, size=36, arrow=False))
            y += 230
        self.panel = pg.Rect(PANEL.x, PANEL.y, PANEL.w, y - PANEL.y + 30)
        widgets += lang_pills(self.app, self._build)
        self.focus.set_widgets(widgets, keep=False)
        if self.mode == "list" and self.app.save.current:
            for w in widgets:
                if getattr(w, "profile_name", None) == self.app.save.current:
                    self.focus.focus(w)
        if self.mode == "confirm":
            self.focus.focus(widgets[1])             # default: "No"
        if self.mode == "create":
            self.focus.focus(self.input)

    def _profile_icon(self, name: str):
        def icon(surf: pg.Surface, r: pg.Rect) -> None:
            spr = frog_front_sprite(0.9)
            surf.blit(spr, spr.get_rect(center=(r.x + 50, r.centery)))
            p = self.app.save.find(name)
            stars = sum(d.total_stars() for d in p.progress.values()) if p else 0
            st = star_sprite(30)
            tr = draw_text(surf, str(stars), 28, (r.right - 26, r.centery), config.C_INK,
                           anchor="midright")
            surf.blit(st, st.get_rect(midright=(tr.left - 6, r.centery - 1)))
        return icon

    # ------------------------------------------------------------ actions
    def _select(self, name: str) -> None:
        self.app.save.current = name
        self.app.persist()
        p = self.app.profile
        if p is None or not progression.tobi_unlocked(p):
            self.app.difficulty = EZZZ       # TOBI PIZDA of the previous profile would lock every level
        from .main_menu import MainMenuScene
        self.app.scenes.reset(MainMenuScene(self.app))

    def _start_create(self) -> None:
        self.mode, self.error = "create", ""
        self.input.text = ""
        self._build()
        pg.key.start_text_input()         # re-ask for the on-screen keyboard

    def _cancel_create(self) -> None:
        self.mode, self.error = "list", ""
        self._build()

    def _create(self, text: str) -> None:
        name = text.strip()
        if not name:
            self.error = i18n.t("profile.err_empty")
        elif self.app.save.find(name):
            self.error = i18n.t("profile.err_exists")
        else:
            self.app.save.create_profile(name)
            self.app.persist()
            self._select(self.app.save.current)
            return
        self.input.shake = 0.4
        self.app.audio.play("denied")

    def _ask_delete(self, name: str) -> None:
        self.to_delete = name
        self.mode = "confirm"
        self._build()

    def _do_delete(self) -> None:
        if self.to_delete:
            self.app.save.delete_profile(self.to_delete)
            self.app.persist()
        self.to_delete = None
        self.mode = "list"
        self._build()

    def _cancel_delete(self) -> None:
        self.mode = "list"
        self._build()

    # ------------------------------------------------------------ scene
    def enter(self) -> None:
        pg.key.start_text_input()
        try:
            pg.key.set_text_input_rect(self.input.rect)
        except (AttributeError, pg.error):
            pass

    def leave(self) -> None:
        pg.key.stop_text_input()

    def back(self) -> None:
        if self.mode == "confirm":
            self._cancel_delete()
        elif self.mode == "create" and self.app.save.profiles:
            self._cancel_create()
        elif self.from_menu and self.app.save.profile:
            self.app.scenes.pop()

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.TEXTINPUT:
            if self.mode == "create":
                self.input.handle_text(event.text)
                self.error = ""
            return
        if (event.type == pg.KEYDOWN and event.key == pg.K_DELETE and self.mode == "list"):
            name = getattr(self.focus.focused, "profile_name", None)
            if name:
                self._ask_delete(name)
                return
        super().handle(event)

    def draw_content(self, surf: pg.Surface) -> None:
        draw_logo(surf, (W // 2, 118), 128, self.time)
        draw_panel(surf, self.panel)
        cy = self.panel.y + 44
        if self.mode == "list":
            draw_text(surf, i18n.t("profile.title"), 46, (W // 2, cy), config.C_INK)
        elif self.mode == "create":
            draw_text(surf, i18n.t("profile.enter_name"), 44, (W // 2, cy + 30), config.C_INK)
            if self.error:
                draw_text(surf, self.error, 28, (W // 2, cy + 179), config.C_RED_TEXT)
        else:
            q = i18n.t("profile.delete_q", name=self.to_delete or "")
            draw_text(surf, q, fit_size(q, 40, self.panel.w - 60), (W // 2, cy + 50), config.C_INK)

    def draw_over(self, surf: pg.Surface) -> None:
        hint = i18n.t("common.hint_nav")
        if self.mode == "list":
            hint += " · " + i18n.t("profile.hint")
        draw_hint(surf, hint)

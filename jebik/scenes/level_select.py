"""Level select: 3 worlds x 4 levels with stars, locks and "soon" tiles."""
from __future__ import annotations

import math

import pygame as pg

from .. import config, i18n
from ..art.chars import fly_sprite
from ..art.common import (draw_text, fit_size, font, lock_sprite, render_ss,
                          rounded_panel, star_sprite)
from ..game.grid import level_exists
from ..game.rules import DIFFICULTY_NAMES, EZZZ, TOBI
from ..ui.widgets import Button
from .common import W, MenuScene, draw_hint
from .flow import LEVELS_PER_WORLD, WORLDS, start_level

TILE_W, TILE_H, GAP = 210, 170, 26
LABEL_W = 180             # world card: picture only
WORLD_ICON = 124
ROW_Y0, ROW_STEP = 290, 200
WORLD_TINT = {1: (205, 236, 245), 2: (222, 240, 200), 3: (250, 226, 240)}
WORLD_INK = {1: (40, 100, 140), 2: (70, 110, 40), 3: (150, 70, 120)}


def world_icon(world: int, size: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        u = size * ss / 20
        if world == 1:     # water drop
            pg.draw.circle(s, (70, 160, 215), (10 * u, 12.5 * u), 6 * u)
            pg.draw.polygon(s, (70, 160, 215), [(10 * u, 1.5 * u), (4.4 * u, 10.5 * u), (15.6 * u, 10.5 * u)])
            pg.draw.circle(s, (190, 230, 250), (8 * u, 13 * u), 1.8 * u)
        elif world == 2:   # grass tuft
            for dx, h, lean in ((-5, 12, -3), (0, 16, 0), (5, 11, 3), (-2, 9, -1), (3, 13, 1)):
                pg.draw.polygon(s, (90, 160, 60), [((10 + dx - 1.6) * u, 18 * u), ((10 + dx + 1.6) * u, 18 * u),
                                                   ((10 + dx + lean) * u, (18 - h) * u)])
            pg.draw.ellipse(s, (130, 95, 60), (3 * u, 16.5 * u, 14 * u, 3.5 * u))
        else:              # pink cloud
            for cx, cy, r in ((7, 12, 4.5), (12, 10, 5.5), (15.5, 13, 3.8), (10, 14, 4)):
                pg.draw.circle(s, (245, 175, 210), (cx * u, cy * u), r * u)
    return render_ss((size, size), draw)


class LevelTile(Button):
    def __init__(self, rect, scene: "LevelSelectScene", level_id: str):
        self.scene = scene
        self.level_id = level_id
        self.world = int(level_id[0])
        super().__init__(rect, level_id, lambda: scene.open_level(level_id), size=46,
                         locked=lambda: not self.unlocked, radius=26, shadow=7)

    @property
    def unlocked(self) -> bool:
        p = self.scene.app.profile
        return bool(p and p.diff(self.scene.app.difficulty).is_unlocked(self.level_id))

    @property
    def playable(self) -> bool:
        return self.unlocked and level_exists(self.level_id)

    def activate(self) -> None:
        if self.unlocked and not self.playable:
            self.shake = 0.4
            from ..ui.widgets import play
            play("denied")
            return
        super().activate()

    def draw(self, surf: pg.Surface) -> None:
        r = self.rect.move(self.shake_offset(), 0)
        down = self.shadow if self.pressed else 0
        if not self.unlocked:
            fill, ink = config.C_BUTTON_DISABLED, (120, 125, 118)
        elif self.hot:
            fill, ink = config.C_BUTTON_HOT, config.C_INK
        else:
            fill, ink = WORLD_TINT[self.world], WORLD_INK[self.world]
        surf.blit(rounded_panel(r.size, fill, config.C_BUTTON_SHADOW, 26, 4,
                                None if self.pressed else config.C_BUTTON_SHADOW, 7), (r.x, r.y + down))
        r = r.move(0, down)
        if not self.unlocked:
            lk = lock_sprite(56, (120, 125, 118))
            surf.blit(lk, lk.get_rect(center=(r.centerx, r.centery - 14)))
            draw_text(surf, self.level_id, 30, (r.centerx, r.bottom - 34), ink)
            return
        draw_text(surf, self.level_id, 48, (r.centerx, r.y + 46), ink)
        if not self.playable:
            text = i18n.t("common.soon")
            draw_text(surf, text, fit_size(text, 34, r.w - 20), (r.centerx, r.y + 112), ink, bold=False)
            return
        rec = self.scene.app.profile.diff(self.scene.app.difficulty).record(self.level_id)
        for i in range(3):
            st = star_sprite(44, i < rec.stars)
            bob = math.sin(self.t * 5 + i) * 2 if self.hot and i < rec.stars else 0
            surf.blit(st, st.get_rect(center=(r.centerx - 50 + i * 50, r.y + 104 + bob)))
        if rec.best_score:
            text = i18n.t("levels.best", score=rec.best_score)
            draw_text(surf, text, fit_size(text, 22, r.w - 16, bold=False), (r.centerx, r.bottom - 22),
                      ink, bold=False)


class DiffPill(Button):
    def __init__(self, rect, diff: str, scene: "LevelSelectScene", locked: bool):
        super().__init__(rect, DIFFICULTY_NAMES[diff], lambda: None, size=30, locked=locked,
                         selected=lambda: scene.app.difficulty == diff, arrow=False,
                         radius=28, shadow=0, border=3)

    def draw(self, surf: pg.Surface) -> None:
        fill, ink = self.colors()
        r = self.rect.move(self.shake_offset(), 0)
        surf.blit(rounded_panel(r.size, fill, config.C_BUTTON_SHADOW, 28, 3), r.topleft)
        text = str(self.label)
        if self.locked:
            lk = lock_sprite(30)
            tw = fit_size(text, 30, r.w - 90)
            img_w = font(tw).size(text)[0]
            x0 = r.centerx - (img_w + 38) // 2
            surf.blit(lk, lk.get_rect(midleft=(x0, r.centery)))
            draw_text(surf, text, tw, (x0 + 38, r.centery - 1), ink, anchor="midleft")
        else:
            draw_text(surf, text, 30, (r.centerx, r.centery - 1), ink)


class LevelSelectScene(MenuScene):
    title_key = "levels.title"
    show_frog = False

    def __init__(self, app):
        super().__init__(app)
        total_w = LABEL_W + LEVELS_PER_WORLD * TILE_W + (LEVELS_PER_WORLD - 1) * GAP + 30
        self.x0 = (W - total_w) // 2
        tiles = []
        for wi, world in enumerate(WORLDS):
            y = ROW_Y0 + wi * ROW_STEP
            for li in range(LEVELS_PER_WORLD):
                x = self.x0 + LABEL_W + 30 + li * (TILE_W + GAP)
                tiles.append(LevelTile((x, y, TILE_W, TILE_H), self, f"{world}-{li + 1}"))
        pills = [DiffPill((W // 2 - 290, 168, 260, 56), EZZZ, self, False),
                 DiffPill((W // 2 + 30, 168, 260, 56), TOBI, self, True)]
        self.focus.set_widgets(tiles + pills + [self.back_button()], keep=False)
        self._icons = {w: world_icon(w, WORLD_ICON) for w in WORLDS}

    def open_level(self, level_id: str) -> None:
        start_level(self.app, level_id)

    def draw_content(self, surf: pg.Surface) -> None:
        for wi, world in enumerate(WORLDS):
            y = ROW_Y0 + wi * ROW_STEP
            r = pg.Rect(self.x0, y + 8, LABEL_W, TILE_H - 16)
            surf.blit(rounded_panel(r.size, (255, 255, 255), WORLD_INK[world], 30, 3), r.topleft)
            ic = self._icons[world]
            bob = math.sin(self.time * 1.8 + wi) * 3
            surf.blit(ic, ic.get_rect(center=(r.centerx, r.centery + bob)))
        # a fly buzzing next to the title, for life
        fs = fly_sprite(1.2, "fly", int(self.time * 20) % 2 == 1)
        surf.blit(fs, fs.get_rect(center=(W // 2 + 330 + math.sin(self.time * 2) * 20,
                                          90 + math.sin(self.time * 3.3) * 10)))

    def draw_over(self, surf: pg.Surface) -> None:
        draw_hint(surf)

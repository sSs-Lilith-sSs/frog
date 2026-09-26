"""Enemy renderers: base class, registry and a placeholder look.

A world's art package registers one renderer per enemy kind::

    @register_enemy_art("hedgehog")
    class HedgehogArt(EnemyArt):
        def draw(self, surf, enemy, off): ...

The game view creates one instance per kind and level (``view`` gives
``to_px``, ``k`` (= cell / 64), ``cs`` and ``t``). Kinds without a renderer
get :class:`EnemyArt`'s placeholder (a labelled disc), so logic can be tried
before the art exists. Telegraphs (warnings) are drawn generically unless
:meth:`EnemyArt.draw_telegraph` returns True.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, TypeVar

import pygame as pg

from ..game.enemy import AIR, Enemy, Telegraph
from .common import disc_sprite, draw_text

if TYPE_CHECKING:
    from ..scenes.game_view import GameView


class EnemyArt:
    # Drawing (and warnings) of UNDER / GROUND enemies is clipped to the field
    # frame; AIR ones (birds, a leaping pike, a boss above the field) are not.
    # Set True / False to force it for a kind.
    clip: bool | None = None

    def __init__(self, view: "GameView"):
        self.view = view
        self.k = view.k
        self.cs = view.cs

    def px(self, pos: tuple[float, float], off: tuple[int, int]) -> tuple[float, float]:
        x, y = self.view.to_px(pos)
        return x + off[0], y + off[1]

    def draw(self, surf: pg.Surface, enemy: Enemy, off: tuple[int, int]) -> None:
        """Placeholder: magenta disc with the kind name (replace per enemy)."""
        x, y = self.px(enemy.pos, off)
        r = self.cs * (0.42 if not enemy.boss else 0.9)
        pulse = 1 + 0.05 * math.sin(self.view.t * 4 + id(enemy) % 7)
        col = (190, 70, 170) if not getattr(enemy, "hit_flash", 0) else (255, 255, 255)
        img = disc_sprite(round(r * pulse * 2) / 2, col)
        surf.blit(img, img.get_rect(center=(round(x), round(y))))
        draw_text(surf, enemy.kind, max(14, int(18 * self.k)), (x, y), (255, 255, 255),
                  outline=(80, 20, 70), outline_w=2)

    def draw_telegraph(self, surf: pg.Surface, enemy: Enemy, tg: Telegraph,
                       off: tuple[int, int]) -> bool:
        """Custom warning look; return False to use the generic one."""
        return False

    def clipped(self, enemy: Enemy) -> bool:
        """Whether this enemy's drawing is clipped to the field frame now."""
        return enemy.layer != AIR if self.clip is None else self.clip

    def update(self, dt: float) -> None:
        """Per-frame animation state (optional)."""


A = TypeVar("A", bound=type[EnemyArt])
_ART: dict[str, type[EnemyArt]] = {}


def register_enemy_art(kind: str) -> Callable[[A], A]:
    def deco(cls: A) -> A:
        _ART[kind] = cls
        return cls
    return deco


def enemy_art_class(kind: str) -> type[EnemyArt]:
    return _ART.get(kind, EnemyArt)


def has_art(kind: str) -> bool:
    return kind in _ART

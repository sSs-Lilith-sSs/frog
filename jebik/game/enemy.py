"""Enemy protocol, boss base class and the enemy registry (no pygame).

A world package defines its enemies by subclassing :class:`Enemy` (or
:class:`Boss`) and registering them under the id used in level files::

    @register_enemy("hedgehog")
    class Hedgehog(Enemy):
        def update(self, dt, world): ...

The :class:`~jebik.game.world.World` creates enemies from the level's
spawns via :func:`create_enemy` and calls the hooks below; every hook has a
harmless default so an enemy only overrides what it needs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, ClassVar, TypeVar

from .. import config
from .grid import Cell, Spawn

if TYPE_CHECKING:
    from .world import World

Pos = tuple[float, float]

# Render layers (see GameView): under the tiles, on the ground, in the air.
UNDER = "under"
GROUND = "ground"
AIR = "air"


@dataclass(frozen=True)
class Telegraph:
    """A warning the renderer shows before an attack.

    ``style`` picks a generic look (see ``jebik/scenes/telegraphs.py``):
    ``"zone"`` red cells, ``"line"`` dashed row/column, ``"arrow"`` edge
    arrow, ``"shadow"`` dark blob, ``"bubbles"`` bubbles, ``"shake"`` mound.
    Enemy art may draw its own instead. ``progress`` runs 0 -> 1 until the hit.
    """
    style: str
    cells: tuple[Cell, ...]
    progress: float = 0.0
    direction: int | None = None


class Enemy:
    """Base class for every predator and boss.

    Subclasses usually set ``kind`` (via :func:`register_enemy`), keep a
    continuous ``pos`` in cell units and override :meth:`update`.
    """
    kind: ClassVar[str] = "enemy"
    boss: ClassVar[bool] = False
    layer: ClassVar[str] = GROUND
    contact_radius: ClassVar[float] = 0.55

    # instance defaults (plain class attributes so dataclass subclasses work)
    alive: bool = True
    pos: Pos = (0.0, 0.0)
    anim: float = 0.0
    stunned: float = 0.0

    # ------------------------------------------------------------ creation
    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Enemy":
        """Build the enemy for ``spawn`` (override for custom setup)."""
        enemy = cls()
        if spawn.cell is not None:
            enemy.pos = (float(spawn.cell[0]), float(spawn.cell[1]))
        return enemy

    # ------------------------------------------------------------ per frame
    def update(self, dt: float, world: "World") -> None:
        """Advance the behaviour. ``world.frog_target`` is the frog's cell
        (None while it is splashing / the level is over)."""
        self.anim += dt
        self.stunned = max(0.0, self.stunned - dt)

    # ------------------------------------------------------------ queries
    def center(self) -> Pos:
        """Where popups / hit sparks appear (cell units)."""
        return self.pos

    def occupied(self) -> set[Cell]:
        """Cells the exit / respawn should avoid."""
        return {(round(self.pos[0]), round(self.pos[1]))}

    def hurts(self, world: "World", frog_pos: Pos) -> bool:
        """Contact damage check (called while the frog is vulnerable)."""
        return self.alive and self.stunned <= 0 and math.dist(self.pos, frog_pos) < self.contact_radius

    def supports(self, cell: Cell) -> bool:
        """True if the frog can stand on this enemy at ``cell`` (whale back)."""
        return False

    def blocks(self, cell: Cell) -> bool:
        """True if the frog may not hop into ``cell`` because of this enemy."""
        return False

    def telegraphs(self) -> list[Telegraph]:
        return []

    def tongue_hit(self, world: "World", line: list[Cell]) -> int | None:
        """Index into ``line`` (the tongue's cells, nearest first) where the
        tongue hits this enemy, or None. The tongue stops there and
        :meth:`on_tongued` is called when it reaches full length."""
        return None

    # ------------------------------------------------------------ reactions
    def on_tongued(self, world: "World") -> None:
        """The frog's tongue hit this enemy."""

    def on_frog_hit(self, world: "World") -> None:
        """This enemy just hurt the frog (e.g. back off)."""

    def on_frog_respawn(self, world: "World", cell: Cell) -> None:
        """The frog respawned at ``cell`` after falling."""

    def on_frog_land(self, world: "World", cell: Cell) -> None:
        """The frog landed on ``cell`` (e.g. on the whale's back)."""


class Boss(Enemy):
    """Enemy with health, vulnerability windows and a HUD pill.

    ``take_hit`` only works while :attr:`vulnerable`; open a window with
    :meth:`open_window` (e.g. whale's back above water, stunned boar).
    Defeat (hp 0) lets the exit appear once exactly N flies are eaten.
    """
    boss = True
    max_hp: ClassVar[int] = config.BOSS_HP
    name_key: ClassVar[str] = "boss.generic"      # i18n key of the HUD name
    hit_text_key: ClassVar[str | None] = None     # popup on a hit ("SASAT!")
    window_time: ClassVar[float] = config.BOSS_WINDOW

    hp: int = config.BOSS_HP
    window: float = 0.0                 # seconds of vulnerability left
    defeated: bool = False
    hit_flash: float = 0.0              # for renderers: >0 right after a hit

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Boss":
        boss = super().create(world, spawn)
        boss.hp = int(spawn.param("hp", cls.max_hp))
        return boss

    @property
    def vulnerable(self) -> bool:
        return self.window > 0 and not self.defeated

    def enraged(self, world: "World") -> bool:
        """Half of the flies eaten -> angrier attacks (whale rule)."""
        return world.eaten * 2 >= world.needed

    def open_window(self, seconds: float | None = None) -> None:
        self.window = self.window_time if seconds is None else seconds

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.window = max(0.0, self.window - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)

    def on_tongued(self, world: "World") -> None:
        self.take_hit(world)

    def take_hit(self, world: "World") -> bool:
        if not self.vulnerable:
            return False
        self.hp = max(0, self.hp - 1)
        self.window = 0.0
        self.hit_flash = config.BOSS_HIT_FLASH
        world.boss_hit(self)
        if self.hp == 0:
            self.defeated = True
            world.boss_defeated(self)
        return True

    def hurts(self, world: "World", frog_pos: Pos) -> bool:
        return not self.defeated and super().hurts(world, frog_pos)


# ---------------------------------------------------------------- registry
E = TypeVar("E", bound=type[Enemy])
_REGISTRY: dict[str, type[Enemy]] = {}


def register_enemy(kind: str) -> Callable[[E], E]:
    """Class decorator: make ``kind`` usable in level files."""
    def deco(cls: E) -> E:
        if not issubclass(cls, Enemy):
            raise TypeError(f"{cls!r} is not an Enemy")
        other = _REGISTRY.get(kind)
        if other is not None and other.__qualname__ != cls.__qualname__:
            raise ValueError(f"enemy kind {kind!r} already registered by {other!r}")
        cls.kind = kind
        _REGISTRY[kind] = cls
        return cls
    return deco


def enemy_class(kind: str) -> type[Enemy]:
    from ..worlds import ensure_loaded
    ensure_loaded()
    try:
        return _REGISTRY[kind]
    except KeyError:
        raise KeyError(f"unknown enemy kind {kind!r}; registered: {sorted(_REGISTRY)}") from None


def registered_kinds() -> list[str]:
    from ..worlds import ensure_loaded
    ensure_loaded()
    return sorted(_REGISTRY)


def create_enemy(world: "World", spawn: Spawn) -> Enemy:
    return enemy_class(spawn.kind).create(world, spawn)

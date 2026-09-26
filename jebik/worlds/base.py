"""World definition: what a world package declares about itself (no pygame).

Every package ``jebik/worlds/<id>/`` creates one :class:`WorldDef` in its
``__init__.py`` and passes it to :func:`register_world`. Logic, levels and
strings are plain Python; the art lives in ``<package>.art`` and is only
imported by the renderer (``art_module``), so logic tests stay pygame-free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

Color = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    """Colours shared by HUD, level select and menus for one world."""
    hud_bg: Color                       # top HUD bar
    hud_line: Color                     # accent line under the bar
    hud_sub: Color = (170, 210, 170)    # secondary HUD text
    ring_bg: Color = (60, 90, 70)       # empty part of HUD cooldown rings
    tile_tint: Color = (205, 236, 245)  # level-select tile fill
    tile_ink: Color = (40, 100, 140)    # level-select tile text
    fill: Color = (45, 125, 170)        # screen fill behind a shaking field
    text_outline: Color = (40, 70, 40)  # outline of in-game popups


@dataclass(frozen=True)
class WorldDef:
    id: str                             # package name: "water", "earth", "sky"
    index: int                          # 1, 2, 3 — the "w" in level ids "w-n"
    theme: Theme
    playable: tuple[int, ...] = ()      # level numbers offered to players
    levels_dir: Path = Path()
    art_module: str = ""                # e.g. "jebik.worlds.water.art"
    strings: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    story: tuple[str, ...] = ()         # i18n keys of the cards shown before x-1

    @property
    def name_key(self) -> str:
        return f"{self.id}.name"

    def level_id(self, n: int) -> str:
        return f"{self.index}-{n}"


_WORLDS: dict[str, WorldDef] = {}


def register_world(world: WorldDef) -> WorldDef:
    bad = [k for k in world.strings if not k.startswith(world.id + ".")]
    if bad:
        raise ValueError(f"world {world.id!r}: string keys must start with '{world.id}.': {bad}")
    for other in _WORLDS.values():
        if other.index == world.index and other.id != world.id:
            raise ValueError(f"world index {world.index} used by {other.id!r} and {world.id!r}")
    _WORLDS[world.id] = world
    return world


def registered() -> dict[str, WorldDef]:
    return _WORLDS

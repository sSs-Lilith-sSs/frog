"""World 1 «Вода»: lily pads over water (style B), snake / pike / heron / whale."""
from __future__ import annotations

from pathlib import Path

from ..base import Theme, WorldDef, register_world
from . import heron, pike, snake, whale  # noqa: F401  (register the enemies)
from .strings import STRINGS

WORLD = register_world(WorldDef(
    id="water",
    index=1,
    theme=Theme(hud_bg=(25, 45, 40), hud_line=(120, 220, 90), hud_sub=(170, 210, 170),
                ring_bg=(60, 90, 70), tile_tint=(205, 236, 245), tile_ink=(40, 100, 140),
                fill=(45, 125, 170), text_outline=(40, 70, 40)),
    playable=(1, 2, 3, 4),
    levels_dir=Path(__file__).parent / "levels",
    art_module=__name__ + ".art",
    strings=STRINGS,
    story=("water.story.1",),
))

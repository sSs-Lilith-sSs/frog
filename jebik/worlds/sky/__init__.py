"""World 3 «Небо»: pink clouds over the abyss, moving rows; swallow / hawk / crow / Jesus."""
from __future__ import annotations

from pathlib import Path

from ..base import Theme, WorldDef, register_world
from . import enemies, jesus  # noqa: F401  (registers the enemies)
from .strings import STRINGS

WORLD = register_world(WorldDef(
    id="sky",
    index=3,
    theme=Theme(hud_bg=(52, 26, 50), hud_line=(255, 140, 200), hud_sub=(230, 190, 220),
                ring_bg=(92, 56, 88), tile_tint=(250, 226, 240), tile_ink=(150, 70, 120),
                fill=(70, 40, 90), text_outline=(110, 40, 90)),
    playable=(1, 2, 3, 4),
    levels_dir=Path(__file__).parent / "levels",
    art_module=__name__ + ".art",
    strings=STRINGS,
    story=("sky.story.1",),
))

"""World 2 «Земля»: grass tiles over pits; hedgehog / fox / mole / boar."""
from __future__ import annotations

from ...paths import resource_path
from ..base import Theme, WorldDef, register_world
from . import enemies  # noqa: F401  (registers hedgehog, fox, mole, boar)
from .strings import STRINGS

WORLD = register_world(WorldDef(
    id="earth",
    index=2,
    theme=Theme(hud_bg=(46, 42, 24), hud_line=(196, 170, 84), hud_sub=(214, 200, 150),
                ring_bg=(88, 78, 46), tile_tint=(222, 240, 200), tile_ink=(70, 110, 40),
                fill=(58, 44, 30), text_outline=(70, 50, 25)),
    playable=(1, 2, 3, 4),
    levels_dir=resource_path("worlds", "earth", "levels"),
    art_module=__name__ + ".art",
    strings=STRINGS,
    story=("earth.story.1", "earth.story.2"),
))

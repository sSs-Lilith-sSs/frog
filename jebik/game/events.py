"""Events the logic emits for the renderer / audio (pure data)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Event kinds
HOP = "hop"                 # cell=target
SUPERJUMP = "superjump"     # cell=target
SUPER_DENIED = "super_denied"
BUMP = "bump"               # tried to hop out of the field
LAND = "land"               # cell
TONGUE = "tongue"           # value=direction
EAT = "eat"                 # pos, kind, value (counter delta)
OVEREAT = "overeat"         # pos
FULL = "full"               # exactly N reached
EXIT_SPAWN = "exit_spawn"   # cell
SPLASH = "splash"           # cell
HIT = "hit"                 # pos
RESPAWN = "respawn"         # cell
HEART_GAIN = "heart_gain"   # pos
HEART_FULL = "heart_full"   # golden fly eaten with full hearts
FIREFLY = "firefly"         # long tongue started
FLY_SPAWN = "fly_spawn"     # kind
WIN = "win"
LOSE = "lose"


@dataclass
class Event:
    kind: str
    cell: tuple[int, int] | None = None
    pos: tuple[float, float] | None = None
    value: Any = None

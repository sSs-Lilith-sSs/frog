"""Events the logic emits for the renderer / audio (pure data).

World packages may define their own kinds (prefix them with the world id,
e.g. ``"earth.stomp"``); the game scene forwards every event it does not
know to the world's art hooks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Frog / flies
HOP = "hop"                 # cell=target
SUPERJUMP = "superjump"     # cell=target
SUPER_DENIED = "super_denied"
BUMP = "bump"               # tried to hop out of the field / into an obstacle
LAND = "land"               # cell
TONGUE = "tongue"           # value=direction
EAT = "eat"                 # pos, kind, value (counter delta)
OVEREAT = "overeat"         # pos
FULL = "full"               # exactly N reached
EXIT_SPAWN = "exit_spawn"   # cell
SPLASH = "splash"           # cell (fell into a hole / off a moving row)
HIT = "hit"                 # pos
RESPAWN = "respawn"         # cell
HEART_GAIN = "heart_gain"   # pos
HEART_FULL = "heart_full"   # golden fly eaten with full hearts
TIME_BONUS = "time_bonus"   # pos, value=seconds (TOBI PIZDA golden fly)
FIREFLY = "firefly"         # long tongue started
FLY_SPAWN = "fly_spawn"     # kind
PUSHED = "pushed"           # cell=target, value=direction (wave, wind...)
WIN = "win"
LOSE = "lose"               # value=reason: "hearts" | "hit" | "fall" | "overeat" | "timeout"

# Tiles / hazards
TILE_WARN = "tile_warn"     # cell: unstable tile starts flickering
TILE_GONE = "tile_gone"     # cell: unstable tile vanished
TILE_BACK = "tile_back"     # cell: unstable tile is back
HOLE_OPEN = "hole_open"     # cell, value=seconds: temporary hole
HOLE_CLOSE = "hole_close"   # cell
ROW_SHIFT = "row_shift"     # cell=(0, row), value=direction (+1/-1)

# Bosses
BOSS_HIT = "boss_hit"       # pos, value=(kind, hp_left)
BOSS_DEFEATED = "boss_defeated"   # pos, value=kind
BOSS_TELL = "boss_tell"     # pos, value=(kind, attack name) — optional sound cue


@dataclass
class Event:
    kind: str
    cell: tuple[int, int] | None = None
    pos: tuple[float, float] | None = None
    value: Any = None

"""Tunables of the sky world (docs/TZ.md §8)."""
from __future__ import annotations

# Melting clouds ('U' tiles) — the level file may override via "unstable:".
MELT_WARN = 1.5
MELT_GONE = 4.0

# Swallow: edge arrow for 1 s, then a fast pass along a row / column.
SWALLOW_WARN = 1.0
SWALLOW_SPEED = 13.0            # cells / s while crossing
SWALLOW_PAUSE = (2.2, 4.0)      # seconds between passes
SWALLOW_FIRST = (1.5, 2.5)      # first pass after the level starts
SWALLOW_AIM = 0.7               # chance to pick the frog's row / column
SWALLOW_MARGIN = 1.5            # starts / ends this far outside the field

# Hawk: soars over the abyss, slower than the frog; 2-cell dash when close.
HAWK_SPEED = 2.1                # cells / s
HAWK_SPIRAL = 0.55              # sideways part of the approach (circling look)
HAWK_TRIGGER = 2.0              # dash when this close (cells)
HAWK_WINDUP = 0.4
HAWK_DASH = 2.0                 # cells
HAWK_DASH_TIME = 0.22
HAWK_RECOVER = 1.3              # harmless drift after a dash / a hit
HAWK_RADIUS = 0.5

# Crow: eats flies, caws (others faster), pecks the frog next to it.
CROW_SPEED = 3.2                # cells / s in the air
CROW_EAT_TIME = 0.6
CROW_REST = (1.2, 2.5)          # sitting between flights
CROW_CAW_EVERY = (6.0, 9.0)
CROW_CAW_TIME = 0.8
CROW_HASTE = (1.5, 3.0)         # enemy speed factor, seconds
CROW_PECK_WINDUP = 0.5
CROW_PECK_COOLDOWN = 1.8
CROW_HUNT_RANGE = 7.0           # only flies this close are worth flying to

# Jesus (boss, level 3-4).
JESUS_FIRST = 2.5               # first attack after the start
JESUS_IDLE = (1.6, 2.4)         # pause between attacks
JESUS_IDLE_ENRAGED = (1.0, 1.5)
JESUS_BEAM_WARN = 1.0           # the row / column glows, then the beam
JESUS_BEAM_TIME = 0.5
JESUS_MULTIPLY_WARN = 1.0
JESUS_MULTIPLY = (10, 15)       # flies conjured by «примноження»
JESUS_MULTIPLY_CAP = 14         # skip if this many counted flies are already out
JESUS_HALO_OUT = 1.5            # halo boomerang: fly out, hover, come back
JESUS_HALO_HOVER = 1.1
JESUS_HALO_HOVER_ENRAGED = 0.8
JESUS_HALO_BACK = 1.5
JESUS_HALO_BONK = 0.55          # caught halo flies back to his head
JESUS_HALO_CATCH = 0.65         # tongue catches the halo within this distance of a cell
JESUS_REBUILD_WARN = 1.3
JESUS_REBUILD = (4, 6)          # clouds that vanish / appear
JESUS_REBUILD_HOLE = 10.0       # vanished clouds come back after this
JESUS_HIT_TIME = 1.2            # «ouch» face

# His place above the field (px; shared by the logic's halo home and the art).
JESUS_CLOUD_GAP = 30            # field top -> bottom of his cloud (the 12 px frame + clear air)
JESUS_PILL_GAP = 20             # part of top_reserve kept free under the HUD boss pill
JESUS_FIGURE_H = 188            # halo top -> cloud bottom, in figure units (art/jesus_figure.py)
JESUS_HEAD_ABOVE_CLOUD = 147.2  # head centre above the cloud bottom, figure units

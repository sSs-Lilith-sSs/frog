"""Tunables of the earth world (docs/TZ.md §8). Never hard-code these in logic."""
from __future__ import annotations

# Crumbling ground ('U' tiles) — the level file may override via "unstable:".
CRUMBLE_WARN = 1.5
CRUMBLE_GONE = 4.0

# ---------------------------------------------------------------- hedgehog
HEDGEHOG_STEP = 0.95          # seconds per cell while walking (slow)
HEDGEHOG_SIGHT = 9            # max cells along a row/column it reacts to the frog
HEDGEHOG_CURL = 0.45          # curls into a ball before rolling (telegraph)
HEDGEHOG_ROLL_SPEED = 7.5     # cells per second while rolling
HEDGEHOG_BUMP_REST = 0.9      # sits dazed after rolling into an edge / stump
HEDGEHOG_GONE = 5.0           # fell into a pit: gone for this long
HEDGEHOG_RESPAWN_DIST = 4     # respawns at least this far (Manhattan) from the frog

# ---------------------------------------------------------------- fox
FOX_CHASE_STEP = 0.30         # seconds per cell while chasing (fast)
FOX_WANDER_STEP = 0.5
FOX_SIGHT = 6                 # starts chasing within this Manhattan distance
FOX_LOSE_SIGHT = 9
FOX_JUMP_TIME = 0.5           # leap over a single pit
FOX_RECOVER = 1.0             # sits still after every jump
FOX_RETREAT = 2.2             # backs off after biting

# ---------------------------------------------------------------- mole
MOLE_STEP = 0.5               # seconds per cell underground
MOLE_TREMOR = 1.2             # ground shakes under the frog before the pop
MOLE_OUT = 1.3                # stays popped out of its pit
MOLE_REST = 2.5               # roams aimlessly before hunting again
MOLE_HOLE_TIME = 8.0          # the pit it leaves

# ---------------------------------------------------------------- boar (boss, 2x2)
BOAR_THINK = 1.3              # pause between actions (calm)
BOAR_THINK_ENRAGED = 0.8
BOAR_WALK_STEP = 0.55         # seconds per cell while lining up with the frog
BOAR_TELL = 1.1               # red lane before a charge
BOAR_TELL_ENRAGED = 0.8
BOAR_CHARGE_SPEED = 8.0       # cells per second
BOAR_PIT_EVERY = 2            # one temporary pit every N cells of a charge
BOAR_PIT_TIME = 6.0
BOAR_EDGE_STUN = 2.0          # ran into the field edge
BOAR_STUMP_STUN = 3.0         # ran into a stump -> vulnerable for this long
BOAR_STOMP_CHANCE = 0.3       # chance an action is a stomp instead of a charge
BOAR_STOMP_TELL = 0.9
BOAR_STOMP_CELLS = 5
BOAR_STOMP_RADIUS = 4         # crumbled cells are picked near the frog first
BOAR_STUMP_REGROW = 1.0       # a stump broken without a hit grows back after the stun

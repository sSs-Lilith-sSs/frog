"""Tunables of the water world: snake, pike, heron and the whale boss."""
from __future__ import annotations

# ---------------------------------------------------------------- snake
SNAKE_LENGTH = 4                   # head + body segments
SNAKE_CHASE_STEP = 0.27            # seconds per cell while chasing
SNAKE_WANDER_STEP = 0.46           # seconds per cell while wandering
SNAKE_SIGHT = 4                    # starts chasing within this Manhattan distance
SNAKE_LOSE_SIGHT = 6               # gives up beyond this distance
SNAKE_RETREAT_TIME = 2.6           # after biting, the snake backs off

# ---------------------------------------------------------------- pike
PIKE_SIGHT = 5                     # notices a frog next to water within this distance
PIKE_SWIM_SPEED = 3.0              # cells / s while hidden (under pads too)
PIKE_WANDER_SPEED = 1.2
PIKE_TERRITORY = 4                 # wanders within this distance of its start
PIKE_WARN = 0.8                    # bubbles before the lunge (TZ)
PIKE_LUNGE = 0.55                  # out of the water, on the pad
PIKE_BITE_WINDOW = (0.1, 0.45)     # part of the lunge that bites the target pad
PIKE_COOLDOWN = 2.4                # hides after a lunge
PIKE_RESPAWN_CALM = 2.0            # no ambush right after the frog respawns

# ---------------------------------------------------------------- heron
HERON_INTERVAL = (3.8, 6.0)        # seconds between strikes
HERON_FIRST = (4.0, 6.0)           # first strike delay after the level starts
HERON_WARN = 1.2                   # shadow on the frog's cell before the beak (TZ)
HERON_STRIKE = 0.45                # beak down: hurts on that cell
HERON_LEAVE = 0.8                  # flies off again

# ---------------------------------------------------------------- whale (boss)
WHALE_SWIM_SPEED = 3.2             # silhouette cells / s
WHALE_GAP = (1.8, 2.6)             # pause between attacks
WHALE_GAP_ENRAGED = (0.9, 1.4)
WHALE_START_DELAY = 3.0            # calm start of the level
WHALE_SURFACE_WARN = 1.5           # red 3x3 zone (TZ)
WHALE_BACK_TIME = 3.0              # back above water = vulnerability window
WHALE_DIVE_WARN = 1.0              # frog on the back: jump off!
WHALE_SINK_TIME = 5.0              # pads in the zone sink this long (TZ)
WHALE_FOUNTAIN_WARN = 1.0          # dashed row / column (TZ)
WHALE_JET_TIME = 0.4
WHALE_WAVE_WARN = 1.0              # arrows on the edge
WHALE_WAVE_SPEED = 7.0             # cells / s of the wave front
WHALE_WAVE_SPEED_ENRAGED = 10.0
WHALE_GULP_WARN = 0.6              # the mouth opens at the edge
WHALE_GULP_TIME = 2.0              # pull duration (TZ)
WHALE_GULP_STEP = 0.7              # the frog slides one cell per step
WHALE_GULP_RANGE = 6               # pulls the frog only this close to the edge
WHALE_GULP_FLY_SPEED = 2.2         # flies drift toward the mouth (cells / s)
WHALE_ENRAGED_WARN = 0.75          # warning times x this when enraged
WHALE_COMBO_CHANCE = 0.5           # enraged: chain a second attack without a pause
WHALE_SURFACE_EVERY = 2            # at most this many other attacks between surfacings

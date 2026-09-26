"""Tunables of the water world (snake now; pike, heron and whale later)."""
from __future__ import annotations

# ---------------------------------------------------------------- snake
SNAKE_LENGTH = 4                   # head + body segments
SNAKE_CHASE_STEP = 0.27            # seconds per cell while chasing
SNAKE_WANDER_STEP = 0.46           # seconds per cell while wandering
SNAKE_SIGHT = 4                    # starts chasing within this Manhattan distance
SNAKE_LOSE_SIGHT = 6               # gives up beyond this distance
SNAKE_RETREAT_TIME = 2.6           # after biting, the snake backs off

# TODO(water agent): pike, heron, whale tunables (see docs/TZ.md §8)

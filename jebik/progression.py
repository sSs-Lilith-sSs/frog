"""Which levels / difficulties are open (pure, computed from completed levels).

* Levels open strictly in order 1-1 ... 3-4, skipping levels that are not
  playable yet (unbuilt levels show «скоро»). A level is open when every
  playable level before it is completed — so worlds unlock sequentially and
  new levels shipped later slot in without breaking old saves.
* TOBI PIZDA opens after all playable EZZZ levels are completed. The unlock
  is sticky (``tobi`` profile flag), so shipping more levels never re-locks it.
* Progress, stars and records are kept separately per difficulty.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .game.rules import EZZZ, TOBI
from .worlds import catalog

if TYPE_CHECKING:
    from .save import Profile

LOCKED = "locked"
OPEN = "open"
SOON = "soon"             # not built yet
TOBI_FLAG = "tobi"


def is_unlocked(profile: "Profile", difficulty: str, level_id: str) -> bool:
    if difficulty == TOBI and not tobi_unlocked(profile):
        return False
    if not catalog.is_playable(level_id):
        return False
    prog = profile.diff(difficulty)
    for lid in catalog.playable_levels():
        if lid == level_id:
            return True
        if not prog.completed(lid):
            return False
    return False


def level_state(profile: "Profile", difficulty: str, level_id: str) -> str:
    if not catalog.is_playable(level_id):
        return SOON
    return OPEN if is_unlocked(profile, difficulty, level_id) else LOCKED


def next_level_to_play(profile: "Profile", difficulty: str) -> str | None:
    """First open level that is not completed yet (None: all done)."""
    prog = profile.diff(difficulty)
    for lid in catalog.playable_levels():
        if not is_unlocked(profile, difficulty, lid):
            return None
        if not prog.completed(lid):
            return lid
    return None


def ezzz_finished(profile: "Profile") -> bool:
    prog = profile.diff(EZZZ)
    levels = catalog.playable_levels()
    return bool(levels) and all(prog.completed(lid) for lid in levels)


def tobi_unlocked(profile: "Profile") -> bool:
    return profile.has(TOBI_FLAG) or ezzz_finished(profile)


def refresh_unlocks(profile: "Profile") -> bool:
    """Call after a win; returns True if TOBI PIZDA just got unlocked."""
    if not profile.has(TOBI_FLAG) and ezzz_finished(profile):
        profile.mark(TOBI_FLAG)
        return True
    return False


def world_complete(profile: "Profile", difficulty: str, world_index: int) -> bool:
    prog = profile.diff(difficulty)
    levels = [lid for lid in catalog.playable_levels() if lid.startswith(f"{world_index}-")]
    return bool(levels) and all(prog.completed(lid) for lid in levels)

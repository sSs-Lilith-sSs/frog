"""Level catalogue: auto-discovered level files and the fixed 3 x 4 order.

Levels live in ``jebik/worlds/<id>/levels/<w>-<n>.txt``. A level is
*playable* (offered in level select, reachable by "Next") when its file
exists **and** its world lists ``n`` in ``WorldDef.playable`` — so a world
agent can keep work-in-progress maps in the folder without exposing them.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..game.grid import Level, LevelError, parse_level
from . import all_worlds, world_of_level

WORLD_COUNT = 3
LEVELS_PER_WORLD = 4
ALL_LEVELS: tuple[str, ...] = tuple(f"{w}-{n}" for w in range(1, WORLD_COUNT + 1)
                                    for n in range(1, LEVELS_PER_WORLD + 1))


def level_path(level_id: str) -> Path | None:
    try:
        world = world_of_level(level_id)
    except (KeyError, ValueError):
        return None
    path = world.levels_dir / f"{level_id}.txt"
    return path if path.is_file() else None


def discovered() -> list[str]:
    """Every level file found in the world packages (sorted by id)."""
    out = []
    for w in all_worlds():
        for p in sorted(w.levels_dir.glob(f"{w.index}-*.txt")):
            out.append(p.stem)
    return sorted(out, key=lambda lid: tuple(int(x) for x in lid.split("-")))


def is_playable(level_id: str) -> bool:
    if level_id not in ALL_LEVELS or level_path(level_id) is None:
        return False
    return int(level_id.split("-")[1]) in world_of_level(level_id).playable


def playable_levels() -> list[str]:
    return [lid for lid in ALL_LEVELS if is_playable(lid)]


@lru_cache(maxsize=32)
def _load(level_id: str, mtime: float) -> Level:
    path = level_path(level_id)
    if path is None:
        raise FileNotFoundError(f"level {level_id} not found")
    level = parse_level(path.read_text(encoding="utf-8"), level_id)
    world = world_of_level(level_id)
    if level.id != level_id:
        raise LevelError(f"{path.name}: id {level.id!r} does not match the file name")
    if level.world != world.id:
        raise LevelError(f"{path.name}: world {level.world!r}, expected {world.id!r}")
    return level


def load_level(level_id: str) -> Level:
    path = level_path(level_id)
    if path is None:
        raise FileNotFoundError(f"level {level_id} not found")
    return _load(level_id, path.stat().st_mtime)


def next_level(level_id: str, playable_only: bool = True) -> str | None:
    """The following level in the 1-1 ... 3-4 order (skipping unbuilt ones)."""
    if level_id not in ALL_LEVELS:
        return None
    for lid in ALL_LEVELS[ALL_LEVELS.index(level_id) + 1:]:
        if not playable_only or is_playable(lid):
            return lid
    return None

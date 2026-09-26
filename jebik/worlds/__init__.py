"""World packages: water (1), earth (2), sky (3).

Each package registers a :class:`~jebik.worlds.base.WorldDef` and its
enemies on import. :func:`ensure_loaded` imports them all (idempotent);
everything that needs the registries calls it lazily, so importing a single
logic module never drags in the others.
"""
from __future__ import annotations

import importlib

from .base import Theme, WorldDef, register_world, registered

PACKAGES = ("water", "earth", "sky")      # load order = world index order
_loaded = False


def ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    for name in PACKAGES:
        importlib.import_module(f"{__name__}.{name}")


def all_worlds() -> list[WorldDef]:
    ensure_loaded()
    return sorted(registered().values(), key=lambda w: w.index)


def world_by_id(world_id: str) -> WorldDef:
    ensure_loaded()
    return registered()[world_id]


def world_by_index(index: int) -> WorldDef:
    for w in all_worlds():
        if w.index == index:
            return w
    raise KeyError(f"no world with index {index}")


def world_of_level(level_id: str) -> WorldDef:
    return world_by_index(int(level_id.split("-")[0]))


__all__ = ["Theme", "WorldDef", "register_world", "ensure_loaded", "all_worlds",
           "world_by_id", "world_by_index", "world_of_level"]

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("JEBIK_NO_SPLASH", "1")       # splash tests pass App(splash=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from jebik.game.grid import Level, parse_level  # noqa: E402
from jebik.game.world import World  # noqa: E402


def make_level(rows: list[str], flies_needed: int = 5, par: float = 60, header: str = "") -> Level:
    """A level from map rows; ``header`` adds extra ``key: value`` lines."""
    text = f"id: 9-9\nflies_needed: {flies_needed}\npar_time: {par}\n{header}\n---\n" + "\n".join(rows)
    return parse_level(text)


def make_world(rows: list[str], flies_needed: int = 5, enemies: bool = False,
               header: str = "", rules=None) -> World:
    return World(make_level(rows, flies_needed, header=header), rules=rules, seed=1,
                 auto_spawn=False, spawn_enemies=enemies)


def run(world: World, seconds: float, dt: float = 1 / 60) -> None:
    for _ in range(int(round(seconds / dt))):
        world.update(dt)


@pytest.fixture
def open_world() -> World:
    return make_world([
        "OOOOO",
        "OOOOO",
        "OOFOO",
        "OOOOO",
        "OOOOO",
    ])

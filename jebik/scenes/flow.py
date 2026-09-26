"""Navigation helpers shared by several screens (which level to start, etc.)."""
from __future__ import annotations

from ..game.grid import level_exists

WORLDS = (1, 2, 3)
LEVELS_PER_WORLD = 4
ALL_LEVELS = tuple(f"{w}-{i}" for w in WORLDS for i in range(1, LEVELS_PER_WORLD + 1))


def next_level_to_play(app) -> str | None:
    """First unlocked, playable and not yet completed level (None if none)."""
    profile = app.profile
    if profile is None:
        return None
    prog = profile.diff(app.difficulty)
    for lid in ALL_LEVELS:
        if prog.is_unlocked(lid) and level_exists(lid) and not prog.record(lid).completed:
            return lid
    return None


def start_level(app, level_id: str, replace: bool = False) -> None:
    from .game_scene import GameScene
    scene = GameScene(app, level_id)
    if replace:
        app.scenes.replace(scene)
    else:
        app.scenes.push(scene)


def go_level_select(app) -> None:
    """Back to the main menu, then open level select (from game overlays)."""
    from .level_select import LevelSelectScene
    from .main_menu import MainMenuScene
    app.scenes.pop_to(MainMenuScene, fade=False)
    app.scenes.push(LevelSelectScene(app))


def go_menu(app) -> None:
    from .main_menu import MainMenuScene
    app.scenes.pop_to(MainMenuScene)

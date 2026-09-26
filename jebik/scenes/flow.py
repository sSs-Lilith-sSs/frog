"""Navigation between screens: starting levels (with cutscenes), next level, menus."""
from __future__ import annotations

from .. import progression, story
from ..worlds import catalog


def next_level_to_play(app) -> str | None:
    """First open and not yet completed level (None if none)."""
    profile = app.profile
    if profile is None:
        return None
    return progression.next_level_to_play(profile, app.difficulty)


def start_level(app, level_id: str, replace: bool = False) -> None:
    """Start ``level_id``; the first time a world begins, its story plays first."""
    from .game_scene import GameScene
    cards, flag = story.before_level(app.profile, level_id)

    def launch(replace_top: bool) -> None:
        scene = GameScene(app, level_id)
        if replace_top:
            app.scenes.replace(scene)
        else:
            app.scenes.push(scene)

    if cards:
        from .cutscene import CutsceneScene
        app.profile.mark(flag)
        app.persist()
        cut = CutsceneScene(app, cards, on_done=lambda: launch(True))
        if replace:
            app.scenes.replace(cut)
        else:
            app.scenes.push(cut)
        return
    launch(replace)


def after_win(app, level_id: str) -> None:
    """«Далі» on the win panel: finale after 3-4, else the next open level."""
    cards, flag = story.after_level(app.profile, level_id)
    if cards:
        from .cutscene import CutsceneScene
        app.profile.mark(flag)
        app.persist()
        app.scenes.pop(fade=False)
        app.scenes.replace(CutsceneScene(app, cards, on_done=lambda: go_level_select(app)))
        return
    nxt = catalog.next_level(level_id)
    profile = app.profile
    if nxt and profile and progression.is_unlocked(profile, app.difficulty, nxt):
        app.scenes.pop(fade=False)
        start_level(app, nxt, replace=True)
    else:
        go_level_select(app)


def go_level_select(app) -> None:
    """Back to the main menu, then open level select (from game overlays)."""
    from .level_select import LevelSelectScene
    from .main_menu import MainMenuScene
    app.scenes.pop_to(MainMenuScene, fade=False)
    app.scenes.push(LevelSelectScene(app))


def go_menu(app) -> None:
    from .main_menu import MainMenuScene
    app.scenes.pop_to(MainMenuScene)


def show_credits(app) -> None:
    from .cutscene import CutsceneScene
    app.scenes.push(CutsceneScene(app, story.credits_cards(), on_done=lambda: app.scenes.pop()))

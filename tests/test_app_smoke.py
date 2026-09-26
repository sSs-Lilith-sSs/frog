"""Headless end-to-end smoke tests through the real scenes."""
import random

import pygame as pg
import pytest

from jebik import save

DT = 1 / 60


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik.app import App
    a = App()
    yield a


def frames(app, seconds, events=()):
    events = list(events)
    for i in range(max(1, int(seconds / DT))):
        app.frame(DT, events if i == 0 else [])


def key(app, k, mod=0, wait=0.05):
    frames(app, DT, [pg.event.Event(pg.KEYDOWN, key=k, mod=mod, unicode="", scancode=0)])
    frames(app, wait, [pg.event.Event(pg.KEYUP, key=k, mod=mod, unicode="", scancode=0)])


def top_name(app):
    return type(app.scenes.top).__name__


def test_first_launch_create_profile_and_browse_menus(app):
    frames(app, 0.3)
    assert top_name(app) == "ProfileScene"
    frames(app, DT, [pg.event.Event(pg.TEXTINPUT, text="Кыця")])
    key(app, pg.K_RETURN)
    frames(app, 0.4)
    assert top_name(app) == "MainMenuScene"
    assert app.save.current == "Кыця"
    assert save.load().current == "Кыця"          # persisted
    # visit every menu entry with the keyboard and come back with Esc
    for downs, name in ((1, "LevelSelectScene"), (2, "RecordsScene"), (3, "SettingsScene"),
                        (4, "HowToScene"), (0, "DifficultyScene")):
        from jebik.scenes.main_menu import MainMenuScene
        menu = app.scenes.top
        assert isinstance(menu, MainMenuScene)
        menu.focus.index = 0
        menu.focus._fix_index()
        for _ in range(downs):
            key(app, pg.K_DOWN)
        key(app, pg.K_RETURN)
        frames(app, 0.4)
        assert top_name(app) == name
        key(app, pg.K_ESCAPE)
        frames(app, 0.4)
        assert top_name(app) == "MainMenuScene"


def test_language_switch_updates_setting(app):
    app.save.create_profile("A")
    from jebik.scenes.main_menu import MainMenuScene
    app.scenes.reset(MainMenuScene(app), fade=False)
    app.set_lang("ru")
    frames(app, 0.1)
    from jebik import i18n
    assert i18n.get_lang() == "ru" and app.settings["lang"] == "ru"
    assert save.load().settings["lang"] == "ru"


def _start_game(app, seed=1):
    app.save.create_profile("P")
    from jebik.scenes.game_scene import GameScene
    from jebik.scenes.main_menu import MainMenuScene
    app.scenes.reset(MainMenuScene(app), fade=False)
    g = GameScene(app, "1-1", seed=seed)
    app.scenes.push(g, fade=False)
    return g


def test_random_play_does_not_crash(app):
    g = _start_game(app)
    rnd = random.Random(4)
    keys = [pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT, pg.K_SPACE, pg.K_w, pg.K_a]
    for _ in range(400):
        k = rnd.choice(keys)
        mod = pg.KMOD_SHIFT if rnd.random() < 0.15 else 0
        key(app, k, mod, wait=rnd.choice((0.02, 0.1, 0.25)))
        if g.world.state != "playing":
            break
    frames(app, 2.0)


def test_pause_resume_and_settings_from_pause(app):
    g = _start_game(app)
    key(app, pg.K_ESCAPE)
    frames(app, 0.3)
    assert top_name(app) == "PauseScene"
    t = g.world.time
    frames(app, 0.5)
    assert g.world.time == t                      # frozen while paused
    pause = app.scenes.top
    pause.settings()
    frames(app, 0.3)
    assert top_name(app) == "SettingsScene"
    key(app, pg.K_ESCAPE)
    frames(app, 0.3)
    assert top_name(app) == "PauseScene"
    key(app, pg.K_ESCAPE)
    frames(app, 0.3)
    assert app.scenes.top is g


def test_win_flow_saves_progress_and_shows_win(app):
    g = _start_game(app)
    w = g.world
    w.eaten = w.needed
    w._become_full()
    ex = w.exit_cell
    for d, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
        n = (ex[0] - dx, ex[1] - dy)
        if n in w.level.pads:
            w.frog.cell = n
            w.request_move(d)
            break
    frames(app, 2.0)
    assert top_name(app) == "WinScene"
    prog = app.profile.diff("ezzz")
    assert prog.record("1-1").completed and prog.is_unlocked("1-2")
    assert save.load().profile.diff("ezzz").record("1-1").stars >= 1
    # "Next" -> 1-2 is not built yet -> level select
    app.scenes.top.next()
    frames(app, 0.5)
    assert top_name(app) == "LevelSelectScene"


def test_lose_flow_and_restart(app):
    g = _start_game(app)
    w = g.world
    w.hearts = 1
    c = next(c for c in sorted(w.level.pads) if w.level.is_water((c[0] + 1, c[1])))
    w.frog.cell = c
    w.request_move(1)
    frames(app, 2.5)
    assert top_name(app) == "LoseScene"
    app.scenes.top.restart()
    frames(app, 0.5)
    assert top_name(app) == "GameScene" and app.scenes.top is not g

"""Touch controls: gesture recognition, superjump arming, touch-mouse filtering."""
import pygame as pg
import pytest

from jebik import config, save
from jebik.game.gestures import Circle, TouchPad, swipe_direction, to_logical

DT = 1 / 60
MIN = config.TOUCH_SWIPE_MIN_DIST


def pad() -> TouchPad:
    return TouchPad(Circle((100, 980), 60), Circle((1820, 980), 60))


# ---------------------------------------------------------------- pure logic
def test_swipe_direction():
    assert swipe_direction(0, -80) == 0
    assert swipe_direction(80, 10) == 1
    assert swipe_direction(-5, 90) == 2
    assert swipe_direction(-90, 30) == 3


def test_to_logical_letterbox():
    assert to_logical(0.5, 0.5, (1920, 1080)) == (960, 540)
    # 4:3 window: 1920x1080 is letterboxed with bars top and bottom
    assert to_logical(0.0, 0.5, (1440, 1080)) == (0, 540)
    x, y = to_logical(1.0, 0.0, (1440, 1080))
    assert x == 1919 and y == 0          # clamped into the bars


@pytest.mark.parametrize("dx,dy,d", [(0, -1, 0), (1, 0, 1), (0, 1, 2), (-1, 0, 3)])
def test_swipe_moves(dx, dy, d):
    p = pad()
    assert p.down(1, (900, 500), 0.0) == []
    assert p.motion(1, (900 + dx * 20, 500 + dy * 20), 0.05) == []      # not far enough
    acts = p.motion(1, (900 + dx * (MIN + 5), 500 + dy * (MIN + 5)), 0.1)
    assert acts == [("move", d, False)]
    assert p.up(1, (900 + dx * (MIN + 5), 500 + dy * (MIN + 5)), 0.15) == []   # no extra tongue


def test_swipe_on_release_and_chaining():
    p = pad()
    p.down(1, (900, 500), 0.0)
    assert p.up(1, (900 + MIN + 10, 500), 0.1) == [("move", 1, False)]
    p.down(2, (900, 500), 1.0)
    assert p.motion(2, (900, 500 - MIN - 1), 1.1) == [("move", 0, False)]
    assert p.motion(2, (900 + MIN + 1, 500 - MIN - 1), 1.2) == [("move", 1, False)]


def test_slow_drag_is_neither_swipe_nor_tap():
    p = pad()
    p.down(1, (900, 500), 0.0)
    assert p.motion(1, (900 + MIN + 10, 500), config.TOUCH_SWIPE_MAX_TIME + 0.2) == []
    assert p.up(1, (900 + MIN + 12, 500), config.TOUCH_SWIPE_MAX_TIME + 0.3) == []


def test_tap_is_tongue():
    p = pad()
    p.down(1, (900, 500), 0.0)
    assert p.up(1, (905, 503), 0.1) == [("tongue",)]
    p.down(2, (900, 500), 1.0)                       # a long press is not a tap
    assert p.up(2, (900, 500), 1.0 + config.TOUCH_TAP_MAX_TIME + 0.1) == []


def test_buttons_pause_and_superjump_arming():
    p = pad()
    assert p.down(1, (100, 980), 0.0) == [("pause",)]
    assert p.up(1, (100, 980), 0.05) == []               # not a tongue tap
    assert p.down(2, (1820, 990), 1.0) == [("arm", True)]
    assert p.super_armed
    p.up(2, (1820, 990), 1.05)
    p.down(3, (900, 500), 2.0)
    assert p.up(3, (900 - MIN - 5, 500), 2.1) == [("move", 3, True)]
    assert not p.super_armed                             # one superjump per arming
    p.down(4, (900, 500), 3.0)
    assert p.up(4, (900 - MIN - 5, 500), 3.1) == [("move", 3, False)]
    # tapping the button again disarms
    p.down(5, (1820, 980), 4.0)
    assert p.down(6, (1820, 980), 4.1) == [("arm", False)]


def test_touch_setting_is_cleaned():
    assert save._clean_settings({"touch": "on"})["touch"] == "on"
    assert save._clean_settings({"touch": "maybe"})["touch"] == "auto"


# ---------------------------------------------------------------- through the app
@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik.app import App
    return App()


def finger(kind, fid, x, y):
    w, h = config.SCREEN_W, config.SCREEN_H
    return pg.event.Event(kind, finger_id=fid, touch_id=0, x=x / w, y=y / h, dx=0.0, dy=0.0)


def frames(app, n, events=()):
    for i in range(n):
        app.frame(DT, list(events) if i == 0 else [])


def test_touch_mouse_ignored_and_fingers_click(app):
    from jebik.ui.touch import TOUCH_MOUSEID, is_touch_mouse
    frames(app, 20)
    scene = app.scenes.top
    assert type(scene).__name__ == "ProfileScene"
    fake = pg.event.Event(pg.MOUSEBUTTONDOWN, pos=(5, 5), button=1, touch=True, which=TOUCH_MOUSEID)
    assert is_touch_mouse(fake)
    assert is_touch_mouse(pg.event.Event(pg.MOUSEMOTION, pos=(1, 1), which=TOUCH_MOUSEID))
    assert not is_touch_mouse(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=(5, 5), button=1, touch=False,
                                             which=0))
    # a synthesized mouse press never reaches the scene
    seen = []
    orig = scene.handle
    scene.handle = lambda e: (seen.append(e.type), orig(e))
    frames(app, 1, [fake])
    assert pg.MOUSEBUTTONDOWN not in seen
    # ... but a finger tap does, converted to a left click at logical coords
    frames(app, 1, [finger(pg.FINGERDOWN, 1, 960, 540)])
    assert pg.MOUSEBUTTONDOWN in seen and app.touch_seen
    frames(app, 1, [finger(pg.FINGERUP, 1, 960, 540)])
    assert pg.MOUSEBUTTONUP in seen


def test_game_touch_controls(app):
    from jebik.scenes.game_scene import GameScene
    from jebik.scenes.touch_hud import PAUSE_CENTER, SUPER_CENTER
    app.save.create_profile("Кыця")
    app.settings["touch"] = "off"
    game = GameScene(app, "1-1", seed=7)
    app.scenes.push(game, fade=False)
    assert not game.touch_native
    app.settings["touch"] = "auto"
    assert not game.touch_native                  # no finger seen yet
    for e in game.world.enemies:
        e.retreat = 1e9
    frames(app, 30)
    f = game.world.frog
    start = f.cell
    x, y = 960, 600
    # arm superjump, swipe right -> the frog lands two cells to the right
    frames(app, 1, [finger(pg.FINGERDOWN, 1, *SUPER_CENTER)])
    assert app.touch_controls and game.touch_native and game.touch.super_armed
    frames(app, 1, [finger(pg.FINGERUP, 1, *SUPER_CENTER)])
    frames(app, 2, [finger(pg.FINGERDOWN, 2, x, y)])
    frames(app, 40, [finger(pg.FINGERUP, 2, x + MIN + 20, y)])
    assert not game.touch.super_armed
    assert f.cell == (start[0] + 2, start[1]) and f.super_cd > 0
    # tap: tongue out in the facing direction
    frames(app, 1, [finger(pg.FINGERDOWN, 3, x, y)])
    frames(app, 2, [finger(pg.FINGERUP, 3, x, y)])
    assert f.tongue is not None or f.tongue_cd > 0
    # pause button
    frames(app, 40)
    frames(app, 1, [finger(pg.FINGERDOWN, 4, *PAUSE_CENTER)])
    assert type(app.scenes.top).__name__ == "PauseScene"

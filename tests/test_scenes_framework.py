"""Scenes of the framework: splash, cutscenes, TOBI restart, records, all worlds render."""
import pygame as pg
import pytest

from jebik import config, i18n, story
from jebik.game.rules import TOBI

DT = 1 / 60


def frames(app, seconds, events=()):
    events = list(events)
    for i in range(max(1, int(seconds / DT))):
        app.frame(DT, events if i == 0 else [])


def top_name(app):
    return type(app.scenes.top).__name__


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik.app import App
    return App()


@pytest.fixture
def splash_app(tmp_path, monkeypatch):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik.app import App
    return App(splash=True)


def _menu(app, name="P"):
    from jebik.scenes.main_menu import MainMenuScene
    if not app.save.find(name):
        app.save.create_profile(name)
    app.scenes.reset(MainMenuScene(app), fade=False)


# ---------------------------------------------------------------- splash
def test_splash_is_first_and_times_out(splash_app):
    assert top_name(splash_app) == "SplashScene"
    frames(splash_app, config.STUDIO_TIME - 0.3)
    assert top_name(splash_app) == "SplashScene"
    frames(splash_app, 0.6)
    assert top_name(splash_app) == "ProfileScene"


@pytest.mark.parametrize("event", [
    pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0, unicode=" ", scancode=0),
    pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(500, 500)),
    pg.event.Event(pg.FINGERDOWN, finger_id=1, touch_id=0, x=0.5, y=0.5, dx=0.0, dy=0.0),
])
def test_splash_skips_on_key_click_or_tap(splash_app, event):
    frames(splash_app, 0.5)
    frames(splash_app, DT, [event])
    frames(splash_app, 0.1)
    assert top_name(splash_app) == "ProfileScene"


def test_intro_sound_prefers_custom_file(splash_app, tmp_path, monkeypatch):
    audio = splash_app.audio
    assert audio.intro_path().name == config.INTRO_FANFARE
    custom = tmp_path / "intro_custom.ogg"
    custom.write_bytes(b"x")
    monkeypatch.setattr(config, "AUDIO_DIR", tmp_path)
    assert audio.intro_path() == custom


def test_world_sounds_load_lazily(app, tmp_path, monkeypatch):
    import shutil
    audio = app.audio
    if not audio.enabled:
        pytest.skip("no mixer")
    (tmp_path / "earth" / "audio").mkdir(parents=True)
    shutil.copy(config.AUDIO_DIR / "sfx_tick.wav", tmp_path / "earth" / "audio" / "stomp.wav")
    monkeypatch.setattr(config, "WORLDS_DIR", tmp_path)
    audio.play("earth.stomp")
    audio.play("earth.missing")
    assert "earth.stomp" in audio.sounds and "earth.missing" in audio._missing


# ---------------------------------------------------------------- cutscenes
def test_story_before_first_levels_once(app):
    _menu(app)
    from jebik.scenes.flow import start_level
    start_level(app, "1-1")
    frames(app, 0.4)
    assert top_name(app) == "CutsceneScene"
    cut = app.scenes.top
    assert [c.text_key for c in cut.cards][:2] == ["story.intro.1", "story.intro.2"]
    for _ in range(12):                              # Enter: finish typing, next card...
        frames(app, DT, [pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0, unicode="", scancode=0)])
        frames(app, 0.35)
        if top_name(app) == "GameScene":
            break
    assert top_name(app) == "GameScene" and app.scenes.top.level_id == "1-1"
    _menu(app)
    start_level(app, "1-1")                          # seen: straight into the game
    frames(app, 0.4)
    assert top_name(app) == "GameScene"
    assert story.before_level(app.profile, "2-1")[1] == "story.earth"
    assert story.before_level(app.profile, "2-2") == ([], None)


def test_final_story_after_last_level_and_credits_dedication(app):
    _menu(app)
    cards, flag = story.after_level(app.profile, "3-4")
    assert flag == "story.final" and cards[-1].art == "credits"
    from jebik.scenes.cutscene import CutsceneScene
    scene = CutsceneScene(app, story.credits_cards(), on_done=lambda: None)
    texts = [t for t, _, _ in scene.credit_lines()]
    assert "для любимой кыци (=^・ω・^=)" in texts


# ---------------------------------------------------------------- TOBI restart
def test_tobi_hit_restarts_level_automatically(app):
    _menu(app)
    app.difficulty = TOBI
    from jebik.scenes.game_scene import GameScene
    g = GameScene(app, "1-1", seed=2)
    app.scenes.push(g, fade=False)
    frames(app, 0.2)
    assert g.world.time_left is not None
    g.world.hurt_frog()
    frames(app, config.TOBI_RESTART_DELAY + 0.5)
    assert top_name(app) == "GameScene" and app.scenes.top is not g


def test_tobi_timeout_shows_lose_panel(app):
    _menu(app)
    app.difficulty = TOBI
    from jebik.scenes.game_scene import GameScene
    g = GameScene(app, "1-1", seed=2)
    app.scenes.push(g, fade=False)
    g.world.time_left = 0.1
    frames(app, config.LOSE_DELAY + 0.6)
    assert top_name(app) == "LoseScene"


# ---------------------------------------------------------------- records / worlds
def test_records_scene_switches_level_and_difficulty(app):
    _menu(app)
    app.profile.record_result("ezzz", "1-1", 1234, 3, 40.0)
    from jebik.scenes.records import RecordsScene
    rs = RecordsScene(app)
    app.scenes.push(rs, fade=False)
    frames(app, 0.2)
    assert [r.name for r in rs.rows] == ["P"] and rs.rows[0].levels == 1      # total
    frames(app, DT, [pg.event.Event(pg.KEYDOWN, key=pg.K_RIGHT, mod=0, unicode="", scancode=0)])
    assert rs.rows[0].score == 1234
    frames(app, DT, [pg.event.Event(pg.KEYDOWN, key=pg.K_TAB, mod=0, unicode="", scancode=0)])
    assert rs.difficulty == TOBI and rs.rows == []
    frames(app, 0.1)


@pytest.mark.parametrize("level_id", ["1-1", "2-1", "3-1"])
def test_every_playable_level_runs_and_renders(app, level_id):
    _menu(app)
    from jebik.scenes.game_scene import GameScene
    g = GameScene(app, level_id, seed=4)
    app.scenes.push(g, fade=False)
    frames(app, 4.0)
    assert g.view.field_art.static().get_size() == (config.SCREEN_W, config.SCREEN_H)
    assert g.hud.theme.hud_bg == g.theme.hud_bg


def test_world_strings_are_merged_and_prefixed():
    from jebik.worlds import all_worlds
    for w in all_worlds():
        assert i18n.has(w.name_key) and i18n.has(f"{w.id}.exit_hint")
        assert all(k.startswith(w.id + ".") for k in w.strings)
    from jebik.worlds.base import WorldDef, Theme, register_world
    with pytest.raises(ValueError):
        register_world(WorldDef("zzz", 9, Theme((0, 0, 0), (0, 0, 0)), strings={"x.y": ("a", "b", "c")}))


def test_layout_cell_override_and_reserves():
    from conftest import make_level
    from jebik.scenes.layout import cell_size, field_rect, top_space
    rows = ["F" + "O" * 21] + ["O" * 22] * 13
    plain = make_level(rows)
    boss = make_level(rows, header="boss: test_boss @ 1 1\ncell: 50\ntop_reserve: 160")
    assert cell_size(boss) == 50 and cell_size(plain) <= config.MAX_CELL
    assert top_space(boss) == config.HUD_H + config.BOSS_PILL_RESERVE + 160
    r = field_rect(boss, 50)
    assert r.top >= top_space(boss) and r.bottom <= config.SCREEN_H

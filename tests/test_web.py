"""Browser build (pygbag) adaptations, exercised on desktop with ``paths.is_web`` faked."""
import json

import pygame as pg
import pytest

from jebik import paths, save, web

DT = 1 / 60


class FakeWindow:
    """Stands in for pygbag's ``platform.window``: localStorage + prompt()."""

    def __init__(self, answer=None):
        self.store: dict[str, str] = {}
        self.answer = answer
        self.asked: list[tuple[str, str]] = []
        outer = self

        class Storage:
            def getItem(self, k):
                return outer.store.get(k)

            def setItem(self, k, v):
                outer.store[k] = str(v)

            def removeItem(self, k):
                outer.store.pop(k, None)

        self.localStorage = Storage()

    def eval(self, source):
        assert source.isascii()                      # pygbag mangles non-ASCII sent to JS
        assert source.startswith("prompt(") and source.endswith(")")
        message, default = json.loads("[" + source[len("prompt("):-1] + "]")
        self.asked.append((message, default))
        return self.answer


@pytest.fixture
def browser(monkeypatch, tmp_path):
    """Pretend to run in the browser; the save folder must stay untouched."""
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    monkeypatch.setattr(paths, "is_web", lambda: True)
    win = FakeWindow()
    monkeypatch.setattr(web, "_window", lambda: win)
    return win


def test_desktop_is_not_web():
    assert not paths.is_web()
    wav = paths.resource_path("assets", "audio", "sfx_jump.wav")
    assert paths.audio_file(wav) == wav


def test_web_prefers_ogg_twin(browser, tmp_path):
    wav, ogg = tmp_path / "a.wav", tmp_path / "a.ogg"
    wav.write_bytes(b"x")
    assert paths.audio_file(wav) == wav             # no .ogg shipped: keep the wav
    ogg.write_bytes(b"x")
    assert paths.audio_file(wav) == ogg
    wav.unlink()
    assert paths.audio_file(tmp_path / "b.wav") == tmp_path / "b.ogg"


def test_web_save_roundtrip_uses_local_storage(browser, tmp_path):
    data = save.load()
    assert data.profiles == [] and data.path is None
    data.create_profile("Кыця")
    data.settings["lang"] = "en"
    assert data.save()
    assert list(tmp_path.iterdir()) == []            # nothing written to disk
    assert browser.store[web.KEY].isascii()
    raw = json.loads(browser.store[web.KEY])
    assert raw["current_profile"] == "Кыця"
    again = save.load()
    assert again.profile.name == "Кыця" and again.settings["lang"] == "en"


def test_web_corrupt_save_is_set_aside(browser):
    browser.store[web.KEY] = "{broken"
    data = save.load()
    assert data.profiles == []
    assert web.KEY not in browser.store and browser.store[web.KEY + ".corrupt"] == "{broken"


def test_web_helpers_degrade_without_browser():
    # desktop: no pygbag bridge -> quiet fallbacks
    assert web.read() is None
    assert web.write("x") is False
    assert web.ask_text("?") is None


def test_text_input_asks_with_browser_prompt(browser):
    from jebik.ui.widgets import TextInput
    got = []
    ti = TextInput((0, 0, 300, 90), "name...", 5, got.append, prompt="Ім'я?")
    browser.answer = "  Кыця-кыця  "
    ti.press((10, 10))
    assert browser.asked == [("Ім'я?", "")]
    assert ti.text == "Кыця-" and got == ["Кыця-"]         # trimmed, capped, submitted
    browser.answer = None                                   # cancelled: unchanged
    ti.press((10, 10))
    assert ti.text == "Кыця-" and got == ["Кыця-"]


@pytest.fixture
def app(browser):
    from jebik.app import App
    return App()


def frames(app, seconds, events=()):
    events = list(events)
    for i in range(max(1, int(seconds / DT))):
        app.frame(DT, events if i == 0 else [])


def test_web_profile_create_by_tap_and_settings_without_fullscreen(app, browser):
    from jebik.scenes.settings import SettingsScene
    frames(app, 0.3)
    assert type(app.scenes.top).__name__ == "ProfileScene"
    browser.answer = "Жабка"
    create = app.scenes.top.focus.widgets[1]                 # «Створити» with an empty name
    create.activate()
    frames(app, 0.5)
    assert type(app.scenes.top).__name__ == "MainMenuScene"
    assert json.loads(browser.store[web.KEY])["current_profile"] == "Жабка"
    app.set_fullscreen(True)                                 # a no-op in the browser
    from jebik.ui.widgets import Toggle
    toggles = [w for w in SettingsScene(app).focus.widgets if isinstance(w, Toggle)]
    assert len(toggles) == 1                                 # grid only, no fullscreen


def test_web_splash_uses_half_resolution_layers(app, monkeypatch, tmp_path):
    from jebik.art import splash_layers
    from jebik.scenes.splash import SplashScene
    splash_layers.bake(tmp_path / "baked", 0.5)
    monkeypatch.setattr(splash_layers, "BAKED_DIR", ())
    monkeypatch.setattr(splash_layers, "resource_path", lambda *p: tmp_path / "baked")
    sc = SplashScene(app)
    assert sc.k == 0.5 and sc.sky.get_size() == (960, 540)
    screen = pg.Surface((1920, 1080))
    for t in (0.1, 3.0, 6.5):
        sc.time = t
        sc.draw(screen)
    assert screen.get_at((960, 540))[:3] != (0, 0, 0)


@pytest.mark.parametrize("level_id", ["1-1", "2-1", "3-1", "3-4"])
def test_tile_cache_draws_the_same_frame(app, monkeypatch, level_id):
    from jebik.art import tile_cache
    from jebik.scenes.game_scene import GameScene
    app.save.create_profile("P")
    g = GameScene(app, level_id, seed=4)
    app.scenes.reset(g, fade=False)
    frames(app, 0.5)
    g.effects.rings.clear()
    plain, cached = pg.Surface((1920, 1080)), pg.Surface((1920, 1080))
    monkeypatch.setattr(tile_cache, "ENABLED", False)
    g.draw(plain)
    monkeypatch.setattr(tile_cache, "ENABLED", True)
    g.draw(cached)
    g.draw(cached)                                           # second frame: from the cache
    tc = g.view.tile_cache
    if level_id == "1-1":
        assert tc.off                      # bobbing lily pads: cache switched itself off
    else:
        assert tc.rebuilds == 1 and not tc.off
    assert pg.image.tobytes(plain, "RGB") == pg.image.tobytes(cached, "RGB")

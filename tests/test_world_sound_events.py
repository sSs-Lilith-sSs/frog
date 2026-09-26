"""The logic emits the events the world sounds hang on; the field plays them."""
from conftest import make_world

from jebik.art.field import FieldRenderer
from jebik.game.enemy import AIR, GROUND
from jebik.game.events import BOSS_TELL, Event
from jebik.worlds.water import config as wc
from jebik.worlds.water import pike as pk


def _kinds(w):
    return [e.kind for e in w.drain_events()]


def _until(w, cond, limit=8.0, dt=1 / 60):
    seen: list[str] = []
    t = 0.0
    while not cond() and t < limit:
        w.update(dt)
        seen += _kinds(w)
        t += dt
    assert cond(), "condition never met"
    return seen


def test_pike_announces_bubbles_and_lunge_and_leaps_over_the_frog():
    w = make_world(["OOOOO", "OF#P#", "OOOOO"], header="spawn: P=pike:hole", enemies=True)
    pike = w.enemies[0]
    seen = _until(w, lambda: pike.state == pk.BUBBLES)
    assert "water.pike_bubbles" in seen and pike.layer == GROUND
    seen = _until(w, lambda: pike.state == pk.LUNGE)
    assert "water.pike_lunge" in seen
    assert pike.layer == AIR                          # drawn above the frog it bites
    _until(w, lambda: pike.state == pk.COOLDOWN)
    assert pike.layer == GROUND


def test_heron_announces_shadow_and_strike():
    w = make_world(["OOOOO", "OOFOO", "OOOOO"], header="enemies: heron", enemies=True)
    heron = w.enemies[0]
    heron.timer = 0.1
    seen = _until(w, lambda: heron.state == "shadow")
    assert "water.heron_shadow" in seen
    seen = _until(w, lambda: heron.state == "strike", limit=wc.HERON_WARN + 0.5)
    assert "water.heron_strike" in seen


def test_whale_wave_and_gulp_are_announced():
    rows = ["O" * 12] * 7 + ["FOOOOOOOOOOO"]
    w = make_world(rows, flies_needed=6, header="boss: whale @ 6 4", enemies=True)
    whale = w.boss
    w.drain_events()
    whale.start_attack(w, "wave")
    assert "water.wave" in _until(w, lambda: whale.state == "wave")
    whale._set("swim", 99)
    whale.start_attack(w, "gulp")
    assert "water.gulp" in _until(w, lambda: whale.state == "gulp")


class Rec:
    def __init__(self):
        self.calls = []

    def play(self, name, volume=1.0):
        self.calls.append((name, volume))
        return True


class Tables(FieldRenderer):
    event_sounds = {"zz.boom": ("zz.boom", .5), "tile_warn": ("zz.crack", 1.0, .3)}
    tell_sounds = {"stomp": ("zz.snort", .8)}


def _tables():
    fr = Tables.__new__(Tables)                       # no level needed for the sound table
    fr.t, fr._sound_t = 0.0, {}
    return fr


def test_event_sounds_and_tells_map_to_sounds():
    fr, audio = _tables(), Rec()
    fr.event_sound(Event("zz.boom"), audio)
    fr.event_sound(Event(BOSS_TELL, value=("boar", "stomp")), audio)
    fr.event_sound(Event("zz.unknown"), audio)
    assert audio.calls == [("zz.boom", .5), ("zz.snort", .8)]


def test_min_gap_merges_simultaneous_events():
    fr, audio = _tables(), Rec()
    for _ in range(5):                                 # a stomp cracks five tiles at once
        fr.event_sound(Event("tile_warn", cell=(1, 1)), audio)
    assert audio.calls == [("zz.crack", 1.0)]
    fr.t += 0.31
    fr.event_sound(Event("tile_warn", cell=(2, 1)), audio)
    assert len(audio.calls) == 2


def test_audio_play_reports_missing_world_sounds(tmp_path, monkeypatch):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik.app import App
    audio = App().audio
    if not audio.enabled:
        assert audio.play("sky.boss_hit") is False
        return
    assert audio.play("sky.boss_hit") is True
    assert audio.play("water.no_such_sound") is False
    assert audio.play("jump") is True

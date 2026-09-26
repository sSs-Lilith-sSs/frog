"""Regression tests for bugs found by the final QA pass (tools/qa_soak.py)."""
import pygame as pg
import pytest

from jebik import progression, save
from jebik.game.rules import EZZZ, TOBI
from jebik.scenes.overlays import fmt_time

DT = 1 / 60


def test_save_with_infinite_or_nan_numbers_loads(tmp_path):
    # json.loads turns 1e999 into inf and NaN into nan: int(inf) used to crash the start
    path = tmp_path / "save.json"
    path.write_text('{"settings": {"music_volume": NaN, "sfx_volume": 1e999},'
                    ' "profiles": [{"name": "Кыця", "created": 1e999, "progress": {"ezzz": {"levels":'
                    ' {"1-1": {"stars": 1e999, "best_score": NaN, "best_time": 1e999, "completed": true,'
                    ' "runs": [{"score": 1e999, "time": 1e999}, {"score": 5, "time": 12.5, "date": NaN}]}}}}}],'
                    ' "current_profile": "Кыця"}', encoding="utf-8")
    data = save.load(path)
    rec = data.profile.diff("ezzz").record("1-1")
    assert rec.completed and rec.stars == 0 and rec.best_score == 0 and rec.best_time is None
    assert [(r.score, r.time, r.date) for r in rec.runs] == [(5, 12.5, 0.0)]
    assert fmt_time(rec.runs[0].time)
    assert all(0.0 <= data.settings[k] <= 1.0 for k in ("music_volume", "sfx_volume"))
    assert data.save()


# ---------------------------------------------------------------- app-level

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik.app import App
    a = App(splash=False)
    a.set_lang("ru")
    return a


def _frames(app, n=10):
    for _ in range(n):
        app.frame(DT, [])


def test_switching_to_a_new_profile_leaves_tobi(app):
    # TOBI PIZDA chosen by an unlocked profile used to stay on for a new one: every level locked
    from jebik.scenes.profile import ProfileScene
    old = app.save.create_profile("Кыця")
    old.mark(progression.TOBI_FLAG)
    app.difficulty = TOBI
    ps = ProfileScene(app, from_menu=True)
    app.scenes.reset(ps, fade=False)
    ps._start_create()
    ps._create("Новая")
    assert app.difficulty == EZZZ
    assert progression.is_unlocked(app.profile, app.difficulty, "1-1")
    ps = ProfileScene(app, from_menu=True)
    app.scenes.reset(ps, fade=False)
    app.difficulty = TOBI
    ps._select("Кыця")                        # a profile that has TOBI keeps the choice
    assert app.difficulty == TOBI


def test_long_wide_profile_name_fits_its_boxes(app, monkeypatch):
    from jebik.art import common
    from jebik.scenes import profile as profile_mod
    from jebik.ui import widgets
    wide = "Ш" * save.MAX_NAME_LEN
    drawn = []
    orig = common.draw_text

    def rec(surf, text, *a, **k):
        r = orig(surf, text, *a, **k)
        drawn.append((text, pg.Rect(r)))
        return r
    monkeypatch.setattr(widgets, "draw_text", rec)
    monkeypatch.setattr(profile_mod, "draw_text", rec)
    app.save.create_profile(wide)
    ps = profile_mod.ProfileScene(app, from_menu=True)
    app.scenes.reset(ps, fade=False)
    ps._start_create()
    ps.input.text = wide
    _frames(app, 2)
    box = ps.input.rect
    assert any(t == wide and box.contains(r) for t, r in drawn)
    drawn.clear()
    ps._ask_delete(wide)
    _frames(app, 2)
    q = next(r for t, r in drawn if wide in t and t != wide)
    assert ps.panel.contains(q)


# ---------------------------------------------------------------- boar stumps
def test_boar_hit_uses_up_only_the_stump_it_crashed_into():
    # a missed stump still waiting to grow back (frog standing on it) was wiped by the next
    # hit, so 3 stumps could run out before 3 hits: the boar became unbeatable
    from conftest import make_world
    from jebik.game.tiles import OBSTACLE
    from jebik.worlds.earth import boar as bl
    rows = ["OOOOOOOOOOOO", "OOOOOOOOOOOO", "OOXOOOOOOOOO", "OOOOOOOOOOOO",
            "OOOOOOOOOOOO", "OOOOOOOOOXOO", "OOOOOOOOOOOO", "OOOOOOFOOOOO"]
    w = make_world(rows, flies_needed=3, header="boss: boar @ 8 2 hp=3", enemies=True)
    w.frog.invuln = 999.0
    b = w.boss

    def crash(pos, d):
        b.pos, b.state, b.timer, b.dir = (float(pos[0]), float(pos[1])), bl.TELL, 0.01, d
        for _ in range(300):
            w.update(1 / 60)
            if b.state == bl.STUN:
                return
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = (6, 7)
    crash((8, 2), (-1, 0))                     # stump (2, 2) breaks, the tongue misses
    assert b.stun_kind == "stump" and b.broken == [(2, 2)]
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = (2, 2)     # ...and the frog sits there
    crash((9, 1), (0, 1))                      # into the stump at (9, 5)
    assert b.stun_kind == "stump" and w.tiles.tile((9, 5)).kind != OBSTACLE
    assert b.take_hit(w) and b.hp == 2
    assert b.broken == [(2, 2)]                # still waiting to grow back
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = (6, 7)
    b.stunned = b.window = 0.0
    b.state, b.timer = bl.THINK, 999.0
    w.update(1 / 60)
    assert w.tiles.tile((2, 2)).kind == OBSTACLE


# ---------------------------------------------------------------- exit vs. a fly on it
def test_landing_on_the_exit_wins_even_with_a_fly_resting_there():
    # TOBI PIZDA: a fly sitting on the lotus used to be eaten first -> overeat -> restart
    from conftest import make_level, run
    from jebik.game.grid import RIGHT
    from jebik.game.rules import WON, rules_for
    from jebik.game.world import World
    lv = make_level(["FOO"], flies_needed=1)
    w = World(lv, rules=rules_for(TOBI, lv), seed=1, auto_spawn=False, spawn_enemies=False)
    w.eaten = 1
    w._become_full()
    w.exit_cell = (1, 0)
    w.flies.spawn_at("fly", (1, 0), rest=5.0)
    w.request_move(RIGHT)
    run(w, 0.3)
    assert w.state == WON and w.overeats == 0 and not w.damaged

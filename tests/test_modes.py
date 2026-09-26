"""TOBI PIZDA rules, unlock order / progression and the records tables."""
import pytest
from conftest import make_world, run

from jebik import config, progression, records, save
from jebik.game import events as ev
from jebik.game.grid import RIGHT
from jebik.game.rules import EZZZ, TOBI, rules_for
from jebik.worlds import catalog


def tobi_world(rows, needed=5, limit=30.0, enemies=False, header=""):
    w = make_world(rows, flies_needed=needed, enemies=enemies, header=header + f"\ntobi_time: {limit}")
    w.rules = rules_for(TOBI, w.level)
    w.hearts = w.rules.hearts
    w.time_left = w.rules.time_limit
    return w


# ---------------------------------------------------------------- TOBI PIZDA
def test_tobi_rules_from_level():
    w = tobi_world(["FO"], limit=42)
    assert w.rules.one_hit and not w.rules.uses_hearts
    assert w.time_left == 42 and w.rules.gold_time == config.TOBI_GOLD_BONUS
    assert rules_for(EZZZ).time_limit is None and rules_for(EZZZ).uses_hearts


def test_tobi_one_hit_loses_at_once():
    w = tobi_world(["FOO"])
    assert w.hurt_frog()
    assert w.state == "lost" and w.lose_reason == "hit"
    assert any(e.kind == ev.LOSE and e.value == "hit" for e in w.drain_events())


def test_tobi_fall_and_overeat_lose_at_once():
    w = tobi_world(["F#"])
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + 0.02)
    assert w.state == "lost" and w.lose_reason == "fall" and w.frog.state == "splash"
    w = tobi_world(["FO"], needed=1)
    w.flies.spawn_at("dragon", (1, 0), rest=9)       # +2 > 1
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + 0.02)
    assert w.state == "lost" and w.lose_reason == "overeat"


def test_tobi_timer_runs_out():
    w = tobi_world(["FO"], limit=2.0)
    run(w, 1.0)
    assert w.state == "playing" and w.time_left == pytest.approx(1.0, abs=0.05)
    run(w, 1.1)
    assert w.state == "lost" and w.lose_reason == "timeout" and w.time_left == 0


def test_tobi_golden_fly_adds_ten_seconds():
    w = tobi_world(["FO"], limit=30)
    w.flies.spawn_at("gold", (1, 0), rest=9)
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + 0.02)
    assert w.time_left == pytest.approx(30 + config.TOBI_GOLD_BONUS - config.HOP_TIME - 0.02, abs=0.05)
    assert w.hearts == 1
    assert any(e.kind == ev.TIME_BONUS for e in w.drain_events())


def test_tobi_win_scores_time_left():
    w = tobi_world(["FOO"], needed=1, limit=50)
    w.eaten = 1
    w._become_full()
    w.exit_cell = (1, 0)
    w.request_move(RIGHT)
    run(w, 0.3)
    res = w.result
    assert res and res.difficulty == TOBI and res.time_left > 49
    assert res.score == config.SCORE_PER_FLY + int(res.time_left * config.SCORE_PER_SECOND_LEFT) \
        + config.SCORE_NO_DAMAGE


def test_ezzz_keeps_hearts():
    w = make_world(["FOO"])
    w.hurt_frog()
    assert w.state == "playing" and w.hearts == config.START_HEARTS - 1


# ---------------------------------------------------------------- progression
@pytest.fixture
def profile(tmp_path):
    return save.load(tmp_path / "s.json").create_profile("P")


# (written so they keep passing when world packages mark more levels playable)
def test_catalog_has_all_twelve_levels_and_placeholders():
    assert len(catalog.ALL_LEVELS) == 12
    playable = catalog.playable_levels()
    assert {"1-1", "2-1", "3-1"} <= set(playable) <= set(catalog.discovered())
    assert playable == sorted(playable, key=catalog.ALL_LEVELS.index)
    for lid in catalog.discovered():
        lv = catalog.load_level(lid)
        assert lv.id == lid and lv.frog_start in lv.pads
    for a, b in zip(playable, playable[1:]):
        assert catalog.next_level(a) == b                  # unbuilt levels are skipped
    assert catalog.next_level(playable[-1]) is None


def test_unlock_order(profile):
    playable = catalog.playable_levels()
    state = lambda lid: progression.level_state(profile, EZZZ, lid)   # noqa: E731
    for lid in catalog.ALL_LEVELS:
        if lid not in playable:
            assert state(lid) == progression.SOON
    for i, lid in enumerate(playable):
        assert state(lid) == progression.OPEN
        assert all(state(later) == progression.LOCKED for later in playable[i + 1:])
        assert progression.next_level_to_play(profile, EZZZ) == lid
        profile.record_result(EZZZ, lid, 900, 1, 60)
    assert progression.next_level_to_play(profile, EZZZ) is None
    assert progression.world_complete(profile, EZZZ, 1)


def test_tobi_unlocks_after_all_ezzz_and_is_sticky(profile, monkeypatch):
    shipped = catalog.ALL_LEVELS[:-1]    # pretend the last level ships later
    monkeypatch.setattr(catalog, "is_playable", lambda lid: lid in shipped)
    monkeypatch.setattr(catalog, "playable_levels", lambda: list(shipped))
    assert not progression.tobi_unlocked(profile)
    assert not progression.is_unlocked(profile, TOBI, "1-1")
    for lid in catalog.playable_levels():
        profile.record_result(EZZZ, lid, 900, 1, 60)
    assert progression.refresh_unlocks(profile) and progression.tobi_unlocked(profile)
    assert progression.is_unlocked(profile, TOBI, "1-1")
    second = catalog.playable_levels()[1]
    assert not progression.is_unlocked(profile, TOBI, second)     # TOBI has its own progress
    monkeypatch.setattr(catalog, "is_playable", lambda lid: lid in catalog.ALL_LEVELS)
    monkeypatch.setattr(catalog, "playable_levels", lambda: list(catalog.ALL_LEVELS))
    assert not progression.ezzz_finished(profile)                 # new levels shipped...
    assert progression.tobi_unlocked(profile)                     # ...TOBI stays open


def test_new_levels_slot_into_the_chain(profile, monkeypatch):
    monkeypatch.setattr(catalog, "is_playable", lambda lid: lid in ("1-1", "2-1", "3-1"))
    profile.record_result(EZZZ, "1-1", 900, 1, 60)
    assert progression.is_unlocked(profile, EZZZ, "2-1")          # 1-2..1-4 not built
    profile.record_result(EZZZ, "2-1", 900, 1, 60)
    monkeypatch.setattr(catalog, "is_playable", lambda lid: lid in catalog.ALL_LEVELS)
    assert progression.is_unlocked(profile, EZZZ, "1-2")
    assert not progression.is_unlocked(profile, EZZZ, "1-3")
    assert progression.next_level_to_play(profile, EZZZ) == "1-2"


# ---------------------------------------------------------------- records
def test_records_level_top_ordering_and_limit(tmp_path):
    data = save.load(tmp_path / "s.json")
    a, b = data.create_profile("A"), data.create_profile("B")
    a.record_result(EZZZ, "1-1", 1000, 2, 50.0, date=1)
    b.record_result(EZZZ, "1-1", 1000, 3, 40.0, date=2)    # same score, faster
    b.record_result(EZZZ, "1-1", 1200, 1, 90.0, date=3)
    a.record_result(EZZZ, "1-1", 1000, 2, 40.0, date=4)    # same score + time, later
    rows = records.level_top(data, EZZZ, "1-1")
    assert [(r.name, r.score, r.time) for r in rows] == [
        ("B", 1200, 90.0), ("B", 1000, 40.0), ("A", 1000, 40.0), ("A", 1000, 50.0)]
    for i in range(15):
        a.record_result(EZZZ, "1-1", 100 + i, 1, 60.0)
    assert len(a.diff(EZZZ).record("1-1").runs) == config.RECORDS_KEEP
    assert len(records.level_top(data, EZZZ, "1-1")) == config.RECORDS_KEEP
    assert records.level_top(data, TOBI, "1-1") == []            # per difficulty


def test_records_total_per_profile(tmp_path):
    data = save.load(tmp_path / "s.json")
    a, b = data.create_profile("A"), data.create_profile("B")
    a.record_result(EZZZ, "1-1", 1000, 2, 50.0)
    a.record_result(EZZZ, "2-1", 800, 3, 70.0)
    b.record_result(EZZZ, "1-1", 1500, 3, 30.0)
    rows = records.total_top(data, EZZZ)
    assert [(r.name, r.score, r.levels, r.stars) for r in rows] == [("A", 1800, 2, 5), ("B", 1500, 1, 3)]


def test_runs_survive_save_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    data = save.load(path)
    p = data.create_profile("A")
    p.record_result(TOBI, "1-1", 999, 3, 12.5, date=7)
    p.mark("story.intro")
    data.save()
    back = save.load(path).profile
    assert back.diff(TOBI).record("1-1").runs[0].score == 999 and back.has("story.intro")

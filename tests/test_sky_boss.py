"""Boss «Ісус»: halo boomerang caught by the tongue -> SASAT hit, beams, rebuild, exit rule."""
from conftest import make_world, run

from jebik.game import events as ev
from jebik.game.grid import DIRS, manhattan, step
from jebik.worlds.sky import config as sc

ROWS = ["OOOOOOOOO", "OOOOOOOOO", "OOO#OOOOO", "OOOOFOOOO", "OOOOOOO#O", "OOOOOOOOO", "OO#OOOOOO"]
HEADER = "boss: jesus hp=3\ntop_reserve: 180\ncell: 50"


def boss_world(rows=ROWS, needed=5):
    w = make_world(rows, needed, enemies=True, header=HEADER)
    boss = w.boss
    boss.timer = 99.0                         # attacks are started by hand in tests
    return w, boss


def _collect(w, seconds, dt=1 / 60):
    out = []
    for _ in range(int(round(seconds / dt))):
        w.update(dt)
        out += w.drain_events()
    return out


def test_boss_basics():
    w, boss = boss_world()
    assert boss.kind == "jesus" and boss.hp == 3
    assert boss.name_key == "sky.boss" and boss.hit_text_key == "sky.sasat"
    assert boss.pos[1] < -1                   # above the field, on his cloud
    assert not boss.hurts(w, boss.pos) and boss.occupied() == set()


def test_catching_the_halo_bonks_him():
    w, boss = boss_world()
    boss._begin_halo(w)
    target = (round(boss.halo_to[0]), round(boss.halo_to[1]))
    d = next(i for i in range(4) if step(w.frog.cell, i, 2) == target)
    assert boss.vulnerable                    # the pill glows while the halo is out
    run(w, sc.JESUS_HALO_OUT + 0.1)
    assert boss.halo_phase == "hover"
    w.request_tongue(d)
    got = _collect(w, 0.3)
    assert boss.halo_phase == "bonk"
    assert any(e.kind == "sky.halo_caught" for e in got)
    got = _collect(w, sc.JESUS_HALO_BONK + 0.2)
    assert boss.hp == 2 and boss.state == "hit"
    hits = [e for e in got if e.kind == ev.BOSS_HIT]
    assert hits and hits[0].value == ("jesus", 2)


def test_halo_that_is_not_caught_just_comes_back():
    w, boss = boss_world()
    boss._begin_halo(w)
    run(w, sc.JESUS_HALO_OUT + sc.JESUS_HALO_HOVER + sc.JESUS_HALO_BACK + 0.2)
    assert boss.halo_phase == "home" and boss.hp == 3 and w.hearts == 3


def test_tongue_misses_when_halo_is_home():
    w, boss = boss_world()
    for d in range(4):
        assert boss.tongue_hit(w, [step(w.frog.cell, d, k) for k in (1, 2)]) is None


def test_beam_row_glows_then_burns():
    w, boss = boss_world()
    w.rng.seed(2)
    boss._begin_beams(w)
    frog = w.frog.cell
    assert frog in boss.beam_cells
    tg = boss.telegraphs()
    assert tg and all(t.style == "line" for t in tg)
    run(w, sc.JESUS_BEAM_WARN - 0.1)
    assert w.hearts == 3
    run(w, 0.3)
    assert w.hearts == 2


def test_multiply_spawns_10_to_15_flies():
    w, boss = boss_world()
    before = len(w.flies.flies)
    boss._multiply(w)
    n = len(w.flies.flies) - before
    assert sc.JESUS_MULTIPLY[0] <= n <= sc.JESUS_MULTIPLY[1]
    assert all(manhattan(f.cell, w.frog.cell) > 1 for f in w.flies.flies)


def test_rebuild_never_under_the_frog():
    w, boss = boss_world()
    for seed in range(30):
        w.rng.seed(seed)
        boss._begin_rebuild(w)
        near = {w.frog.cell} | {(w.frog.cell[0] + dx, w.frog.cell[1] + dy) for dx, dy in DIRS}
        assert not near & set(boss.vanish)
        assert all(not w.tiles.standable(c) for c in boss.appear)
    vanish, appear = boss.vanish, boss.appear
    run(w, sc.JESUS_REBUILD_WARN + 0.1)
    assert all(not w.tiles.standable(c) for c in vanish)
    assert all(w.tiles.standable(c) for c in appear)
    assert w.hearts == 3


def test_exit_needs_exact_flies_and_defeated_boss():
    w, boss = boss_world(needed=2)
    w.eaten = 1
    fly = w.flies.spawn_at("fly", step(w.frog.cell, 1), rest=5.0)
    w.request_move(1)
    run(w, 0.3)
    assert w.full and fly not in w.flies.flies
    assert w.exit_cell is None                # boss still up -> no rainbow
    for _ in range(3):
        boss.open_window(1.0)
        assert boss.take_hit(w)
    assert boss.defeated and w.exit_cell is not None
    run(w, 0.5)
    assert boss.state == "sad" and boss.telegraphs() == []


def test_defeat_first_then_flies():
    w, boss = boss_world(needed=1)
    for _ in range(3):
        boss.open_window(1.0)
        boss.take_hit(w)
    assert boss.defeated and w.exit_cell is None
    w.flies.spawn_at("fly", step(w.frog.cell, 1), rest=5.0)
    w.request_move(1)
    run(w, 0.3)
    assert w.exit_cell is not None


def test_attack_loop_runs_without_errors():
    w, boss = boss_world()
    boss.timer = 0.5
    kinds = set()
    for _ in range(60 * 40):
        w.update(1 / 60)
        for e in w.drain_events():
            if e.kind == ev.BOSS_TELL:
                kinds.add(e.value[1])
    assert "halo" in kinds and len(kinds) >= 3

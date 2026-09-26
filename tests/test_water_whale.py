"""Water boss Кит: attack zones, vulnerability window on its back, 1-4 exit rule."""
from conftest import make_world, run

from jebik import config
from jebik.game import frog as fs
from jebik.game.grid import DOWN, LEFT, RIGHT, UP
from jebik.game.world import World
from jebik.worlds import catalog
from jebik.worlds.water import config as wc
from jebik.worlds.water import whale as wh

H = config.START_HEARTS
FIELD = ["O" * 12] * 7 + ["FOOOOOOOOOOO"]


def _world(rows=FIELD):
    w = make_world(rows, flies_needed=6, header="boss: whale @ 6 4", enemies=True)
    return w, w.boss


def _put(w, cell, facing=RIGHT):
    f = w.frog
    f.cell = f.hop_from = f.hop_to = f.last_safe = cell
    f.facing = facing


def test_whale_starts_submerged_and_calm():
    w, whale = _world()
    assert isinstance(whale, wh.Whale) and whale.layer == "under" and not whale.surfaced
    run(w, wc.WHALE_START_DELAY - 0.1)
    assert whale.attacks == [] and w.hearts == H


def test_whale_attacks_on_its_own_and_surfaces_regularly():
    w, whale = _world()
    for _ in range(40):
        w.hearts = 99                                  # keep the level running
        run(w, 1.0)
    assert len(whale.attacks) >= 6
    runs, gap = 0, 0
    for a in whale.attacks:
        gap = 0 if a == "surface" else gap + 1
        runs = max(runs, gap)
    assert "surface" in whale.attacks and runs <= wc.WHALE_SURFACE_EVERY


def test_surfacing_zone_hits_and_sinks_pads():
    w, whale = _world()
    _put(w, (5, 3))
    whale.start_attack(w, "surface")
    tg = whale.telegraphs()[0]
    zone = {(x, y) for x in range(4, 7) for y in range(2, 5)}
    assert tg.style == "zone" and set(tg.cells) == zone and whale.blowhole == (5, 3)
    run(w, wc.WHALE_SURFACE_WARN - 0.05)
    assert w.hearts == H and not whale.surfaced
    run(w, 0.1)
    assert whale.surfaced and whale.vulnerable and w.hearts == H - 1
    assert all(w.tiles.is_hole(c) for c in zone)       # pads sank ...
    assert all(w.can_stand(c) for c in zone)           # ... but the back holds
    assert w.frog.state != fs.SPLASH
    run(w, wc.WHALE_BACK_TIME + wc.WHALE_DIVE_WARN + 0.1)
    assert not whale.surfaced
    run(w, wc.WHALE_SINK_TIME)
    assert not any(w.tiles.is_hole(c) for c in zone)   # pads are back


def test_whale_hit_only_from_its_back_inside_the_window():
    w, whale = _world()
    _put(w, (1, 3))
    assert whale.tongue_hit(w, [(2, 3), (3, 3)]) is None
    _put(w, (5, 3))
    whale.start_attack(w, "surface")
    _put(w, (1, 3))                                    # outside the zone
    run(w, wc.WHALE_SURFACE_WARN + 0.05)
    assert whale.surfaced and w.hearts == H
    _put(w, (3, 3))                                    # blowhole in reach, but not on the back
    w.request_tongue(RIGHT)
    run(w, 0.3)
    assert whale.hp == 3
    w.request_move(RIGHT)                              # onto the back (a sunk pad)
    run(w, 0.25)
    assert w.frog.cell == (4, 3) and w.frog.state == fs.IDLE
    w.request_tongue(RIGHT)
    run(w, 0.3)
    assert whale.hp == 2 and whale.state == wh.DIVE_WARN and not whale.vulnerable
    run(w, 0.3)
    w.request_tongue(RIGHT)                            # window closed
    run(w, 0.3)
    assert whale.hp == 2
    run(w, wc.WHALE_DIVE_WARN)                         # it dives: frog on a sunk pad falls
    assert w.frog.state == fs.SPLASH or w.frog.cell != (4, 3)


def test_back_window_closes_by_itself():
    w, whale = _world()
    _put(w, (2, 6))
    whale.start_attack(w, "surface")
    _put(w, (9, 1))
    run(w, wc.WHALE_SURFACE_WARN + wc.WHALE_BACK_TIME + 0.1)
    assert whale.state == wh.DIVE_WARN and not whale.vulnerable and not whale.take_hit(w)


def test_fountain_warns_then_jets_along_the_line():
    w, whale = _world()
    _put(w, (5, 3))
    whale.start_attack(w, "fountain")
    (tg,) = whale.telegraphs()
    assert tg.style == "line" and (5, 3) in tg.cells
    assert len(tg.cells) in (12, 8)
    run(w, wc.WHALE_FOUNTAIN_WARN - 0.05)
    assert w.hearts == H
    run(w, 0.15)
    assert whale.state == wh.JET and whale.telegraphs()[0].style == "jet" and w.hearts == H - 1


def test_fountain_can_be_dodged_and_enraged_fountain_is_a_cross():
    w, whale = _world()
    _put(w, (5, 3))
    whale.start_attack(w, "fountain")
    horizontal = whale.lines[0][1] == RIGHT
    w.request_move(UP if horizontal else RIGHT)
    run(w, wc.WHALE_FOUNTAIN_WARN + wc.WHALE_JET_TIME + 0.1)
    assert w.hearts == H
    w.eaten = w.needed // 2
    assert whale.enraged(w)
    run(w, 3)
    whale.start_attack(w, "fountain")
    assert len(whale.telegraphs()) == 2


def test_wave_pushes_the_frog_one_cell_even_into_water():
    rows = ["O" * 12] * 3 + ["OOOOOO#OOOOO"] + ["O" * 12] * 3 + ["FOOOOOOOOOOO"]
    w, whale = _world(rows)
    _put(w, (3, 3))
    whale.start_attack(w, "wave")
    whale.push_dir = RIGHT
    assert all(t.style == "arrow" and t.cells[0][0] == 0 for t in whale.telegraphs())
    run(w, wc.WHALE_WAVE_WARN + 1.0)
    assert w.frog.cell == (4, 3) and w.hearts == H
    run(w, 3)
    _put(w, (5, 3))
    whale.start_attack(w, "wave")
    whale.push_dir = RIGHT
    run(w, wc.WHALE_WAVE_WARN + 1.2)
    assert w.hearts == H - 1                          # pushed into the water at (6, 3)


def test_super_jump_clears_the_wave():
    w, whale = _world()
    _put(w, (6, 3))
    whale.start_attack(w, "wave")
    whale.push_dir = RIGHT
    run(w, wc.WHALE_WAVE_WARN)
    for _ in range(200):                               # jump just before the front arrives
        if whale.front > 4.2:
            break
        w.update(1 / 120)
    w.request_move(LEFT, super_jump=True)
    run(w, 1.0)
    assert w.frog.cell == (4, 3)


def test_gulp_pulls_frog_and_flies_to_the_edge():
    w, whale = _world()
    _put(w, (2, 4))
    fly = w.flies.spawn_at("fly", (3, 5), rest=9)
    whale.start_attack(w, "gulp")
    assert whale.push_dir == LEFT and whale.telegraphs()[0].style == "gulp"
    x0 = fly.pos[0]
    run(w, wc.WHALE_GULP_WARN + wc.WHALE_GULP_TIME)
    assert w.frog.state == fs.SPLASH or w.frog.cell[0] < 2
    assert fly not in w.flies.flies or fly.pos[0] < x0


def test_gulp_ignores_a_far_frog():
    w, whale = _world()
    _put(w, (6, 7))
    whale.start_attack(w, "gulp")
    assert whale.push_dir == DOWN
    _put(w, (6, 0))
    run(w, wc.WHALE_GULP_WARN + wc.WHALE_GULP_TIME)
    assert w.frog.cell == (6, 0)


# ---------------------------------------------------------------- level 1-4
def test_level_1_4_exit_needs_flies_and_defeated_whale():
    w = World(catalog.load_level("1-4"), seed=2, auto_spawn=False)
    whale = w.boss
    assert isinstance(whale, wh.Whale) and whale.hp == 3
    w.eaten = w.needed
    w._become_full()
    assert w.full and w.exit_cell is None
    for i in range(3):
        whale.open_window(3)
        assert whale.take_hit(w)
        assert (w.exit_cell is None) == (i < 2)
    assert whale.defeated

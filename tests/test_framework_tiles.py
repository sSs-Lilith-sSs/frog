"""Level format + generic tile hazards: unstable tiles, moving rows, temp holes, obstacles."""
import pytest
from conftest import make_level, make_world, run

from jebik import config
from jebik.game import events as ev
from jebik.game import frog as fs
from jebik.game.grid import LevelError, parse_level
from jebik.game.grid import DOWN, LEFT, RIGHT
from jebik.game.tiles import GONE, STABLE, WARNING, Unstable


# ---------------------------------------------------------------- level format
def test_extended_level_format():
    lv = parse_level("""
id: 3-4
world: sky
flies_needed: 20
par_time: 50
tobi_time: 60
cell: 50
top_reserve: 160
spawn: P=pike:hole, H=hawk
enemies: swallow; crow @ 2 0 speed=1.5
boss: jesus hp=3
unstable: warn=1 gone=2.5 trigger=cycle stable=3
moving: 1 left 2.5
---
FUXP
OHO#
""")
    assert (lv.world, lv.world_index, lv.level_index) == ("sky", 3, 4)
    assert lv.tobi_time == 60 and lv.cell == 50 and lv.top_reserve == 160
    assert lv.unstable == {(1, 0)} and lv.obstacles == {(2, 0)}
    assert (3, 0) not in lv.pads and (1, 1) in lv.pads            # :hole vs tile spawn
    kinds = [(s.kind, s.cell) for s in lv.spawns]
    assert ("pike", (3, 0)) in kinds and ("hawk", (1, 1)) in kinds
    assert ("swallow", None) in kinds and ("crow", (2, 0)) in kinds
    crow = next(s for s in lv.spawns if s.kind == "crow")
    assert crow.param("speed", 1.0) == 1.5
    assert lv.boss == "jesus" and any(s.kind == "jesus" for s in lv.spawns)
    u = lv.unstable_spec
    assert (u.warn, u.gone, u.trigger, u.stable) == (1.0, 2.5, "cycle", 3.0)
    assert lv.moving_rows[0].row == 1 and lv.moving_rows[0].direction == -1


@pytest.mark.parametrize("bad", [
    "moving: 9 left 2\n---\nFO",          # row out of range
    "moving: 0 up 2\n---\nFO",            # bad direction
    "unstable: trigger=never\n---\nFU",
    "spawn: O=snake\n---\nFO",            # legend may not reuse tile chars
    "enemies: hawk @ 5 5\n---\nFO",       # outside the map
    "flies_needed: 0\n---\nFO",
])
def test_bad_level_headers(bad):
    with pytest.raises(LevelError):
        parse_level(bad)


# ---------------------------------------------------------------- unstable tiles
def test_unstable_state_machine_step_trigger():
    u = Unstable(warn=1.5, gone=4.0, trigger="step")
    assert u.update(10) is None and u.state == STABLE          # never breaks by itself
    assert u.start_warning() and u.state == WARNING
    assert not u.start_warning()                               # already warning
    assert u.update(1.0) is None and u.present and 0.6 < u.progress < 0.7
    assert u.update(0.6) == GONE and not u.present
    assert u.update(3.9) is None and u.state == GONE
    assert u.update(0.2) == STABLE and u.present and u.back_t == 0.0


def test_unstable_cycle_trigger_runs_on_its_own():
    u = Unstable(warn=1.0, gone=2.0, trigger="cycle", stable=3.0, timer=3.0)
    states = []
    for _ in range(int(7 / 0.05)):
        change = u.update(0.05)
        if change:
            states.append(change)
    assert states[:3] == [WARNING, GONE, STABLE]


def test_frog_sinks_with_an_unstable_tile():
    w = make_world(["FUO"], header="unstable: warn=1.5 gone=3")
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + 0.02)
    kinds = [e.kind for e in w.drain_events()]
    assert ev.TILE_WARN in kinds and w.frog.cell == (1, 0)
    run(w, 1.4)
    assert w.frog.state == fs.IDLE                             # still flickering
    run(w, 0.2)
    assert w.frog.state == fs.SPLASH and w.hearts == config.START_HEARTS - 1
    run(w, config.SPLASH_TIME + 0.1)
    assert w.frog.cell != (1, 0) and w.tiles.standable(w.frog.cell)
    run(w, 3.0)
    assert w.tiles.standable((1, 0))                           # it came back


# ---------------------------------------------------------------- moving rows
def test_moving_row_carries_the_frog_and_wraps_tiles():
    w = make_world(["OFO#O", "OOOOO"], header="moving: 0 right 1.0")
    tile_ids = [w.tiles.tile((x, 0)).id for x in range(5)]
    run(w, 1.01)
    assert w.frog.cell == (2, 0) and w.frog.state == fs.IDLE
    assert [w.tiles.tile(((x + 1) % 5, 0)).id for x in range(5)] == tile_ids
    assert w.tiles.is_hole((4, 0)) and w.tiles.standable((0, 0))     # '#' moved, 'O' wrapped
    assert any(e.kind == ev.ROW_SHIFT for e in w.drain_events())


def test_moving_row_drops_the_frog_off_the_edge():
    w = make_world(["OOOF", "OOOO"], header="moving: 0 right 1.0")
    run(w, 1.01)
    assert w.frog.state == fs.SPLASH and w.hearts == config.START_HEARTS - 1
    run(w, config.SPLASH_TIME + 0.05)
    assert w.frog.state == fs.IDLE and w.frog.cell[1] == 1           # respawn off the moving row


def test_hopping_frog_is_not_carried():
    w = make_world(["OFOO", "OOOO"], header="moving: 0 right 1.0")
    run(w, 1.0 - config.HOP_TIME / 2)
    w.request_move(DOWN)
    run(w, config.HOP_TIME)
    assert w.frog.cell == (1, 1)


# ---------------------------------------------------------------- temporary holes
def test_temporary_hole_restores_and_drops_the_frog():
    w = make_world(["OFO"])
    w.make_hole((1, 0), 2.0)
    assert not w.tiles.standable((1, 0)) and w.tiles.is_hole((1, 0))
    assert w.frog.state == fs.SPLASH                                 # it was standing there
    run(w, 1.9)
    assert not w.tiles.standable((1, 0))
    run(w, 0.2)
    assert w.tiles.standable((1, 0))
    assert [e.kind for e in w.drain_events()].count(ev.HOLE_CLOSE) == 1


def test_temporary_hole_on_water_is_ignored():
    w = make_world(["F#O"])
    assert w.tiles.make_hole((1, 0), 3) == []


# ---------------------------------------------------------------- obstacles
def test_obstacle_blocks_hops_but_not_super_jumps():
    w = make_world(["FXO", "OOO"])
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + 0.02)
    assert w.frog.cell == (0, 0)
    assert any(e.kind == ev.BUMP for e in w.drain_events())
    w.request_move(RIGHT, super_jump=True)                           # over the stump
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.cell == (2, 0) and w.hearts == config.START_HEARTS
    w.frog.super_cd = 0
    w.request_move(LEFT, super_jump=True)
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.cell == (0, 0)


def test_obstacles_are_not_walkable_for_enemies_or_holes():
    lv = make_level(["FXO"])
    w = make_world(["FXO"])
    assert w.tiles.blocks((1, 0)) and not w.tiles.is_hole((1, 0))
    assert list(w.tiles.neighbors((2, 0))) == []
    assert (1, 0) not in lv.holes

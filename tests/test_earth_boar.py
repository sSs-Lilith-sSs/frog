"""Earth boss: the boar — lane charges, stumps, stuns, hits, stomp, exit rule."""
from conftest import make_world, run

from jebik.game.grid import LEFT
from jebik.game.tiles import OBSTACLE, SOLID
from jebik.worlds.earth import boar as bl
from jebik.worlds.earth import config as ec
from jebik.worlds.earth.boar import Boar

OPEN = ["OOOOOOOOOOOO",
        "OOOOOOOOOOOO",
        "OOOOOOFOOOOO",
        "OOOOOOOOOOOO",
        "OOOOOOOOOOOO",
        "OOOOOOOOOOOO"]


def boar_world(rows=OPEN, x=8, y=2):
    w = make_world(rows, flies_needed=3, header=f"boss: boar @ {x} {y} hp=3", enemies=True)
    w.frog.invuln = 999.0                     # keep the frog out of the way
    b = w.boss
    assert isinstance(b, Boar)
    return w, b


def until(w, cond, seconds=10.0):
    for _ in range(int(seconds * 60)):
        w.update(1 / 60)
        if cond():
            return True
    return False


def test_boar_is_2x2_and_telegraphs_a_lane_toward_the_frog():
    w, b = boar_world()
    assert b.body() == {(8, 2), (9, 2), (8, 3), (9, 3)}
    assert b.tongue_hit(w, [(7, 2), (8, 2)]) == 1
    assert until(w, lambda: b.state == bl.TELL)
    assert b.dir == (-1, 0)
    tg = b.telegraphs()[0]
    assert tg.style == "zone" and {(0, 2), (0, 3), (7, 2), (7, 3)} <= set(tg.cells)
    assert not set(tg.cells) & b.body()


def test_charge_to_edge_stuns_two_seconds_leaves_pits_but_no_window():
    w, b = boar_world()
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = (6, 5)     # out of the lane
    b.state, b.timer, b.dir = bl.TELL, 0.01, (-1, 0)
    assert until(w, lambda: b.state == bl.STUN, 3)
    assert b.stun_kind == "edge" and round(b.pos[0]) == 0 and round(b.pos[1]) == 2
    assert abs(b.stunned - ec.BOAR_EDGE_STUN) < 0.1
    assert not b.vulnerable
    assert b.pits >= 2 and any(w.tiles.is_hole((x, y)) for x in range(2, 8) for y in (2, 3))
    b.stunned, b.state, b.timer = 0.0, bl.THINK, 999.0     # let it rest
    run(w, ec.BOAR_PIT_TIME + 0.5)
    assert all(w.tiles.standable((x, y)) for x in range(12) for y in (2, 3))   # pits close again


def test_tongue_hits_only_while_stunned_by_a_stump():
    rows = [r for r in OPEN]
    rows[2] = "OOXOOOOOOOOO"
    rows[3] = "OOOOOOOFOOOO"
    rows = [r.replace("F", "O") if i == 2 else r for i, r in enumerate(rows)]
    w, b = boar_world(rows, 9, 2)
    # not stunned: the tongue bounces off
    w.frog.facing = 1
    b.state, b.timer = bl.THINK, 99
    w.request_tongue(1)
    run(w, 0.5)
    assert b.hp == 3
    # charge into the stump at (2, 2)
    b.state, b.timer, b.dir = bl.TELL, 0.01, (-1, 0)
    assert until(w, lambda: b.state == bl.STUN, 3)
    assert b.stun_kind == "stump" and round(b.pos[0]) == 3
    assert w.tiles.tile((2, 2)).kind == SOLID               # the stump broke
    assert b.vulnerable and abs(b.stunned - ec.BOAR_STUMP_STUN) < 0.1
    assert b.blocks((3, 2)) and not b.hurts(w, (3.5, 2.5))
    # frog at (7, 3) tongues left: (6, 3), (5, 3) -> not reaching; hop closer
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = (6, 3)
    w.request_tongue(LEFT)
    run(w, 0.6)
    assert b.hp == 2 and not b.vulnerable
    assert b.stumps_left == 0                              # used stump stays broken


def test_missed_stump_grows_back():
    rows = [r for r in OPEN]
    rows[2] = "OOXOOOOOOOOO"
    rows[5] = "OOOOOOFOOOOO"
    w, b = boar_world(rows, 9, 2)
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = (6, 5)
    b.state, b.timer, b.dir = bl.TELL, 0.01, (-1, 0)
    assert until(w, lambda: b.state == bl.STUN, 3)
    assert w.tiles.tile((2, 2)).kind == SOLID
    run(w, ec.BOAR_STUMP_STUN + 0.2)
    assert w.tiles.tile((2, 2)).kind == OBSTACLE


def test_stomp_crumbles_five_cells_which_come_back_as_plain_grass():
    w, b = boar_world()
    b.charges = 1
    b.state, b.timer = bl.STOMP, 0.01
    run(w, 0.05)
    assert len(b.stomp_cells) == ec.BOAR_STOMP_CELLS
    assert all(w.tiles.tile(c).unstable is not None for c in b.stomp_cells)
    assert any(e.kind == "earth.stomp" for e in w.drain_events())
    b.state, b.timer = bl.THINK, 999
    run(w, ec.CRUMBLE_WARN + 0.1)
    assert all(w.tiles.is_hole(c) for c in b.stomp_cells)
    run(w, 10)
    assert all(w.tiles.standable(c) and w.tiles.tile(c).unstable is None for c in b.stomp_cells)


def test_exit_needs_exact_flies_and_defeated_boar():
    w, b = boar_world()
    w.eaten = w.needed
    w._become_full()
    assert w.full and w.exit_cell is None
    for hp in (2, 1, 0):
        assert not b.take_hit(w)                           # closed window
        b.open_window(ec.BOAR_STUMP_STUN)
        assert b.take_hit(w) and b.hp == hp
    assert b.defeated and w.exit_cell is not None
    assert w.exit_cell not in b.body()
    assert not b.hurts(w, b.center())

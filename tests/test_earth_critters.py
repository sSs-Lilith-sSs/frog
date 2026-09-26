"""Earth world: hedgehog, fox and mole behaviour (headless, seeded)."""
from conftest import make_world, run

from jebik import config
from jebik.game import events as ev
from jebik.worlds.earth import config as ec
from jebik.worlds.earth import hedgehog as hh
from jebik.worlds.earth import mole as ml
from jebik.worlds.earth.fox import Fox, fox_moves
from jebik.worlds.earth.hedgehog import Hedgehog

HH = "spawn: H=hedgehog"


# ---------------------------------------------------------------- hedgehog
def test_hedgehog_rolls_at_frog_in_clear_row():
    w = make_world(["FOOOOOH"], header=HH, enemies=True)
    h = w.enemies[0]
    assert isinstance(h, Hedgehog)
    run(w, 0.05)
    assert h.state == hh.CURL and h.roll_dir == (-1, 0)
    assert h.telegraphs() and h.telegraphs()[0].style == "line"
    run(w, ec.HEDGEHOG_CURL + 0.1)
    assert h.state == hh.ROLL
    run(w, 1.0)
    assert w.hearts == config.START_HEARTS - 1          # rolled straight into the frog


def test_hedgehog_rolls_along_a_column_too():
    w = make_world(["H", "O", "O", "F"], header=HH, enemies=True)
    run(w, 0.05)
    assert w.enemies[0].state == hh.CURL and w.enemies[0].roll_dir == (0, 1)


def test_hedgehog_ignores_frog_behind_a_pit_or_off_line():
    w = make_world(["FO#OOH", "OOOOOO"], header=HH, enemies=True)
    run(w, 0.05)
    assert w.enemies[0].state == hh.WALK
    w = make_world(["FOOOOO", "OOOOOH"], header=HH, enemies=True)
    run(w, 0.05)
    assert w.enemies[0].state == hh.WALK


def test_hedgehog_falls_into_pit_and_comes_back_after_5s():
    w = make_world(["FOOOOOOH", "OOOOOOOO"], header=HH, enemies=True)
    h = w.enemies[0]
    run(w, 0.05)
    assert h.state == hh.CURL
    w.make_hole((4, 0), 30)                               # a pit opens on its path
    run(w, ec.HEDGEHOG_CURL + 0.6)
    assert h.state == hh.GONE and not h.alive and h.falls == 1
    assert not h.hurts(w, h.pos) and h.occupied() == set()
    assert any(e.kind == "earth.hedgehog_fall" for e in w.drain_events())
    assert w.hearts == config.START_HEARTS
    run(w, ec.HEDGEHOG_GONE - 0.8)
    assert not h.alive
    run(w, 0.8)
    assert h.alive and w.tiles.standable(h.cell)


def test_hedgehog_stops_at_a_stump():
    w = make_world(["FOXOOOH"], header=HH, enemies=True)
    run(w, 0.05)
    assert w.enemies[0].state == hh.WALK                  # stump blocks the view
    w = make_world(["FOOOOOH", "OOOOOOO"], header=HH, enemies=True)
    h = w.enemies[0]
    h.roll_dir = (1, 0)
    h.state = hh.ROLL
    run(w, 0.3)
    assert h.state == hh.REST and h.cell == (6, 0)        # hit the field edge


# ---------------------------------------------------------------- fox
def test_fox_moves_jump_single_pits_only():
    w = make_world(["F#O##O", "OOOOOO"])
    assert set(fox_moves(w, (0, 0))) == {(2, 0), (0, 1)}
    assert (5, 0) not in set(fox_moves(w, (2, 0)))        # two pits: no leap


def test_fox_jumps_over_pit_then_recovers_one_second():
    w = make_world(["FO#OL"], header="spawn: L=fox", enemies=True)
    fox = w.enemies[0]
    assert isinstance(fox, Fox)
    landed_at = None
    for _ in range(240):
        w.update(1 / 60)
        if fox.jumps and not fox.jumping:
            landed_at = fox.cell
            break
    assert fox.jumps == 1 and landed_at == (1, 0)
    assert any(e.kind == "earth.fox_jump" for e in w.drain_events())
    run(w, ec.FOX_RECOVER - 0.1)
    assert fox.cell == (1, 0) and fox.next_cell is None and w.hearts == config.START_HEARTS
    run(w, 0.6)
    assert w.hearts == config.START_HEARTS - 1            # recovered and bit the frog


def test_fox_is_harmless_mid_leap():
    w = make_world(["FOO#OL"], header="spawn: L=fox", enemies=True)
    fox = w.enemies[0]
    fox.jumping = True
    assert not fox.hurts(w, fox.pos)


# ---------------------------------------------------------------- mole
def test_mole_trembles_under_frog_then_leaves_temporary_pit():
    rows = ["OOOOO", "OOOOO", "OOFOO", "OOOOO", "OOOOM"]
    w = make_world(rows, header="spawn: M=mole", enemies=True)
    mole = w.enemies[0]
    assert not mole.hurts(w, mole.pos)
    seen_tremor = False
    for _ in range(60 * 10):
        w.update(1 / 60)
        if mole.state == ml.TREMOR:
            seen_tremor = True
            tg = mole.telegraphs()
            assert tg and tg[0].style == "shake" and tg[0].cells == ((2, 2),)
        if mole.pops:
            break
    assert seen_tremor and mole.pops == 1
    assert w.tiles.is_hole((2, 2))
    assert w.frog.state == "splash"                       # the frog stood still: it fell
    run(w, ec.MOLE_HOLE_TIME - 0.3)
    assert w.tiles.is_hole((2, 2))
    run(w, 0.4)
    assert w.tiles.standable((2, 2))                      # pit restored after 8 s
    assert any(e.kind == ev.HOLE_CLOSE for e in w.drain_events())


def test_mole_pops_into_empty_ground_if_frog_leaves():
    rows = ["OOOOO", "OOOOO", "OOFOO", "OOOOO", "OOOOM"]
    w = make_world(rows, header="spawn: M=mole", enemies=True)
    mole = w.enemies[0]
    for _ in range(60 * 10):
        w.update(1 / 60)
        if mole.state == ml.TREMOR:
            break
    w.request_move(1)                                     # hop away
    run(w, ec.MOLE_TREMOR + 0.1)
    assert mole.pops == 1 and w.tiles.is_hole((2, 2))
    assert w.hearts == config.START_HEARTS

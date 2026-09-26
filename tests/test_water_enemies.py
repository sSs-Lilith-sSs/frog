"""Water world: pike and heron telegraph -> strike timing, dodging."""
from conftest import make_world, run

from jebik import config
from jebik.game.grid import DOWN, LEFT, UP
from jebik.worlds.water import config as wc
from jebik.worlds.water import heron as hn
from jebik.worlds.water import pike as pk

H = config.START_HEARTS


def _until(w, cond, limit=6.0, dt=1 / 60):
    t = 0.0
    while not cond() and t < limit:
        w.update(dt)
        t += dt
    assert cond(), "condition never met"
    return t


# ---------------------------------------------------------------- pike
def _pike_world():
    w = make_world(["OOOOO",
                    "OF#P#",
                    "OOOOO"], header="spawn: P=pike:hole", enemies=True)
    return w, w.enemies[0]


def test_pike_is_hidden_until_frog_is_next_to_water():
    w = make_world(["OOOOOO", "FOOO#P"], header="spawn: P=pike:hole", enemies=True)
    pike = w.enemies[0]
    run(w, 4.0)                                      # frog 3 cells from the water
    assert pike.state in (pk.HIDDEN, pk.COOLDOWN) and not pike.telegraphs()
    assert not pike.visible and w.hearts == H


def test_pike_bubbles_then_bites_after_warn_time():
    w, pike = _pike_world()
    _until(w, lambda: pike.telegraphs())
    tg = pike.telegraphs()[0]
    assert tg.style == "bubbles" and tg.cells == ((2, 1),)
    assert pike.target == (1, 1)
    run(w, wc.PIKE_WARN - 0.05)
    assert w.hearts == H and pike.state == pk.BUBBLES
    run(w, 0.25)
    assert pike.state == pk.LUNGE and w.hearts == H - 1


def test_pike_misses_a_frog_that_hopped_away():
    w, pike = _pike_world()
    _until(w, lambda: pike.telegraphs())
    w.request_move(LEFT)                              # (0, 1): no water next to it
    run(w, wc.PIKE_WARN + wc.PIKE_LUNGE + 0.1)
    assert w.hearts == H and w.frog.cell == (0, 1)


# ---------------------------------------------------------------- heron
def _heron_world():
    w = make_world(["OOO", "OFO", "OOO"], header="enemies: heron", enemies=True)
    heron = w.enemies[0]
    heron.timer = 0.01
    return w, heron


def test_heron_first_strike_is_not_immediate():
    w = make_world(["OOO", "OFO", "OOO"], header="enemies: heron", enemies=True)
    run(w, wc.HERON_FIRST[0] - 0.1)
    assert w.enemies[0].state == hn.AWAY and w.hearts == H


def test_heron_shadow_then_beak_after_warn_time():
    w, heron = _heron_world()
    run(w, 0.05)
    tg = heron.telegraphs()
    assert tg and tg[0].style == "shadow" and tg[0].cells == ((1, 1),)
    run(w, wc.HERON_WARN - 0.1)
    assert w.hearts == H and heron.state == hn.SHADOW
    run(w, 0.15)
    assert heron.state == hn.STRIKE and w.hearts == H - 1


def test_heron_shadow_stays_so_hopping_dodges():
    w, heron = _heron_world()
    run(w, 0.05)
    w.request_move(UP)
    run(w, wc.HERON_WARN + wc.HERON_STRIKE + 0.2)
    assert heron.target in ((1, 1), None) and w.hearts == H
    w.request_move(DOWN)
    run(w, 0.3)
    assert w.hearts == H

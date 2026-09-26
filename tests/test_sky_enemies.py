"""Sky predators: swallow telegraph -> pass, hawk windup -> dash, crow eats / caws / pecks."""
from conftest import make_world, run

from jebik import config
from jebik.game.grid import RIGHT, UP
from jebik.worlds.sky import config as sc

OPEN = ["OOOOOOO", "OOOOOOO", "OOFOOOO", "OOOOOOO", "OOOOOOO"]


def _events(world, seconds, dt=1 / 60):
    out = []
    for _ in range(int(round(seconds / dt))):
        world.update(dt)
        out += world.drain_events()
    return out


def _force_row(sw, world, row, forward=True):
    """Put the swallow's next pass on ``row`` (left -> right)."""
    sw.timer = 0.0
    world.rng.seed(0)
    sw._pick_lane = lambda w: _lane(sw, w, row)


def _lane(sw, w, row):
    m = sc.SWALLOW_MARGIN
    sw.axis, sw.index, sw.direction = "row", row, RIGHT
    sw.start, sw.end = (-m, float(row)), (w.level.width - 1 + m, float(row))
    sw._lane = sw.lane_cells(w)


def test_swallow_arrow_then_pass_hits_frog_in_its_row():
    w = make_world(OPEN, enemies=True, header="enemies: swallow")
    sw = w.enemies[0]
    assert sw.telegraphs() == [] and not sw.hurts(w, w.frog.pos())
    _force_row(sw, w, 2)
    run(w, 0.05)
    assert sw.state == "warn"
    styles = {t.style: t for t in sw.telegraphs()}
    assert styles["arrow"].cells == ((-1, 2),) and styles["arrow"].direction == RIGHT
    assert len(styles["line"].cells) == 7
    run(w, sc.SWALLOW_WARN - 0.15)
    assert sw.state == "warn" and w.hearts == 3          # 1 s of warning, no damage yet
    run(w, 0.5)
    assert w.hearts == 2                                  # then it flies through the row


def test_swallow_is_dodged_by_leaving_the_row():
    w = make_world(OPEN, enemies=True, header="enemies: swallow")
    sw = w.enemies[0]
    _force_row(sw, w, 2)
    run(w, 0.1)
    w.request_move(UP)
    run(w, 2.0)
    assert w.hearts == 3 and sw.passes == 1


def test_hawk_winds_up_then_dashes_two_cells():
    w = make_world(OPEN, enemies=True, header="enemies: hawk @ 4 2")
    hawk = w.enemies[0]
    assert hawk.speed < 1 / config.HOP_TIME               # slower than the frog
    run(w, 1 / 60)
    assert hawk.state == "windup"
    tg = hawk.telegraphs()
    assert tg and tg[0].style == "zone" and (2, 2) in tg[0].cells
    run(w, sc.HAWK_WINDUP - 0.1)
    assert w.hearts == 3 and hawk.state == "windup"
    run(w, 0.4)
    assert hawk.dashes == 1 and w.hearts == 2
    assert hawk.dash_to == (2.0, 2.0)                     # 2 cells from (4, 2)


def test_hawk_flies_over_the_abyss():
    w = make_world(["OOOOOOOO", "O######O", "OF####HO"], enemies=True, header="spawn: H=hawk:hole")
    hawk = w.enemies[0]
    start = hawk.pos
    run(w, 0.6)
    assert hawk.pos[0] < start[0]                          # moved over the holes toward the frog


def test_crow_eats_a_fly_and_supply_drops():
    w = make_world(["OOOOOO", "OOOOOO", "OOOOOO", "FOOOOO"], enemies=True, header="enemies: crow @ 3 0")
    crow = w.enemies[0]
    fly = w.flies.spawn_at("fly", (5, 0), rest=5.0)
    crow.timer, crow.caw_timer = 0.0, 99.0
    ev = _events(w, 1.5)
    assert fly not in w.flies.flies and crow.eaten == 1
    assert any(e.kind == "sky.crow_eat" for e in ev)
    assert w.eaten == 0                                     # the frog got nothing


def test_crow_caw_hastens_the_others():
    w = make_world(OPEN, enemies=True, header="enemies: crow @ 6 0; swallow")
    crow = w.enemies[0]
    crow.caw_timer, crow.timer = 0.0, 5.0
    ev = _events(w, 0.1)
    assert any(e.kind == "sky.caw" for e in ev)
    assert w.enemy_speed == sc.CROW_HASTE[0]
    run(w, sc.CROW_HASTE[1])
    assert w.enemy_speed == 1.0


def test_crow_pecks_the_frog_next_to_it():
    w = make_world(OPEN, enemies=True, header="enemies: crow @ 3 2")
    crow = w.enemies[0]
    crow.caw_timer, crow.peck_cd = 99.0, 0.0
    run(w, 0.05)
    assert crow.state == "peck" and crow.telegraphs()[0].cells == ((2, 2),)
    run(w, sc.CROW_PECK_WINDUP)
    assert w.hearts == 2


def test_crow_peck_misses_if_the_frog_hops_away():
    w = make_world(OPEN, enemies=True, header="enemies: crow @ 3 2")
    w.enemies[0].caw_timer, w.enemies[0].peck_cd = 99.0, 0.0
    run(w, 0.05)
    w.request_move(UP)
    run(w, sc.CROW_PECK_WINDUP + 0.1)
    assert w.hearts == 3
    assert w.frog.cell == (2, 1)

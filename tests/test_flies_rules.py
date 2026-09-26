from conftest import make_world, run

from jebik import config
from jebik.game import events as ev
from jebik.game.grid import DOWN, RIGHT

ROW = ["FOOOOOO"]


def tongue_until_done(w):
    w.request_tongue()
    run(w, 0.6)


def test_tongue_range_two(open_row=None):
    w = make_world(ROW)
    w.frog.facing = RIGHT
    far = w.flies.spawn_at("fly", (3, 0), rest=99)
    tongue_until_done(w)
    assert far in w.flies.flies and w.eaten == 0
    near = w.flies.spawn_at("fly", (2, 0), rest=99)
    run(w, config.TONGUE_COOLDOWN)
    tongue_until_done(w)
    assert near not in w.flies.flies and w.eaten == 1


def test_tongue_range_four_with_firefly():
    w = make_world(ROW)
    w.frog.facing = RIGHT
    ff = w.flies.spawn_at("firefly", (1, 0), rest=99)
    tongue_until_done(w)
    assert ff not in w.flies.flies
    assert w.frog.firefly > 0
    assert w.eaten == 0                       # firefly is not counted
    far = w.flies.spawn_at("fly", (4, 0), rest=99)
    too_far = w.flies.spawn_at("fly", (5, 0), rest=99)
    run(w, config.TONGUE_COOLDOWN)
    tongue_until_done(w)
    assert far not in w.flies.flies
    assert too_far in w.flies.flies
    # firefly wears off -> range back to 2
    run(w, config.FIREFLY_DURATION)
    assert w.frog.tongue_range == config.TONGUE_RANGE


def test_tongue_catches_first_fly_on_line():
    w = make_world(ROW)
    w.frog.facing = RIGHT
    second = w.flies.spawn_at("fly", (2, 0), rest=99)
    first = w.flies.spawn_at("fly", (1, 0), rest=99)
    tongue_until_done(w)
    assert first not in w.flies.flies
    assert second in w.flies.flies
    assert w.eaten == 1


def test_tongue_ignores_flies_off_the_line():
    w = make_world(["FOO", "OOO"])
    w.frog.facing = RIGHT
    off = w.flies.spawn_at("fly", (1, 1), rest=99)
    tongue_until_done(w)
    assert off in w.flies.flies


def test_tongue_reaches_flies_over_water():
    w = make_world(["F##"])
    w.frog.facing = RIGHT
    fly = w.flies.spawn_at("fly", (2, 0), rest=99)
    tongue_until_done(w)
    assert fly not in w.flies.flies and w.eaten == 1


def test_space_with_direction_turns_and_fires():
    w = make_world(["FO", "OO"])
    w.frog.facing = RIGHT
    fly = w.flies.spawn_at("fly", (0, 1), rest=99)
    w.request_tongue(DOWN)
    run(w, 0.6)
    assert fly not in w.flies.flies


def test_tongue_cooldown():
    w = make_world(ROW)
    w.frog.facing = RIGHT
    w.request_tongue()
    run(w, 0.3)                              # tongue back, cooldown not over
    fly = w.flies.spawn_at("fly", (1, 0), rest=99)
    w.request_tongue()
    run(w, 0.05)
    assert w.frog.tongue is None and fly in w.flies.flies
    run(w, config.TONGUE_COOLDOWN)
    tongue_until_done(w)
    assert fly not in w.flies.flies


def test_landing_on_fly_eats_it():
    w = make_world(ROW)
    fly = w.flies.spawn_at("fly", (1, 0), rest=99)
    w.request_move(RIGHT)
    run(w, 0.3)
    assert fly not in w.flies.flies and w.eaten == 1


def test_exact_n_spawns_exit_and_reaching_it_wins():
    w = make_world(["FOOOOOO", "OOOOOOO"], flies_needed=2)
    w.frog.facing = RIGHT
    w.flies.spawn_at("dragon", (1, 0), rest=99)
    tongue_until_done(w)
    assert w.eaten == 2 and w.full
    kinds = [e.kind for e in w.drain_events()]
    assert ev.FULL in kinds and ev.EXIT_SPAWN in kinds
    exit_cell = w.exit_cell
    assert exit_cell in w.level.pads and exit_cell != w.frog.cell
    # teleport next to the exit and hop on it
    w.frog.cell = (exit_cell[0] - 1, exit_cell[1]) if exit_cell[0] > 0 else (1, exit_cell[1])
    direction = RIGHT if exit_cell[0] > w.frog.cell[0] else 3
    w.request_move(direction)
    run(w, 0.3)
    assert w.state == "won"
    assert w.result is not None and w.result.stars == 3
    assert w.result.score == 2 * config.SCORE_PER_FLY + 3 * config.SCORE_PER_HEART \
        + config.SCORE_NO_DAMAGE


def test_overeat_costs_heart_and_counter_stays_n():
    w = make_world(ROW, flies_needed=1)
    w.frog.facing = RIGHT
    w.flies.spawn_at("fly", (1, 0), rest=99)
    tongue_until_done(w)
    assert w.eaten == 1 and w.full
    w.drain_events()
    run(w, config.TONGUE_COOLDOWN)
    w.flies.spawn_at("fly", (2, 0), rest=99)
    tongue_until_done(w)
    assert w.eaten == 1
    assert w.hearts == config.START_HEARTS - 1
    assert ev.OVEREAT in [e.kind for e in w.drain_events()]
    assert w.damaged


def test_dragonfly_overshoot_counts_as_overeat():
    w = make_world(ROW, flies_needed=3)
    w.eaten = 2
    w.frog.facing = RIGHT
    w.flies.spawn_at("dragon", (1, 0), rest=99)
    tongue_until_done(w)
    assert w.eaten == 3 and w.full and w.exit_cell is not None
    assert w.hearts == config.START_HEARTS - 1


def test_golden_and_firefly_not_counted():
    w = make_world(ROW, flies_needed=1)
    w.frog.facing = RIGHT
    w.flies.spawn_at("gold", (1, 0), rest=99)
    tongue_until_done(w)
    run(w, config.TONGUE_COOLDOWN)
    w.flies.spawn_at("firefly", (1, 0), rest=99)
    tongue_until_done(w)
    assert w.eaten == 0 and not w.full


def test_golden_heart_cap_three():
    w = make_world(ROW)
    w.frog.facing = RIGHT
    assert w.hearts == 3
    w.flies.spawn_at("gold", (1, 0), rest=99)
    tongue_until_done(w)
    assert w.hearts == 3
    w.hearts = 1
    for _ in range(3):
        run(w, config.TONGUE_COOLDOWN)
        w.flies.spawn_at("gold", (1, 0), rest=99)
        tongue_until_done(w)
    assert w.hearts == 3


def test_stars_and_score_rules():
    from jebik.game.rules import compute_result
    r = compute_result("1-1", "ezzz", 30, 5, 3, True, 60)
    assert r.stars == 3
    assert compute_result("1-1", "ezzz", 90, 5, 3, True, 60).stars == 2
    assert compute_result("1-1", "ezzz", 20, 5, 2, False, 60).stars == 1


def test_flies_keep_population_between_3_and_5():
    from jebik.game.grid import load_level
    from jebik.game.world import World
    w = World(load_level("1-1"), seed=5)
    for _ in range(60 * 20):
        w.update(1 / 60)
        n = w.flies.counted_alive()
        assert n <= config.FLY_MAX
    assert config.FLY_MIN <= w.flies.counted_alive() + len(w.flies.respawn_timers) <= config.FLY_MAX

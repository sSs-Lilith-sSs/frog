from conftest import make_world, run

from jebik import config
from jebik.game import events as ev
from jebik.game import frog as fs
from jebik.game.grid import DOWN, LEFT, RIGHT, UP


def kinds(world):
    return [e.kind for e in world.drain_events()]


def test_hop_moves_one_cell_and_takes_hop_time(open_world):
    w = open_world
    w.request_move(RIGHT)
    assert w.frog.state == fs.HOP
    run(w, config.HOP_TIME * 0.5)
    assert w.frog.cell == (2, 2)            # logical cell changes on landing
    run(w, config.HOP_TIME)
    assert w.frog.cell == (3, 2)
    assert w.frog.state == fs.IDLE
    assert w.frog.facing == RIGHT


def test_bounds_block_movement_but_turn_frog():
    w = make_world(["FO", "OO"])
    w.request_move(UP)
    assert w.frog.state == fs.IDLE
    assert w.frog.cell == (0, 0)
    assert w.frog.facing == UP
    assert ev.BUMP in kinds(w)
    w.request_move(LEFT)
    assert w.frog.cell == (0, 0) and w.frog.facing == LEFT


def test_move_is_buffered_during_hop(open_world):
    w = open_world
    w.request_move(RIGHT)
    run(w, 0.05)
    w.request_move(DOWN)          # buffered
    run(w, config.HOP_TIME * 2 + 0.05)
    assert w.frog.cell == (3, 3)


def test_only_one_move_is_buffered(open_world):
    w = open_world
    w.request_move(RIGHT)
    w.request_move(DOWN)
    w.request_move(UP)            # replaces DOWN in the one-slot buffer
    run(w, 1.0)
    assert w.frog.cell == (3, 1)


def test_hop_into_water_splashes_loses_heart_and_respawns():
    w = make_world(["OOO", "F#O", "OOO"])
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + 0.02)
    assert w.frog.state == fs.SPLASH
    assert w.hearts == config.START_HEARTS - 1
    assert ev.SPLASH in kinds(w)
    run(w, config.SPLASH_TIME + 0.05)
    assert w.frog.state == fs.IDLE
    assert w.frog.cell == (0, 1)          # last safe pad
    assert w.frog.invuln > 0
    assert w.damaged


def test_water_death_on_last_heart_loses_game():
    w = make_world(["F#"])
    w.hearts = 1
    w.request_move(RIGHT)
    run(w, config.HOP_TIME + config.SPLASH_TIME + 0.1)
    assert w.state == "lost"
    run(w, config.LOSE_DELAY + 0.1)
    assert w.show_result


def test_superjump_over_water_lands_two_cells_away():
    w = make_world(["F#O"])
    w.request_move(RIGHT, super_jump=True)
    assert w.frog.state == fs.SUPER
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.cell == (2, 0)
    assert w.frog.state == fs.IDLE
    assert w.hearts == config.START_HEARTS


def test_superjump_cooldown():
    w = make_world(["FOOOOOO"])
    w.request_move(RIGHT, super_jump=True)
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.cell == (2, 0)
    w.drain_events()
    w.request_move(RIGHT, super_jump=True)          # still cooling down
    assert w.frog.state == fs.IDLE and w.frog.cell == (2, 0)
    assert ev.SUPER_DENIED in kinds(w)
    run(w, config.SUPERJUMP_COOLDOWN)
    w.request_move(RIGHT, super_jump=True)
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.cell == (4, 0)


def test_superjump_out_of_bounds_is_refused_without_cooldown():
    w = make_world(["OFO"])
    w.request_move(RIGHT, super_jump=True)
    assert w.frog.state == fs.IDLE
    assert w.frog.super_cd == 0


def test_superjump_into_water_still_splashes():
    w = make_world(["FO#"])
    w.request_move(RIGHT, super_jump=True)
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.state == fs.SPLASH

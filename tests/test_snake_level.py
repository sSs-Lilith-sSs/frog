import random

import pytest
from conftest import make_level, make_world, run

from jebik import config
from jebik.game.grid import LevelError, load_level, parse_level
from jebik.game.snake import Snake
from jebik.game.world import World


MAZE = [
    "S#OOOOO",
    "O#O###O",
    "O#O#O#O",
    "OOO#OFO",
]


def test_snake_path_never_uses_water():
    lv = make_level(MAZE)
    snake = Snake.spawn(lv, lv.snake_starts[0], random.Random(3), length=2)
    path = snake.path_to((5, 3))
    assert path is not None
    assert all(c in lv.pads for c in path)


def test_snake_reaches_frog_without_entering_water():
    lv = make_level(MAZE)
    w = World(lv, seed=2, auto_spawn=False)
    snake = w.enemies[0]
    for _ in range(60 * 30):
        w.update(1 / 60)
        # force chase regardless of distance so the test is quick
        for cell in snake.cells:
            assert cell in lv.pads
        if w.hearts < config.START_HEARTS:
            break
    assert snake.visited <= lv.pads
    assert w.hearts < config.START_HEARTS, "snake never reached the frog"


def test_snake_chases_within_sight_and_wanders_otherwise():
    w = make_world(["S" + "O" * 9 + "F"], enemies=True)
    snake = w.enemies[0]
    run(w, 0.1)
    assert snake.mode == "wander"
    w2 = make_world(["OOOOSOOF"], enemies=True)
    run(w2, 0.1)
    assert w2.enemies[0].mode == "chase"


def test_snake_bite_costs_heart_gives_invulnerability_and_retreat():
    w = make_world(["OOOOOO", "SOOOFO"], enemies=True)
    snake = w.enemies[0]
    for _ in range(600):
        w.update(1 / 60)
        if w.damaged:
            break
    assert w.hearts == config.START_HEARTS - 1
    assert w.frog.invuln > 0
    assert snake.retreat > 0
    hearts = w.hearts
    run(w, 1.0)                      # invulnerable: no double hit
    assert w.hearts == hearts


def test_superjump_passes_over_snake():
    w = make_world(["FOOO"], enemies=False)
    lv = w.level
    snake = Snake(level=lv, rng=random.Random(0), cells=[(1, 0)])
    snake.step_time = 99
    w.enemies.append(snake)
    snake.next_cell = None
    snake.update = lambda dt, frog: None       # frozen snake
    w.request_move(1, super_jump=True)
    run(w, config.SUPERJUMP_TIME + 0.02)
    assert w.frog.cell == (2, 0)
    assert w.hearts == config.START_HEARTS


def test_respawn_avoids_snake():
    w = make_world(["OOOOOO", "F#OOOO"], enemies=False)
    lv = w.level
    snake = Snake(level=lv, rng=random.Random(0), cells=[(0, 0)])
    snake.update = lambda dt, frog: None
    w.enemies.append(snake)
    w.frog.invuln = 5                          # ignore contact while testing
    w.request_move(1)                          # into water
    run(w, config.HOP_TIME + config.SPLASH_TIME + 0.1)
    cell = w.frog.cell
    assert cell in lv.pads
    assert abs(cell[0] - 0) + abs(cell[1] - 0) >= config.SNAKE_SAFE_RESPAWN_DIST


def test_level_1_1_file_parses():
    lv = load_level("1-1")
    assert (lv.width, lv.height) == (12, 8)
    assert lv.flies_needed == 5
    assert lv.frog_start in lv.pads
    assert len(lv.snake_starts) == 1 and lv.snake_starts[0] in lv.pads
    assert lv.holes and all(not lv.is_pad(h) for h in lv.holes)
    assert lv.world == "water" and lv.world_index == 1 and lv.level_index == 1


def test_parse_errors():
    with pytest.raises(LevelError):
        parse_level("id: 1-1\nOOO")                       # no separator
    with pytest.raises(LevelError):
        parse_level("---\nOOO\nOO")                        # ragged
    with pytest.raises(LevelError):
        parse_level("---\nOOO\nOOO")                       # no frog
    with pytest.raises(LevelError):
        parse_level("---\nFOX")                            # unknown char
    with pytest.raises(LevelError):
        parse_level("size: 4x1\n---\nFOO")                 # size mismatch


def test_parse_meta_and_map():
    lv = parse_level("# comment\nid = 2-3\nworld: land\nflies_needed: 7\n"
                     "par_time: 45\n---\n#FO\nSO#\n")
    assert lv.id == "2-3" and lv.world == "land"
    assert lv.flies_needed == 7 and lv.par_time == 45
    assert lv.frog_start == (1, 0) and lv.snake_starts == ((0, 1),)
    assert lv.pads == {(1, 0), (2, 0), (0, 1), (1, 1)}


def test_field_cell_size_fits_all_planned_levels():
    from jebik import config
    from jebik.scenes.game_view import cell_size, field_rect
    sizes = [(12, 8), (14, 9), (16, 10), (18, 12), (14, 9), (16, 10), (18, 11), (20, 13),
             (16, 10), (18, 11), (20, 12), (22, 14)]
    for w, h in sizes:
        lv = make_level(["F" + "O" * (w - 1)] + ["O" * w] * (h - 1))
        cs = cell_size(lv)
        assert cs >= 64, (w, h, cs)          # the spec's base cell always fits
        r = field_rect(lv, cs)
        assert r.left >= 0 and r.right <= config.SCREEN_W
        assert r.top >= config.HUD_H and r.bottom <= config.SCREEN_H
    assert cell_size(make_level(["F" + "O" * 11] + ["O" * 12] * 7)) == config.MAX_CELL


def test_nearby_snake_retreats_after_water_respawn():
    w = make_world(["OOOOOOO", "F#OOOOO"], enemies=False)
    snake = Snake(level=w.level, rng=random.Random(0), cells=[(4, 0), (5, 0)])
    w.enemies.append(snake)
    w.request_move(1)                           # splash
    run(w, config.HOP_TIME + config.SPLASH_TIME + 0.05)
    assert snake.retreat > 0 or snake.mode == "retreat"

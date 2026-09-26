"""Water levels 1-1..1-4: parse, match the TZ tables, playable, fair and solvable."""
import pytest
from conftest import run

from jebik.game.grid import bfs_distances, manhattan
from jebik.game.world import World
from jebik.i18n import LANGS, t
from jebik.worlds import catalog, world_by_id

TABLE = {   # id: (size, flies, tobi, enemies)
    "1-2": ((14, 9), 7, 140, {"snake", "pike"}),
    "1-3": ((16, 10), 9, 130, {"snake", "pike", "heron"}),
    "1-4": ((18, 12), 12, 120, {"snake", "whale"}),
}


@pytest.mark.parametrize("lid", sorted(TABLE))
def test_level_matches_tz(lid):
    lv = catalog.load_level(lid)
    size, flies, tobi, kinds = TABLE[lid]
    assert (lv.width, lv.height) == size and lv.flies_needed == flies and lv.tobi_time == tobi
    assert {s.kind for s in lv.spawns} == kinds
    assert (lv.boss == "whale") == (lid == "1-4")


def test_water_levels_are_playable():
    assert set(world_by_id("water").playable) >= {1, 2, 3, 4}


@pytest.mark.parametrize("lid", ["1-1", *sorted(TABLE)])
def test_level_is_solvable_and_start_is_safe(lid):
    lv = catalog.load_level(lid)
    w = World(lv, seed=4, auto_spawn=False)
    dist = bfs_distances(lv.frog_start, w.tiles.neighbors)
    pads = [c for c in lv.cells() if w.tiles.standable(c)]
    assert len(dist) >= 0.9 * len(pads)             # (almost) every pad reachable by hops
    assert len(dist) >= 3 * lv.flies_needed
    for s in lv.spawns:
        if s.cell is not None:
            assert manhattan(s.cell, lv.frog_start) >= 6
    # nothing hurts the frog in the first seconds if she stays put
    run(w, 2.5)
    assert w.hearts == w.rules.hearts


def test_pike_lives_in_water():
    for lid in ("1-2", "1-3"):
        lv = catalog.load_level(lid)
        pike = next(s for s in lv.spawns if s.kind == "pike")
        assert pike.cell in lv.holes


def test_whale_strings_and_icon():
    for key in ("water.boss", "water.whale_hit", "water.hint.whale"):
        assert all(t(key, lang) for lang in LANGS)
    import pygame as pg
    from jebik.art.world_art import art_for
    pg.init()
    icon = art_for("water").boss_icon("whale", 44)
    assert icon is not None and icon.get_size() == (44, 44)

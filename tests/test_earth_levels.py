"""Earth levels 2-1..2-4: TZ numbers, fair starts, everything reachable."""
import pytest
from conftest import run

from jebik import config
from jebik.game.grid import DIRS, bfs_distances, manhattan
from jebik.game.world import World
from jebik.worlds import catalog
from jebik.worlds.earth.hedgehog import clear_line

TZ = {  # id: (size, flies, tobi, enemy kinds)
    "2-1": ((14, 9), 10, 115, {"hedgehog"}),
    "2-2": ((16, 10), 12, 105, {"hedgehog", "fox"}),
    "2-3": ((18, 11), 14, 95, {"hedgehog", "fox", "mole"}),
    "2-4": ((20, 13), 16, 85, {"hedgehog", "boar"}),
}


@pytest.mark.parametrize("lid", sorted(TZ))
def test_level_matches_tz_and_is_playable(lid):
    lv = catalog.load_level(lid)
    size, flies, tobi, kinds = TZ[lid]
    assert (lv.width, lv.height) == size and lv.flies_needed == flies and lv.tobi_time == tobi
    assert {s.kind for s in lv.spawns} == kinds
    assert catalog.is_playable(lid) and lv.par_time < lv.tobi_time


def test_boss_level_has_boar_and_three_stumps():
    lv = catalog.load_level("2-4")
    assert lv.boss == "boar" and len(lv.obstacles) == 3
    w = World(lv, seed=1)
    assert {(x, y) for x in (13, 14) for y in (6, 7)} == w.boss.body()
    assert all(w.tiles.standable(c) for c in w.boss.body())


@pytest.mark.parametrize("lid", sorted(TZ))
def test_every_tile_reachable_and_start_is_safe(lid):
    lv = catalog.load_level(lid)

    def moves(c):
        for dx, dy in DIRS:
            for k in (1, 2):
                n = (c[0] + dx * k, c[1] + dy * k)
                if n in lv.pads:
                    yield n
    dist = bfs_distances(lv.frog_start, moves)
    assert set(lv.pads) <= set(dist)
    # plain hops (no super jump) reach almost everything
    walk = bfs_distances(lv.frog_start, lambda c: (n for n in lv.pad_neighbors(c)))
    assert len(walk) >= 0.95 * len(lv.pads)
    w = World(lv, seed=3, auto_spawn=False)
    for s in lv.spawns:
        assert s.cell in lv.pads
        assert manhattan(s.cell, lv.frog_start) >= 5
        if s.kind == "hedgehog":
            assert clear_line(w, s.cell, lv.frog_start, 99) is None


@pytest.mark.parametrize("lid", sorted(TZ))
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_standing_still_at_start_is_safe_for_a_few_seconds(lid, seed):
    w = World(catalog.load_level(lid), seed=seed)
    run(w, 3.0)
    assert w.hearts == config.START_HEARTS and w.state == "playing"

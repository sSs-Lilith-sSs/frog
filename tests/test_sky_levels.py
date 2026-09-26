"""Sky levels 3-1..3-4: TZ numbers, playable, safe start, reachable clouds."""
import pytest
from conftest import run

from jebik import i18n
from jebik.game.grid import bfs_distances, step
from jebik.game.world import World
from jebik.worlds import catalog

TZ = {  # id: (size, flies, tobi, enemies)
    "3-1": ((16, 10), 14, 80, {"swallow"}),
    "3-2": ((18, 11), 16, 72, {"swallow", "hawk"}),
    "3-3": ((20, 12), 18, 66, {"swallow", "hawk", "crow"}),
    "3-4": ((22, 14), 20, 60, {"jesus", "swallow"}),
}


@pytest.mark.parametrize("lid", sorted(TZ))
def test_level_matches_tz_and_is_playable(lid):
    lv = catalog.load_level(lid)
    size, flies, tobi, kinds = TZ[lid]
    assert (lv.width, lv.height) == size
    assert lv.flies_needed == flies and lv.tobi_time == tobi
    assert {s.kind for s in lv.spawns} == kinds
    assert catalog.is_playable(lid)
    assert (lv.boss == "jesus") == (lid == "3-4")


@pytest.mark.parametrize("lid", sorted(TZ))
def test_level_is_solvable(lid):
    lv = catalog.load_level(lid)
    start = lv.frog_start
    moving = {m.row for m in lv.moving_rows}
    assert start in lv.pads and start not in lv.unstable and start[1] not in moving
    assert lv.moving_rows or lid == "3-4"
    assert lv.unstable

    def moves(c):
        for d in range(4):
            for k in (1, 2):                  # hops and super jumps
                n = step(c, d, k)
                if n in lv.pads:
                    yield n
    reach = bfs_distances(start, moves)
    assert len(reach) == len(lv.pads)         # every cloud can be reached
    fixed = [c for c in lv.pads if c not in lv.unstable and c[1] not in moving]
    assert len(fixed) > lv.width * lv.height * 0.6


def test_boss_level_layout():
    lv = catalog.load_level("3-4")
    assert lv.cell == 50 and lv.top_reserve >= 150


@pytest.mark.parametrize("lid", sorted(TZ))
def test_safe_start_and_long_run(lid):
    w = World(catalog.load_level(lid), seed=11)
    run(w, 1.5)
    assert w.hearts == 3                      # nothing can reach the frog in the first moments
    for _ in range(60 * 30):
        w.update(1 / 60)
        w.drain_events()


def test_sky_strings():
    for lang in ("ua", "en", "ru"):
        assert i18n.t("sky.sasat", lang) == "SASAT!"
    assert i18n.t("sky.boss", "ua") == "Ісус"

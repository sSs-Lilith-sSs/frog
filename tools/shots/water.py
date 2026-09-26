"""Water-world screenshots: 1-2 pike, 1-3 heron shadow + pike bubbles,
1-4 whale surfaced (frog on its back) and the fountain warning.
Level 1-1 is covered by the core flow."""
from __future__ import annotations

from shot_driver import Driver


def _put(world, cell, facing=1) -> None:
    f = world.frog
    f.cell = f.hop_from = f.hop_to = f.last_safe = cell
    f.facing = facing


def _enemy(world, kind):
    return next(e for e in world.enemies if e.kind == kind)


def shots(d: Driver) -> None:
    from jebik.worlds.water import pike as pk

    # --- 1-2: the level, then the pike lunging out of its pond
    g = d.play("1-2", seed=5)
    d.shot("water_01_level_1_2")
    w = g.world
    _put(w, (5, 4))
    pike = _enemy(w, "pike")
    pike.state, pike.timer = pk.HIDDEN, 0.0
    d.run(0.33 + 0.8 + 0.18)
    d.shot("water_02_pike_lunge")

    # --- 1-3: heron shadow on the frog + pike bubbles next to her pad
    g = d.play("1-3", seed=5)
    w = g.world
    _put(w, (5, 4), facing=0)
    pike = _enemy(w, "pike")
    pike.state, pike.timer = pk.HIDDEN, 0.0
    _enemy(w, "heron").timer = 0.25
    d.run(0.95)
    d.shot("water_03_heron_pike")

    # --- 1-4: the whale surfaced, the frog on its back aiming at the blowhole
    g = d.play("1-4", seed=5)
    w = g.world
    whale = w.boss
    _put(w, (8, 5))
    whale.start_attack(w, "surface")
    _put(w, (7, 8))
    d.run(0.8)
    d.shot("water_04_whale_zone")
    d.run(0.8)
    _put(w, (7, 5), facing=1)
    d.run(0.3)
    d.shot("water_05_whale_back")

    # --- 1-4: fountain warning (dashed line) and the jet
    g = d.play("1-4", seed=6)
    w = g.world
    w.boss.start_attack(w, "fountain")
    d.run(0.55)
    d.shot("water_06_fountain_warn")
    d.run(0.5)
    d.shot("water_07_fountain_jet")
    w.boss.start_attack(w, "gulp")
    d.run(1.2)
    d.shot("water_08_gulp")
    d.go_menu()

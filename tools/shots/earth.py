"""Earth-world screenshots (file names start with ``earth_``)."""
from __future__ import annotations

from shot_driver import Driver

from jebik.worlds.earth import boar as boar_logic
from jebik.worlds.earth import hedgehog as hh
from jebik.worlds.earth import mole as ml


def _enemy(world, kind):
    return next(e for e in world.enemies if e.kind == kind)


def shots(d: Driver) -> None:
    # --- 2-1: hedgehog rolling along the frog's row, one crumbling tile
    g = d.play("2-1", seed=5)
    w = g.world
    h = _enemy(w, "hedgehog")
    fx, fy = w.frog.cell
    h.pos, h.cell, h.next_cell = (fx + 4.0, float(fy)), (fx + 4, fy), None
    h.state, h.roll_dir, h.facing, h.spin = hh.ROLL, (-1, 0), (-1, 0), 1.3
    d.run(0.12)
    d.shot("earth_01_level_2-1")
    d.go_menu()

    # --- 2-3: hedgehog, fox, mole mound + tremor, crumbling ground
    g = d.play("2-3", seed=5)
    w = g.world
    for cell in sorted(w.level.unstable)[:1]:
        w.events.extend(w.tiles.on_land(cell))
    m = _enemy(w, "mole")
    m.state, m.timer = ml.DIG, 0.0
    d.run(1.2)
    d.shot("earth_02_level_2-3")
    fx, fy = w.frog.cell
    m.cell, m.next_cell = (fx, fy), None
    m.pos = (float(fx), float(fy))
    m.state, m.timer, m.target = ml.TREMOR, 0.8, (fx, fy)
    d.run(0.3)
    d.shot("earth_03_mole_tremor")
    d.go_menu()

    # --- 2-4: boar telegraphs a charge down its lane
    g = d.play("2-4", seed=5)
    w = g.world
    b = w.boss
    b.state, b.timer, b.dir, b._tell = boar_logic.TELL, 0.7, (-1, 0), 1.1
    d.run(0.25)
    d.shot("earth_04_boar_charge")
    # ... runs into a stump: stunned, vulnerable
    b.pos = (4.0, 6.0)
    b.dir = (-1, 0)
    b._stop(w, (4, 6), [(3, 6)])
    d.run(0.5)
    d.shot("earth_05_boar_stunned")
    d.go_menu()

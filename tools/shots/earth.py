"""Earth-world screenshots (earth agent: extend freely; file names start with ``earth_``)."""
from __future__ import annotations

from shot_driver import Driver


def shots(d: Driver) -> None:
    g = d.play("2-1", seed=5)
    w = g.world
    # show the crumbling-ground warning on one 'U' tile
    for cell in sorted(w.level.unstable)[:1]:
        w.events.extend(w.tiles.on_land(cell))
    d.run(0.9)
    d.shot("earth_01_placeholder")
    d.go_menu()

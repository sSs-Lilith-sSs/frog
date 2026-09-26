"""Sky-world screenshots (sky agent: extend freely; file names start with ``sky_``)."""
from __future__ import annotations

from shot_driver import Driver


def shots(d: Driver) -> None:
    g = d.play("3-1", seed=5, settle=2.8)       # a moving row mid-slide
    w = g.world
    for cell in sorted(w.level.unstable)[:1]:   # a melting cloud
        w.events.extend(w.tiles.on_land(cell))
    d.run(1.0)
    d.shot("sky_01_placeholder")
    d.go_menu()

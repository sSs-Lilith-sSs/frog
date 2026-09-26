"""Sky-world screenshots (file names start with ``sky_``)."""
from __future__ import annotations

from shot_driver import Driver


def _enemy(g, kind):
    return next(e for e in g.world.enemies if e.kind == kind)


def shots(d: Driver) -> None:
    # 3-1: swallow arrow on the edge, a drifting row, a melting cloud
    g = d.play("3-1", seed=5, settle=1.0)
    w = g.world
    sw = _enemy(g, "swallow")
    sw.timer = 0.05
    for cell in sorted(w.level.unstable)[:1]:
        w.events.extend(w.tiles.on_land(cell))
    d.run(0.6)
    d.shot("sky_01_swallow_warn")
    d.run(0.55)
    d.shot("sky_02_swallow_fly")

    # 3-3: hawk winding up, crow cawing
    g = d.play("3-3", seed=4, settle=1.5)
    w = g.world
    hawk, crow = _enemy(g, "hawk"), _enemy(g, "crow")
    fx, fy = w.frog.cell
    hawk.pos = (fx + 1.6, fy - 0.6)
    crow.caw_timer = 0.0
    crow.state, crow.timer = "sit", 1.0
    d.run(0.25)
    d.shot("sky_03_hawk_crow")

    # 3-4: the boss — beams, then the halo boomerang
    g = d.play("3-4", seed=3, settle=1.0)
    w = g.world
    boss = w.boss
    boss.attack_n = 1
    boss._begin_beams(w)
    d.run(0.7)
    d.shot("sky_04_boss_beams")
    boss.state, boss.beam_on, boss.beam_cells = "idle", False, ()
    boss.timer = 99
    boss._begin_halo(w)
    d.run(1.7)
    d.shot("sky_05_boss_halo")
    boss.halo_phase = "home"
    boss._multiply(w)
    boss.state, boss.timer = "multiply", 0.5
    d.run(0.3)
    d.shot("sky_06_boss_multiply")
    boss._begin_rebuild(w)
    d.run(0.8)
    d.shot("sky_07_boss_rebuild")
    d.run(1.0)
    boss.state, boss.timer, boss.vanish, boss.appear = "halo", 99, (), ()
    boss.halo_phase, boss.halo_t, boss.halo_from = "bonk", 0.0, w.frog.pos()   # caught halo flies back
    d.run(0.8)
    d.shot("sky_08_boss_sasat")
    boss.hp = 1
    boss.state, boss.timer = "idle", 99
    boss.open_window(1.0)
    boss.take_hit(w)
    d.run(1.0)
    d.shot("sky_09_boss_sad")
    d.go_menu()

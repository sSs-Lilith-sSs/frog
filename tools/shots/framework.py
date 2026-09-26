"""Framework screenshots: records, TOBI PIZDA HUD, boss pill mock, cutscene, credits."""
from __future__ import annotations

import math

from shot_driver import Driver, pg

from jebik import progression, story
from jebik.game.enemy import Boss, Telegraph, register_enemy
from jebik.game.grid import parse_level
from jebik.game.rules import EZZZ, TOBI

MOCK_LEVEL = """
id: 1-4
world: water
flies_needed: 12
tobi_time: 120
boss: mock_boss @ 8 3 hp=3
---
OOOOOOOOOOOOOOOOOO
OO##OOOOOOOOOO##OO
OO##OOOOO##OOO##OO
OOOOOOOOO##OOOOOOO
OOOOO#OOOOOOOOOOOO
OOOOO##OOOOOO#OOOO
OOOOOOOOOOOOO##OOO
O##OOOOOOOOOOOOOOO
O##OOOOOF##OOOOO#O
OOOOOOOOO#OOOOOO#O
OOOO#OOOOOOOO##OOO
OOOOOOOOOOOOOOOOOO
"""


@register_enemy("mock_boss")
class MockBoss(Boss):
    """Screenshot-only boss: drifts, shows a zone + line telegraph."""
    name_key = "boss.generic"
    hit_text_key = "sky.sasat"

    def update(self, dt, world) -> None:
        super().update(dt, world)
        self.pos = (8 + math.sin(self.anim * 0.7) * 2.5, 3 + math.cos(self.anim * 0.9) * 0.6)

    def telegraphs(self) -> list[Telegraph]:
        p = (self.anim * 0.4) % 1.0
        zone = tuple((x, y) for x in range(12, 15) for y in range(7, 10))
        line = tuple((x, 5) for x in range(0, 18))
        return [Telegraph("zone", zone, p), Telegraph("line", line, p, direction=1)]


def shots(d: Driver) -> None:
    app = d.app
    app.touch_seen = False                # the core flow tapped the screen
    prof = app.profile
    # --- records: a few runs of two profiles
    other = app.save.find("Жабка") or app.save.create_profile("Жабка")
    app.save.current = prof.name
    runs = ((prof, ((1880, 52.3, 3), (1400, 80.1, 2))), (other, ((1650, 61.0, 3), (900, 99.9, 1))))
    for p, rs in runs:
        for score, t, stars in rs:
            p.record_result(EZZZ, "1-1", score, stars, t)
    other.record_result(EZZZ, "2-1", 2300, 2, 101.0)
    from jebik.scenes.records import RecordsScene
    app.scenes.push(RecordsScene(app))
    d.settle(0.5)
    d.key(pg.K_RIGHT)                     # Total -> 1-1
    d.settle(0.5)
    d.shot("17_records")
    d.go_menu()

    # --- TOBI PIZDA: finish every playable EZZZ level -> unlocked
    for lid in ("1-1", "2-1", "3-1"):
        prof.record_result(EZZZ, lid, 1500, 3, 60.0)
    progression.refresh_unlocks(prof)
    app.difficulty = TOBI
    from jebik.scenes.level_select import LevelSelectScene
    app.scenes.push(LevelSelectScene(app))
    d.settle(0.6)
    d.shot("18_level_select_tobi")
    g = d.play("1-1", seed=7)
    w = g.world
    for e in w.enemies:
        e.retreat = 1e9
    f = w.frog
    f.facing = 1
    ahead = (f.cell[0] + 1, f.cell[1])
    w.flies.flies = [fl for fl in w.flies.flies if fl.cell != ahead]
    w.flies.spawn_at("gold", ahead, rest=5)
    d.run(0.6)
    d.key(pg.K_SPACE, wait=1 / 60)
    d.run(0.7)
    d.shot("19_tobi_hud")
    app.difficulty = EZZZ

    # --- boss HUD pill with a mock boss (zone + line telegraphs, SASAT! popup)
    level = parse_level(MOCK_LEVEL)
    g = d.play("1-4", seed=3, level=level, settle=1.8)
    boss = g.world.boss
    boss.open_window()
    boss.take_hit(g.world)                # -> BOSS_HIT event, «SASAT!» popup
    boss.open_window()
    d.run(0.35)
    d.shot("20_boss_pill_mock")
    d.go_menu()

    # --- cutscene (intro card, text fully typed) and the credits roll
    from jebik.scenes.cutscene import CutsceneScene
    cards = list(story.INTRO) + story.world_cards("water")
    app.scenes.push(CutsceneScene(app, cards, on_done=lambda: app.scenes.pop()))
    d.settle(3.5)
    d.shot("21_cutscene")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)
    app.scenes.push(CutsceneScene(app, story.credits_cards(), on_done=lambda: app.scenes.pop()))
    d.settle(12.0)
    d.shot("22_credits")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)

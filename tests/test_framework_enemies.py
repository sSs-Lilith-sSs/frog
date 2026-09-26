"""Enemy registry, the Enemy protocol inside World, and the boss framework."""
import pytest
from conftest import make_world, run

from jebik import config
from jebik.game import events as ev
from jebik.game.enemy import (Boss, Enemy, Telegraph, create_enemy, enemy_class,
                              register_enemy, registered_kinds)
from jebik.game.grid import RIGHT, Spawn
from jebik.worlds.water.snake import Snake


@register_enemy("test_rock")
class Rock(Enemy):
    """Sits still; hurts on contact; shows a zone telegraph."""
    def telegraphs(self):
        return [Telegraph("zone", ((0, 0),), 0.5)]


@register_enemy("test_boss")
class TestBoss(Boss):
    name_key = "boss.generic"
    hit_text_key = "sky.sasat"

    def hurts(self, world, frog_pos):
        return False

    def tongue_hit(self, world, line):
        cell = (round(self.pos[0]), round(self.pos[1]))
        return line.index(cell) if cell in line else None


# ---------------------------------------------------------------- registry
def test_registry_knows_world_enemies_and_test_ones():
    kinds = registered_kinds()
    assert "snake" in kinds and "test_rock" in kinds
    assert enemy_class("snake") is Snake


def test_registry_rejects_duplicates_and_unknown():
    with pytest.raises(ValueError):
        @register_enemy("snake")
        class Other(Enemy):
            pass
    with pytest.raises(KeyError):
        enemy_class("no_such_enemy")
    with pytest.raises(TypeError):
        register_enemy("test_bad")(int)


def test_level_spawns_create_registered_enemies():
    w = make_world(["FOOOR"], header="spawn: R=test_rock\nenemies: test_rock @ 2 0", enemies=True)
    assert [type(e) for e in w.enemies] == [Rock, Rock]
    assert w.enemies[0].pos == (4.0, 0.0) and w.enemies[1].pos == (2.0, 0.0)


def test_snake_is_created_through_the_registry():
    w = make_world(["S#OF"], enemies=True)
    assert isinstance(w.enemies[0], Snake) and w.enemies[0].world is w


def test_contact_enemy_hurts_via_protocol():
    w = make_world(["FOR"], header="spawn: R=test_rock", enemies=True)
    w.request_move(RIGHT)
    run(w, 0.3)
    w.request_move(RIGHT)
    run(w, 0.2)
    assert w.hearts == config.START_HEARTS - 1 and w.frog.invuln > 0
    assert any(e.kind == ev.HIT and e.value == "test_rock" for e in w.drain_events())


def test_world_api_for_enemies():
    w = make_world(["FOO#"])
    rock = create_enemy(w, Spawn("test_rock", (3, 3)))
    w.enemies.append(rock)
    assert w.frog_target == (0, 0)
    w.haste(1.5, 2.0)
    assert w.enemy_speed == 1.5
    run(w, 2.1)
    assert w.enemy_speed == 1.0
    assert w.hurt_frog(rock) and w.hearts == config.START_HEARTS - 1
    assert not w.hurt_frog(rock)                    # invulnerable now
    w.frog.invuln = 0
    w.frog.state = "idle"
    assert w.push_frog(RIGHT, 2)
    run(w, 0.4)
    assert w.frog.cell == (2, 0)
    w.push_frog(RIGHT)                              # into the water
    run(w, 0.4)
    assert w.frog.state == "splash"


# ---------------------------------------------------------------- bosses
def _boss_world(needed: int = 2):
    w = make_world(["FOOOO", "OOOOO"], flies_needed=needed, header="boss: test_boss @ 3 0",
                   enemies=True)
    return w, w.boss


def test_boss_needs_window_and_three_hits():
    w, boss = _boss_world()
    assert boss.hp == config.BOSS_HP and not boss.vulnerable
    assert not boss.take_hit(w)
    for i in range(3):
        boss.open_window()
        assert boss.take_hit(w)
        assert not boss.take_hit(w)                 # the window closes on a hit
    assert boss.hp == 0 and boss.defeated
    kinds = [e.kind for e in w.drain_events()]
    assert kinds.count(ev.BOSS_HIT) == 3 and ev.BOSS_DEFEATED in kinds


def test_exit_needs_exact_flies_and_defeated_boss():
    w, boss = _boss_world()
    w.eaten = w.needed
    w._become_full()
    assert w.full and w.exit_cell is None and not w.exit_ready
    for _ in range(3):
        boss.open_window()
        boss.take_hit(w)
    assert w.exit_cell is not None


def test_exit_when_boss_falls_first():
    w, boss = _boss_world(needed=1)
    for _ in range(3):
        boss.open_window(5)
        boss.take_hit(w)
    assert w.exit_cell is None                      # flies still missing
    w.flies.spawn_at("fly", (1, 0), rest=9)
    w.request_move(RIGHT)
    run(w, 0.3)
    assert w.full and w.exit_cell is not None


def test_tongue_hits_boss_in_its_window():
    w, boss = _boss_world()
    w.frog.cell = (1, 0)
    w.frog.facing = RIGHT
    boss.open_window(5)
    w.request_tongue()
    run(w, 0.3)
    assert boss.hp == config.BOSS_HP - 1
    boss.window = 0
    run(w, 0.5)
    w.request_tongue()
    run(w, 0.3)
    assert boss.hp == config.BOSS_HP - 1            # not vulnerable -> no damage


def test_boss_hp_from_level_params_and_enrage():
    w = make_world(["FOO"], flies_needed=4, header="boss: test_boss @ 2 0 hp=5", enemies=True)
    assert w.boss.hp == 5 and not w.boss.enraged(w)
    w.eaten = 2
    assert w.boss.enraged(w)
    assert w.level.boss == "test_boss"

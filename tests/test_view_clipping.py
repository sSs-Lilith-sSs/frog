"""Field-layer drawing stays inside the field frame; overlays (AIR, boss) do not."""
import pygame as pg
import pytest
from conftest import make_level, make_world

from jebik import config
from jebik.art.common import clipped
from jebik.art.enemy_art import EnemyArt, register_enemy_art
from jebik.art.field import FieldRenderer
from jebik.game.enemy import AIR, GROUND, UNDER

RED = (255, 0, 0)


def test_clipped_intersects_and_restores():
    s = pg.Surface((100, 100))
    s.set_clip(pg.Rect(10, 10, 50, 50))
    with clipped(s, pg.Rect(30, 30, 100, 100)):
        assert s.get_clip() == pg.Rect(30, 30, 30, 30)
    assert s.get_clip() == pg.Rect(10, 10, 50, 50)
    with clipped(s, None):
        assert s.get_clip() == pg.Rect(10, 10, 50, 50)
    with pytest.raises(RuntimeError):
        with clipped(s, pg.Rect(0, 0, 5, 5)):
            raise RuntimeError
    assert s.get_clip() == pg.Rect(10, 10, 50, 50)


@register_enemy_art("test_clip_blob")
class BlobArt(EnemyArt):
    def draw(self, surf, enemy, off):
        surf.fill(RED)                                   # paints everywhere it may


class Blob:
    kind = "test_clip_blob"
    alive = True
    boss = False
    pos = (0.0, 0.0)

    def __init__(self, layer):
        self.layer = layer

    def telegraphs(self):
        return []


class Stub:
    def __init__(self, *enemies):
        self.enemies = list(enemies)


@pytest.fixture
def view():
    from jebik.scenes.game_view import GameView
    return GameView(make_level(["FOOO", "OOOO", "OOOO"]))


@pytest.mark.parametrize("layer, inside_only", [(UNDER, True), (GROUND, True), (AIR, False)])
def test_enemy_layers_clip_to_the_field(view, layer, inside_only):
    surf = pg.Surface((config.SCREEN_W, config.SCREEN_H))
    view._draw_enemies(surf, Stub(Blob(layer)), layer, (0, 0))
    f = view.field
    assert surf.get_at(f.center)[:3] == RED
    outside = surf.get_at((f.left - 5, f.top - 5))[:3]
    assert (outside != RED) if inside_only else (outside == RED)
    assert surf.get_clip() == surf.get_rect()                  # restored


def test_clip_follows_the_screen_shake(view):
    surf = pg.Surface((config.SCREEN_W, config.SCREEN_H))
    view._draw_enemies(surf, Stub(Blob(GROUND)), GROUND, (7, 0))
    f = view.field
    assert surf.get_at((f.right + 3, f.centery))[:3] == RED     # the frame moved right by 7
    assert surf.get_at((f.left + 3, f.centery))[:3] != RED


def test_art_can_force_clipping(view):
    art = view.art_of("test_clip_blob")
    try:
        art.clip = True
        assert art.clipped(Blob(AIR))
        art.clip = False
        assert not art.clipped(Blob(GROUND))
    finally:
        art.clip = None


class WideTiles(FieldRenderer):
    """Tiles three cells wide (like the sky's wind-streaked clouds)."""

    def tile_sprite(self, tile, cell):
        img = pg.Surface((self.cs * 3, self.cs), pg.SRCALPHA)
        img.fill(RED)
        return img


def test_moving_rows_stay_inside_the_frame():
    w = make_world(["FOOOO", "OOOOO", "OOOOO"], header="moving: 1 right 2.0")
    cs = 40
    rect = pg.Rect(200, 100, 5 * cs, 3 * cs)
    fr = WideTiles(w.level, cs, rect)
    surf = pg.Surface((800, 400))
    fr.draw_tiles(surf, w, (0, 0))
    row = lambda r: rect.y + r * cs + cs // 2                  # noqa: E731
    assert surf.get_at((rect.left - 10, row(1)))[:3] != RED    # moving row: clipped
    assert surf.get_at((rect.left + 10, row(1)))[:3] == RED
    assert surf.get_at((rect.left - 10, row(0)))[:3] == RED    # still rows: as drawn


def test_jesus_floats_clear_of_the_field_and_the_boss_pill():
    """3-4: his cloud keeps clear air above the field frame and his halo stays
    under the HUD boss pill (measured on the real sprite)."""
    from jebik.game.world import World
    from jebik.scenes.game_view import GameView
    from jebik.worlds import catalog
    lv = catalog.load_level("3-4")
    w = World(lv, seed=1)
    view = GameView(lv)
    boss = w.boss
    layer = pg.Surface((config.SCREEN_W, config.SCREEN_H), pg.SRCALPHA)
    view.art_of(boss.kind).draw(layer, boss, (0, 0))
    box = layer.get_bounding_rect(min_alpha=160)               # ignore the soft glow
    frame_top = view.field.top - 12
    from jebik.scenes.boss_pill import PILL_H
    pill_bottom = config.HUD_H + 12 + 22 + PILL_H // 2          # hud.py draws the pill there
    assert frame_top - box.bottom >= 15
    assert box.top >= pill_bottom

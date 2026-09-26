#!/usr/bin/env python3
"""Headless screenshots of every screen, driven by scripted input.

    python3 tools/screenshot.py [out_dir] [--lang ua|en|ru]

``out_dir`` defaults to ./screenshots. ``--lang`` picks the language of all
screens except the three main-menu shots (UA / EN / RU are always taken).
``--only <hook>`` runs just the core flow + one hook from ``tools/shots/``.

Runs with SDL's dummy video/audio drivers and a throw-away save directory.
World packages add their shots in ``tools/shots/<world>.py`` (``shots(d)``).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from shot_driver import ARROW, DT, ROOT, Driver, pg  # noqa: E402  (sets up SDL + save dir)

from jebik.game import frog as fs  # noqa: E402
from jebik.game.grid import step  # noqa: E402

HOOKS_DIR = Path(__file__).resolve().parent / "shots"


def run_hooks(d: Driver, only: str | None = None) -> None:
    """``tools/shots/<name>.py`` each define ``shots(driver)`` (framework first)."""
    files = sorted(HOOKS_DIR.glob("*.py"), key=lambda f: (f.stem != "framework", f.stem))
    for f in files:
        if f.stem.startswith("_") or (only and f.stem != only):
            continue
        spec = importlib.util.spec_from_file_location(f"shots_{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print(f"--- hook {f.stem}")
        mod.shots(d)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", nargs="?", default=str(ROOT / "screenshots"))
    ap.add_argument("--lang", choices=("ua", "en", "ru"), default="ua")
    ap.add_argument("--only", help="run only this hook from tools/shots/ after the core flow")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    d = Driver(out, splash=True)
    app = d.app
    app.set_lang(args.lang)

    # --- studio splash mid-animation (beams sweeping), then skip with a key
    d.settle(3.0)
    d.shot("00_splash")
    d.key(pg.K_SPACE)
    d.settle(0.6)

    # --- profile: first launch -> type a name (Cyrillic via TEXTINPUT)
    d.settle(0.5)
    d.type_text("Кыця")
    d.settle(0.3)
    d.shot("01_profile_create")
    d.key(pg.K_RETURN)
    d.settle(0.6)

    # --- main menu in EN (and RU)
    app.set_lang("en")
    d.settle(0.3)
    d.shot("04_main_menu_en")
    app.set_lang("ru")
    d.settle(0.3)
    d.shot("05_main_menu_ru")
    app.set_lang("ua")
    d.settle(0.1)
    d.shot("03_main_menu_ua")
    app.set_lang(args.lang)

    # --- profile list (second profile exists)
    app.save.create_profile("Жабка")
    app.save.current = "Кыця"
    from jebik.scenes.profile import ProfileScene
    app.scenes.push(ProfileScene(app, from_menu=True))
    d.settle(0.6)
    d.shot("02_profile_list")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)

    # --- settings (focus moved to the music choice)
    from jebik.scenes.settings import SettingsScene
    app.scenes.push(SettingsScene(app))
    d.settle(0.5)
    d.key(pg.K_DOWN)
    d.key(pg.K_DOWN)
    d.settle(0.3)
    d.shot("06_settings")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)

    # --- how to play
    from jebik.scenes.howto import HowToScene
    app.scenes.push(HowToScene(app))
    d.settle(0.6)
    d.shot("07_howto")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)

    # --- difficulty via the Play button (focused by default)
    d.key(pg.K_RETURN)
    d.settle(0.6)
    d.shot("08_difficulty")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)

    # --- level select
    from jebik.scenes.level_select import LevelSelectScene
    app.scenes.push(LevelSelectScene(app))
    d.settle(0.6)
    d.shot("09_level_select")
    d.key(pg.K_ESCAPE)
    d.settle(0.5)

    # --- gameplay: Play -> EZZZ -> level 1-1 (fixed seed for repeatable shots)
    from jebik.scenes.game_scene import GameScene
    from jebik.scenes.flow import go_menu
    app.scenes.push(GameScene(app, "1-1", seed=7))
    d.settle(2.0)                                  # start banner fades
    g = d.game
    w = g.world
    for enemy in w.enemies:            # keep the snake shy so the run is clean
        enemy.retreat = 1e9
    for k in (pg.K_RIGHT, pg.K_UP, pg.K_UP, pg.K_RIGHT, pg.K_RIGHT):
        d.key(k, wait=0.25)
    d.settle(0.4)
    # set up a catch two cells ahead so the tongue is visibly out
    f = w.frog
    f.facing = 1 if f.cell[0] < w.level.width - 3 else 3
    target = step(f.cell, f.facing, 2)
    for fly in list(w.flies.flies):
        if fly.cell in (step(f.cell, f.facing, 1), target):
            w.flies.flies.remove(fly)
    w.flies.spawn_at("fly", target, rest=5)
    # extra showcase: a golden fly, a dragonfly and a firefly somewhere
    free = [c for c in sorted(w.level.pads) if abs(c[0] - f.cell[0]) + abs(c[1] - f.cell[1]) > 3]
    for kind, c in zip(("gold", "firefly", "dragon"), (free[3], free[len(free) // 2], free[-6])):
        w.flies.spawn_at(kind, c, rest=8)
    d.key(pg.K_SPACE, wait=DT)
    d.run(0.13)                                    # Space waits 60 ms for an aim arrow
    d.shot("10_gameplay_tongue")
    d.settle(0.5)

    # --- pause
    d.key(pg.K_ESCAPE)
    d.settle(0.4)
    d.shot("11_pause")
    d.key(pg.K_ESCAPE)
    d.settle(0.4)

    # --- "Сита!": eat the last needed fly -> banner + lotus exit
    w.eaten = w.needed - 1
    f.facing = 1 if f.cell[0] < w.level.width - 2 else 3
    ahead = step(f.cell, f.facing, 1)
    for fly in list(w.flies.flies):
        if fly.cell == ahead:
            w.flies.flies.remove(fly)
    w.flies.spawn_at("fly", ahead, rest=5)
    d.key(pg.K_SPACE, wait=DT)
    d.run(0.9)
    d.shot("12_full_exit")

    # --- win: hop onto the exit from a neighbouring pad
    ex = w.exit_cell
    for dd in range(4):
        n = step(ex, (dd + 2) % 4)
        if n in w.level.pads:
            f.cell = f.hop_from = f.hop_to = n
            f.state = fs.IDLE
            key = ARROW[dd]
            break
    d.run(0.6)                                     # tongue cooldown over
    d.key(key, wait=0.3)
    d.settle(2.8)
    d.shot("13_win")

    # --- level select after winning 1-1 (stars + unlocked "soon" tile)
    go_menu(app)
    d.settle(0.5)
    app.scenes.push(LevelSelectScene(app))
    d.settle(0.6)
    d.shot("14_level_select_after_win")
    go_menu(app)
    d.settle(0.5)

    # --- lose: last heart, hop into water
    app.scenes.push(GameScene(app, "1-1", seed=3))
    d.settle(0.6)
    g = d.game
    w = g.world
    w.hearts = 1
    water_move = None
    for c in sorted(w.level.pads):
        for dd in range(4):
            if w.level.is_water(step(c, dd)):
                water_move = (c, dd)
                break
        if water_move:
            break
    c, dd = water_move
    w.frog.cell = w.frog.hop_from = w.frog.hop_to = c
    key = ARROW[dd]
    d.key(key, wait=0.2)
    d.settle(2.6)
    d.shot("15_lose")

    # --- touch controls: on-screen ⏸ / ⇧ buttons, superjump armed by a tap
    go_menu(app)
    d.settle(0.5)
    from jebik.scenes.touch_hud import SUPER_CENTER
    app.settings["touch"] = "on"
    app.scenes.push(GameScene(app, "1-1", seed=7))
    d.settle(2.0)
    fx, fy = SUPER_CENTER[0] / app.screen.get_width(), SUPER_CENTER[1] / app.screen.get_height()
    d.run(DT, [pg.event.Event(pg.FINGERDOWN, finger_id=1, touch_id=0, x=fx, y=fy, dx=0.0, dy=0.0)])
    d.run(0.2, [pg.event.Event(pg.FINGERUP, finger_id=1, touch_id=0, x=fx, y=fy, dx=0.0, dy=0.0)])
    d.shot("16_gameplay_touch")
    app.settings["touch"] = "auto"

    go_menu(app)
    d.settle(0.5)
    run_hooks(d, args.only)

    print(f"{len(d.shots)} screenshots in {out}")
    pg.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())

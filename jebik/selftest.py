"""Packaging self-check: ``python3 frog.py --selftest`` (or ``JEBIK_SELFTEST=1``).

Meant for the frozen build (PyInstaller) where a missing data file or a
dynamically imported module would only show up at runtime. It checks that
fonts and sounds are bundled, every world package and its art module import,
every playable level of every world loads, every enemy kind has its renderer,
and then plays each level for a moment through the real ``GameScene``.

Exit code 0 = all good. The report goes to stdout (if there is one — a
windowed ``.exe`` has none) and to ``<save dir>/selftest.log``.
"""
from __future__ import annotations

import os
import sys
import traceback

from . import config, paths

FRAMES_PER_LEVEL = 30


def _checks(log) -> list[str]:
    from .app import App
    from .art.enemy_art import has_art
    from .art.world_art import art_for
    from .worlds import all_worlds, catalog

    errors: list[str] = []

    def check(ok: bool, what: str) -> None:
        log(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            errors.append(what)

    log(f"frozen={paths.is_frozen()} package_dir={paths.package_dir()}")
    for f in (config.FONT_BOLD, config.FONT_REGULAR):
        check(f.is_file(), f"font {f.name}")
    for name in config.SFX_NAMES:
        check((config.AUDIO_DIR / f"sfx_{name}.wav").is_file(), f"sfx {name}")
    for fname in (*config.MUSIC_FILES.values(), config.INTRO_FANFARE):
        check((config.AUDIO_DIR / fname).is_file(), f"music {fname}")

    app = App(splash=False)
    check(bool(app.audio.sounds) or not app.audio.enabled, "sounds loaded")
    worlds = all_worlds()
    check([w.id for w in worlds] == ["water", "earth", "sky"], "worlds water/earth/sky")
    found = set(catalog.discovered())
    playable = catalog.playable_levels()
    log(f"discovered levels: {sorted(found)}")
    log(f"playable levels:   {playable}")
    for w in worlds:
        mine = [lid for lid in playable if lid.startswith(f"{w.index}-")]
        check(len(mine) == len(w.playable), f"world {w.id}: {len(mine)} playable level(s)")
        try:
            art_for(w.id)
            check(True, f"world {w.id}: art module")
        except Exception as exc:      # noqa: BLE001 - report, don't crash
            check(False, f"world {w.id}: art module ({exc!r})")

    from .scenes.game_scene import GameScene
    from .scenes.main_menu import MainMenuScene
    if app.save.profile is None:
        app.save.create_profile("selftest")
    app.scenes.reset(MainMenuScene(app), fade=False)
    for lid in playable:
        try:
            level = catalog.load_level(lid)
            missing = sorted({s.kind for s in level.spawns if not has_art(s.kind)})
            check(not missing, f"level {lid}: enemy art {missing or 'complete'}")
            g = GameScene(app, lid, seed=1)
            app.scenes.push(g, fade=False)
            for _ in range(FRAMES_PER_LEVEL):
                app.frame(1 / 60, [])
            app.scenes.reset(MainMenuScene(app), fade=False)
            check(True, f"level {lid}: plays ({level.width}x{level.height}, "
                        f"{len(level.spawns)} enemies)")
        except Exception as exc:      # noqa: BLE001
            check(False, f"level {lid}: {exc!r}")
            log(traceback.format_exc())
    return errors


def main() -> int:
    lines: list[str] = []

    def log(msg: str) -> None:
        lines.append(msg)
        if sys.stdout is not None:
            print(msg, flush=True)

    os.environ.setdefault("JEBIK_NO_SPLASH", "1")
    try:
        errors = _checks(log)
    except Exception:                 # noqa: BLE001
        log(traceback.format_exc())
        errors = ["crashed"]
    log("SELFTEST " + ("PASSED" if not errors else f"FAILED ({len(errors)} problem(s))"))
    try:
        out = paths.save_dir()
        out.mkdir(parents=True, exist_ok=True)
        (out / "selftest.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass
    return 0 if not errors else 1


def requested(argv: list[str] | None = None) -> bool:
    argv = sys.argv[1:] if argv is None else argv
    return "--selftest" in argv or bool(os.environ.get("JEBIK_SELFTEST"))

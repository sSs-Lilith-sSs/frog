#!/usr/bin/env python3
"""Headless QA soak of the real game: menus, settings, every level, TOBI PIZDA,
records, cutscenes, profiles and saves — driven with synthesized events.

    python3 tools/qa_soak.py                 # full soak (a few minutes)
    python3 tools/qa_soak.py --quick         # fewer runs per level
    python3 tools/qa_soak.py --runs 40 --only 3-4

Every exception is caught with its traceback; invariants (soft-locks, NaN
positions, enemies off the field, exit on a hole / unreachable, frog spawning
in hazards, frozen flies, missing sounds, text overflowing its panel in RU,
frame-time spikes, memory growth) are reported at the end. Exit code 1 if
anything was found. SDL runs on dummy drivers, saves go to a temp folder.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
import traceback
import tracemalloc
from collections import Counter, defaultdict
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.pop("JEBIK_NO_SPLASH", None)
os.environ.pop("JEBIK_AUTOQUIT", None)
SAVE_DIR = Path(tempfile.mkdtemp(prefix="jebik_qa_"))
os.environ["JEBIK_SAVE_DIR"] = str(SAVE_DIR)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

sys.modules.setdefault("qa_soak", sys.modules[__name__])   # qa_flows imports us: one module, one SAVE_DIR

import pygame as pg  # noqa: E402

from jebik.game.rules import EZZZ  # noqa: E402

DT = 1 / 60
ARROWS = {0: pg.K_UP, 1: pg.K_RIGHT, 2: pg.K_DOWN, 3: pg.K_LEFT}
SPIKE_MS = 120.0
LANG = "ru"                  # the QA language (level play is not repeated per language)


def kev(t, k, mod=0, uni=""):
    return pg.event.Event(t, key=k, mod=mod, unicode=uni, scancode=0)


class Harness:
    def __init__(self, splash: bool = False):
        self.issues: dict[tuple, dict] = {}
        self.causes: dict = defaultdict(Counter)      # (level, difficulty) -> hits / falls / boss hits
        self.frames = 0
        self.frame_ms: list[float] = []
        self.spikes: list[tuple[float, str]] = []
        self.draw_every = 1
        self.ctx = "boot"
        self.app = None
        self.new_app(splash)

    # ------------------------------------------------------------ app / hooks
    def new_app(self, splash: bool = False):
        from jebik.app import App
        if pg.mixer.get_init():
            pg.mixer.stop()                    # the old App's sounds must not be freed mid-play
        self.app = App(splash=splash)       # no pg.quit(): cached fonts must stay valid
        self.app.set_lang(LANG)
        audio = self.app.audio
        orig_play = audio.play

        def play(name, volume=1.0):
            ok = orig_play(name, volume)
            if not ok and audio.enabled and not name.endswith((".boss_hit", ".boss_defeated")):
                self.issue("missing_sound", name)
            return ok
        audio.play = play
        from jebik.ui import widgets
        widgets.set_sound_hook(play)
        return self.app

    def issue(self, kind: str, detail: str, tb: str = ""):
        key = (kind, detail[:160])
        rec = self.issues.setdefault(key, {"n": 0, "ctx": self.ctx, "tb": tb})
        rec["n"] += 1

    # ------------------------------------------------------------ frames
    def frame(self, events=(), dt=DT):
        app = self.app
        self.frames += 1
        draw = self.frames % self.draw_every == 0
        mgr = app.scenes
        before = mgr.top
        t0 = time.perf_counter()
        if draw:
            app.frame(dt, list(events))
        else:
            orig = mgr.draw
            mgr.draw = lambda surf: None
            try:
                app.frame(dt, list(events))
            finally:
                mgr.draw = orig
        ms = (time.perf_counter() - t0) * 1000
        if draw and before is not None:
            self.frame_ms.append(ms)
            n = getattr(before, "_qa_draws", 0)     # the first draws of a scene build its caches
            before._qa_draws = n + 1
            if ms > SPIKE_MS and mgr.top is before and n >= 2:
                self.spikes.append((ms, f"{self.ctx} top={type(mgr.top).__name__}"))

    def run(self, seconds, events=()):
        events = list(events)
        for i in range(max(1, int(round(seconds / DT)))):
            self.frame(events if i == 0 else [])

    def key(self, k, mod=0, wait=0.05):
        self.frame([kev(pg.KEYDOWN, k, mod)])
        self.run(wait, [kev(pg.KEYUP, k, mod)])

    def settle(self, s=0.4):
        self.run(s)

    @property
    def top(self):
        return self.app.scenes.top

    def top_name(self):
        return type(self.top).__name__

    @property
    def game(self):
        from jebik.scenes.game_scene import GameScene
        return next((s for s in reversed(self.app.scenes.stack) if isinstance(s, GameScene)), None)

    def to_menu(self):
        from jebik.scenes.main_menu import MainMenuScene
        if self.app.save.profile is None:
            self.app.save.create_profile("QA")
        self.app.scenes.reset(MainMenuScene(self.app), fade=False)
        self.settle(0.1)
        while self.app.scenes.transitioning:        # keys are ignored during a cross-fade
            self.frame([])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tobi-runs", type=int, default=1)
    ap.add_argument("--fuzz-seeds", type=int, default=48)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip-flows", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.runs, args.tobi_runs, args.fuzz_seeds = 2, 1, 6
    import qa_flows
    import qa_run
    t_start = time.perf_counter()
    h = Harness(splash=True)
    stats: dict = defaultdict(Counter)
    from jebik.worlds import catalog
    levels = args.only or catalog.playable_levels()

    def phase(name, fn, *a):
        h.ctx = name
        t0 = time.perf_counter()
        print(f"== {name}", end=" ", flush=True)
        try:
            fn(h, *a)
            print(f"({time.perf_counter() - t0:.0f} s)", flush=True)
        except Exception:                             # noqa: BLE001
            h.issue("exception", f"{name}: {traceback.format_exc().splitlines()[-1]}",
                    traceback.format_exc())
            try:
                h.app.scenes.stack.clear()
                h.to_menu()
            except Exception:                         # noqa: BLE001
                h.new_app()

    if not args.skip_flows:
        phase("splash+profile", qa_flows.splash_and_profile)
        phase("settings", qa_flows.settings_flow)
        phase("window/touch", qa_flows.window_and_touch)
        phase("campaign EZZZ 1-1..3-4", qa_flows.campaign, stats)
        phase("locale overflow", qa_flows.locale_scan)
    import qa_fuzz
    phase("logic fuzz (no drawing)", qa_fuzz.logic_fuzz, levels, args.fuzz_seeds, stats)
    tracemalloc.start()
    phase("soak EZZZ", qa_run.soak_levels, levels, args.runs, stats, EZZZ)
    snap1 = tracemalloc.take_snapshot()
    phase("soak TOBI", qa_flows.tobi_flow, levels, args.tobi_runs, stats)
    phase("memory: 1-1 x25", qa_run.memory_loop, stats)
    snap2 = tracemalloc.take_snapshot()
    growth = sum(s.size_diff for s in snap2.compare_to(snap1, "filename"))
    top = snap2.compare_to(snap1, "lineno")[:5]
    tracemalloc.stop()
    if not args.skip_flows:
        phase("records/profiles/saves", qa_flows.records_profiles_saves)
    for (lid, diff), c in h.causes.items():
        if "boss_hit" in c and c["boss_hit"] == 0 and diff == EZZZ:
            h.issue("boss_never_hit", f"{lid}: the bot never hit the boss in any run")
    report(h, stats, growth, top, time.perf_counter() - t_start)
    shutil.rmtree(SAVE_DIR, ignore_errors=True)
    return 1 if h.issues else 0


def report(h, stats, growth, top, wall):
    print("\n==================== QA SOAK REPORT ====================")
    runs = sum(v for k, c in stats.items() if k != "_wall" for kk, v in c.items()
               if kk not in ("t_sum", "restarts"))
    print(f"wall {wall:.0f} s, frames {h.frames}, level runs {runs}")
    for k in sorted(k for k in stats if k != "_wall"):
        c = dict(stats[k])
        print(f"  {k}: {c}")
    ms = sorted(h.frame_ms)
    if ms:
        print(f"frame ms (drawn frames): p50 {ms[len(ms) // 2]:.1f}  p99 {ms[int(len(ms) * .99)]:.1f}  "
              f"max {ms[-1]:.1f}")
    for sp in sorted(h.spikes, reverse=True)[:8]:
        print(f"  spike {sp[0]:.0f} ms  {sp[1]}")
    print("damage / boss hits per level:")
    for k in sorted(h.causes):
        print(f"  {k}: {dict(h.causes[k].most_common())}")
    print(f"tracemalloc growth soak->end: {growth / 1024:.0f} KiB")
    for s in top:
        print(f"  {s}")
    print(f"\nISSUES: {len(h.issues)}")
    for (kind, detail), rec in sorted(h.issues.items()):
        print(f"- [{kind}] x{rec['n']} ({rec['ctx']}): {detail}")
        if rec["tb"]:
            print("    " + "\n    ".join(rec["tb"].strip().splitlines()[-8:]))


if __name__ == "__main__":
    sys.exit(main())

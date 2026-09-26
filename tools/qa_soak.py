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
import random
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

import pygame as pg  # noqa: E402

from jebik import config  # noqa: E402
from jebik.game import frog as fs  # noqa: E402
from jebik.game.rules import EZZZ, PLAYING, TOBI  # noqa: E402
from qa_bot import Bot, Checker, safe_neighbor_to  # noqa: E402

DT = 1 / 60
ARROWS = {0: pg.K_UP, 1: pg.K_RIGHT, 2: pg.K_DOWN, 3: pg.K_LEFT}
SPIKE_MS = 120.0
LANG = "ru"                  # the QA language (level play is not repeated per language)


def kev(t, k, mod=0, uni=""):
    return pg.event.Event(t, key=k, mod=mod, unicode=uni, scancode=0)


class Harness:
    def __init__(self, splash: bool = False):
        self.issues: dict[tuple, dict] = {}
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
        if self.app is not None:
            pg.quit()
        self.app = App(splash=splash)
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
        if draw:
            self.frame_ms.append(ms)
            if ms > SPIKE_MS and mgr.top is before and self.frames > 3:
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


# ---------------------------------------------------------------- level runs
class LevelRun:
    """Plays one level through the GameScene with the bot / random input."""

    def __init__(self, h: Harness, lid: str, seed: int, mode: str, budget: float):
        self.h, self.lid, self.seed, self.mode, self.budget = h, lid, seed, mode, budget
        self.rng = random.Random(f"{lid}/{seed}/{mode}")
        self.bot = Bot(seed, noise=0.03 if mode == "bot" else 0.0)
        self.game = None
        self.checker = None
        self.restarts = 0
        self.pauses = 0
        self.t = 0.0

    def _hook(self, g):
        self.game = g
        self.checker = Checker(lambda k, d: self.h.issue(k, f"{self.lid}: {d}"), g.world)
        orig = g._handle_events
        chk = self.checker

        def handle(events, _orig=orig, _g=g):
            chk.events(_g.world, events)
            _orig(events)
        g._handle_events = handle

    def start(self, push=True):
        from jebik.scenes.game_scene import GameScene
        h = self.h
        h.to_menu()
        if push:
            h.app.scenes.push(GameScene(h.app, self.lid, seed=self.seed), fade=False)
        self._hook(h.game)

    def _actions_to_events(self, act):
        if act is None:
            return []
        if act[0] == "move":
            k = ARROWS[act[1]]
            mod = pg.KMOD_SHIFT if act[2] else 0
            return [kev(pg.KEYDOWN, k, mod), kev(pg.KEYUP, k, mod)]
        if act[0] == "tongue":
            f = self.game.world.frog
            evs = [kev(pg.KEYDOWN, pg.K_SPACE)]
            if act[1] is not None and act[1] != f.facing:
                evs += [kev(pg.KEYDOWN, ARROWS[act[1]]), kev(pg.KEYUP, ARROWS[act[1]])]
            return evs + [kev(pg.KEYUP, pg.K_SPACE)]
        return []

    def _random_events(self):
        r = self.rng.random()
        if r > 0.12:
            return []
        choice = self.rng.randrange(14)
        k = self.rng.choice(list(ARROWS.values()) + [pg.K_w, pg.K_a, pg.K_s, pg.K_d])
        if choice < 6:
            return [kev(pg.KEYDOWN, k)] + ([kev(pg.KEYUP, k)] if self.rng.random() < 0.7 else [])
        if choice < 8:
            return [kev(pg.KEYDOWN, k, pg.KMOD_SHIFT), kev(pg.KEYUP, k, pg.KMOD_SHIFT)]
        if choice < 10:
            return [kev(pg.KEYDOWN, pg.K_SPACE), kev(pg.KEYUP, pg.K_SPACE)]
        if choice == 10:
            return [kev(pg.KEYUP, k)]
        if choice == 11:
            p = (self.rng.randrange(1920), self.rng.randrange(1080))
            return [pg.event.Event(pg.MOUSEBUTTONDOWN, pos=p, button=1),
                    pg.event.Event(pg.MOUSEBUTTONUP, pos=p, button=1)]
        if choice == 12:
            x, y = self.rng.random(), self.rng.random()
            fid = self.rng.randrange(3)
            evs = [pg.event.Event(pg.FINGERDOWN, finger_id=fid, x=x, y=y, dx=0, dy=0, touch_id=1)]
            x2 = min(1, max(0, x + self.rng.uniform(-.15, .15)))
            evs.append(pg.event.Event(pg.FINGERMOTION, finger_id=fid, x=x2, y=y, dx=0, dy=0, touch_id=1))
            evs.append(pg.event.Event(pg.FINGERUP, finger_id=fid, x=x2, y=y, dx=0, dy=0, touch_id=1))
            return evs
        return [kev(pg.KEYDOWN, pg.K_ESCAPE), kev(pg.KEYUP, pg.K_ESCAPE)]

    def _overlay_step(self):
        """Something is over the game (pause / settings / win / lose)."""
        h = self.h
        name = h.top_name()
        if name == "PauseScene":
            r = self.rng.random()
            if r < 0.7:
                h.key(pg.K_ESCAPE)
            elif r < 0.85:
                self.restarts += 1
                h.top.restart()
                h.settle(0.35)
            else:
                h.top.settings()
                h.settle(0.3)
            return
        if name == "SettingsScene":
            h.key(pg.K_ESCAPE)
            h.settle(0.2)
            return
        h.frame([])

    def play(self, start: bool = True) -> str:
        h = self.h
        if start:
            self.start()
        stuck_result = 0.0
        pause_at = self.rng.uniform(3, 30) if self.rng.random() < 0.35 else None
        while True:
            g = h.game
            name = h.top_name()
            if name == "WinScene":
                return "win"
            if name == "LoseScene":
                return "lose"
            if g is None:
                return "left"
            if g is not self.game:
                self.restarts += 1
                self._hook(g)
            if h.top is not g:
                self._overlay_step()
                continue
            w = g.world
            if self.t > self.budget:
                return self.force_win()
            evs = []
            if self.mode == "bot":
                evs = self._actions_to_events(self.bot.decide(w, DT))
            else:
                evs = self._random_events()
            if pause_at is not None and self.t > pause_at and w.state == PLAYING:
                pause_at = None
                self.pauses += 1
                evs = [pg.event.Event(pg.WINDOWFOCUSLOST)] if self.rng.random() < 0.5 else \
                    [kev(pg.KEYDOWN, pg.K_p), kev(pg.KEYUP, pg.K_p)]
            h.frame(evs)
            self.t += DT
            if h.game is g:
                self.checker.frame(g.world, DT)
                if g.world.state != PLAYING and h.top is g and g.restart_timer is None:
                    stuck_result += DT
                    if stuck_result > g.world.end_timer + 3 and stuck_result > 4:
                        h.issue("result_softlock", f"{self.lid}: {g.world.state} but no panel")
                        return "softlock"
                else:
                    stuck_result = 0.0

    def force_win(self) -> str:
        """Drive the world to completion (boss hits, exact N, hop on the exit)."""
        h = self.h
        g = h.game
        w = g.world
        boss = w.boss
        guard = 0
        while boss is not None and not boss.defeated and guard < 10:
            boss.open_window(1.0)
            boss.take_hit(w)
            guard += 1
        if not w.full:
            w.eaten = w.needed
            w._become_full()
        w._maybe_open_exit()
        for _ in range(900):
            if h.top_name() == "WinScene":
                return "forced"
            if h.game is not g or w.state != PLAYING:
                break
            f = w.frog
            ex = w.exit_cell
            if ex is not None and f.can_act and w.tiles.standable(ex):
                nd = safe_neighbor_to(w, ex)
                if nd:
                    f.cell = f.hop_from = f.hop_to = f.last_safe = nd[0]
                    f.invuln = 5.0
                    h.frame([kev(pg.KEYDOWN, ARROWS[nd[1]]), kev(pg.KEYUP, ARROWS[nd[1]])])
                    continue
            f.invuln = max(f.invuln, 1.0)
            h.frame([])
        h.run(2.0)
        if h.top_name() == "WinScene":
            return "forced"
        h.issue("force_win_failed", f"{self.lid}: top={h.top_name()} state={w.state} exit={w.exit_cell} "
                f"frog={w.frog.state}@{w.frog.cell}")
        return "force_failed"


def soak_levels(h: Harness, levels, runs: int, stats, difficulty=EZZZ, budget=150.0):
    h.app.difficulty = difficulty
    h.draw_every = 12
    for lid in levels:
        for i in range(runs):
            mode = "bot" if i % 3 != 2 else "random"
            seed = 1000 + i
            h.ctx = f"{difficulty} {lid} seed={seed} {mode}"
            t0 = time.perf_counter()
            try:
                run = LevelRun(h, lid, seed, mode, budget if mode == "bot" else 45.0)
                out = run.play()
            except Exception:                         # noqa: BLE001
                out = "exception"
                h.issue("exception", f"{h.ctx}: {traceback.format_exc().splitlines()[-1]}",
                        traceback.format_exc())
                h.app.scenes.stack.clear()
                h.to_menu()
                run = None
            stats[(difficulty, lid, mode)][out] += 1
            if run is not None:
                stats[(difficulty, lid, mode)]["t_sum"] += int(run.t)
                stats[(difficulty, lid, mode)]["restarts"] += run.restarts
            stats["_wall"][lid] += time.perf_counter() - t0
    h.draw_every = 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--tobi-runs", type=int, default=6)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip-flows", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.runs, args.tobi_runs = 6, 2
    import qa_flows
    t_start = time.perf_counter()
    h = Harness(splash=True)
    stats: dict = defaultdict(Counter)
    from jebik.worlds import catalog
    levels = args.only or catalog.playable_levels()

    def phase(name, fn, *a):
        h.ctx = name
        print(f"== {name}", flush=True)
        try:
            fn(h, *a)
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
    tracemalloc.start()
    phase("soak EZZZ", soak_levels, levels, args.runs, stats, EZZZ)
    snap1 = tracemalloc.take_snapshot()
    phase("soak TOBI", qa_flows.tobi_flow, levels, args.tobi_runs, stats)
    phase("memory: 1-1 x25", qa_flows.memory_loop, stats)
    snap2 = tracemalloc.take_snapshot()
    growth = sum(s.size_diff for s in snap2.compare_to(snap1, "filename"))
    top = snap2.compare_to(snap1, "lineno")[:5]
    tracemalloc.stop()
    if not args.skip_flows:
        phase("records/profiles/saves", qa_flows.records_profiles_saves)
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

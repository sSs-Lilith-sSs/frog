"""Level runs for ``tools/qa_soak.py``: one level played through the real
GameScene by the bot (``qa_bot``) or by random input, with the per-frame
invariants of ``qa_checks``; plus the forced win used when the bot runs out of time."""
from __future__ import annotations

import random
import time
import traceback

import pygame as pg

from jebik.game import events as ev
from jebik.game.rules import EZZZ, PLAYING
from qa_bot import Bot
from qa_checks import Checker, safe_neighbor_to
from qa_soak import ARROWS, DT, Harness, kev


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
        self.forcing = False                          # force_win: its boss hits are not counted
        self.t = 0.0

    def _hook(self, g):
        self.game = g
        self.checker = Checker(lambda k, d: self.h.issue(k, f"{self.lid}: {d}"), g.world)
        orig = g._handle_events
        chk = self.checker

        causes = self.h.causes
        if g.world.boss is not None:
            causes[(self.lid, g.world.rules.difficulty)]["boss_hit"] += 0

        def handle(events, _orig=orig, _g=g):
            chk.events(_g.world, events)
            for e in [] if self.forcing else events:
                if e.kind in (ev.HIT, ev.SPLASH, ev.OVEREAT, ev.BOSS_HIT, ev.LOSE):
                    causes[(self.lid, _g.world.rules.difficulty)][f"{e.kind}:{e.value}"
                                                                  if e.kind in (ev.HIT, ev.LOSE) else e.kind] += 1
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
            if self.t > self.budget and w.state == PLAYING:
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
        self.forcing = True
        w.flies.auto_spawn = False                   # no fly left to overeat on the way
        w.flies.flies = [fl for fl in w.flies.flies if not fl.counted]
        w.hearts = w.rules.max_hearts
        if w.time_left is not None:
            w.time_left = max(w.time_left, 60.0)
        for e in w.enemies:                          # freeze attacks (TOBI: any fall restarts)
            e.update = lambda dt, world: None
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


def soak_levels(h: Harness, levels, runs: int, stats, difficulty=EZZZ, budget=100.0):
    h.app.difficulty = difficulty
    h.draw_every = 12
    for lid in levels:
        for i in range(runs):
            mode = "bot" if i % 3 != 2 else "random"
            seed = 1000 + i
            h.ctx = f"{difficulty} {lid} seed={seed} {mode}"
            t0 = time.perf_counter()
            try:
                run = LevelRun(h, lid, seed, mode, budget if mode == "bot" else 30.0)
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


def memory_loop(h, stats):
    h.app.difficulty = EZZZ
    h.draw_every = 4
    for i in range(25):
        run = LevelRun(h, "1-1", 50 + i, "random", 8.0)
        run.start()
        for _ in range(int(8 / DT)):
            h.frame(run._random_events())
            if h.game is None:
                break
        if h.game is not None and h.top is h.game:
            h.key(pg.K_ESCAPE)
            h.settle(0.2)
            if h.top_name() == "PauseScene":
                h.top.restart()
                h.settle(0.4)
    h.draw_every = 1

"""Logic-only fuzz for ``tools/qa_soak.py``: many seeds of every level played
straight on :class:`~jebik.game.world.World` (no drawing, ~50x faster than the
scene soak) by the bot with heavy random noise, with the same invariants as the
scene runs. Finds rare crashes and impossible situations the slow runs miss."""
from __future__ import annotations

import random
import traceback

from jebik.game.rules import EZZZ, PLAYING, TOBI, rules_for
from jebik.game.world import World
from jebik.worlds import catalog
from qa_bot import Bot
from qa_checks import Checker

DT = 1 / 60


def fuzz_level(h, lid: str, seed: int, difficulty: str, seconds: float, noise: float, stats) -> str:
    level = catalog.load_level(lid)
    w = World(level, rules_for(difficulty, level), seed=seed)
    chk = Checker(lambda k, d: h.issue(k, f"{lid} fuzz {difficulty} seed={seed}: {d}"), w)
    bot = Bot(seed, noise=noise)
    rng = random.Random(seed)
    for _ in range(int(seconds / DT)):
        act = bot.decide(w, DT)
        if act is None and rng.random() < 0.02:          # extra mashing while busy
            act = ("move", rng.randrange(4), rng.random() < 0.3)
        if act is not None:
            if act[0] == "move":
                w.request_move(act[1], act[2])
            elif act[0] == "tongue":
                w.request_tongue(act[1])
        w.update(DT)
        chk.events(w, w.drain_events())
        chk.frame(w, DT)
        if w.state != PLAYING:
            break
    stats[("fuzz", difficulty, lid)][w.state if w.state != PLAYING else "timeout"] += 1
    for kind in ("boss_hit",):
        boss = w.boss
        if boss is not None:
            stats[("fuzz", difficulty, lid)][kind] += boss.max_hp - boss.hp if boss.hp <= boss.max_hp else 0
    return w.state


def logic_fuzz(h, levels, seeds: int, stats) -> None:
    for lid in levels:
        for i in range(seeds):
            difficulty = TOBI if i % 4 == 3 else EZZZ
            noise = (0.02, 0.2, 0.6)[i % 3]
            h.ctx = f"fuzz {lid} seed={i} {difficulty} noise={noise}"
            try:
                fuzz_level(h, lid, 5000 + i, difficulty, 90.0, noise, stats)
            except Exception:                              # noqa: BLE001
                h.issue("exception", f"{h.ctx}: {traceback.format_exc().splitlines()[-1]}",
                        traceback.format_exc())

"""Records tables across all local profiles (pure).

* Per level: every profile keeps its best runs (``LevelRecord.runs``); the
  table merges them — top 10 by score, then faster time, then earlier date.
* Total: one row per profile — sum of its best scores over all levels,
  ordered by score, then by total best time, then name.
Both are separate per difficulty.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    from .save import SaveData


@dataclass(frozen=True)
class RecordRow:
    name: str
    score: int
    time: float
    stars: int
    date: float = 0.0
    levels: int = 1          # total table: completed levels


def level_top(data: "SaveData", difficulty: str, level_id: str,
              n: int = config.RECORDS_KEEP) -> list[RecordRow]:
    rows = []
    for p in data.profiles:
        rec = p.diff(difficulty).levels.get(level_id)
        if rec is None:
            continue
        runs = rec.runs
        if not runs and rec.completed:          # results saved before runs existed
            rows.append(RecordRow(p.name, rec.best_score, rec.best_time or 0.0, rec.stars))
        rows.extend(RecordRow(p.name, r.score, r.time, r.stars, r.date) for r in runs)
    rows.sort(key=lambda r: (-r.score, r.time, r.date, r.name.casefold()))
    return rows[:n]


def total_top(data: "SaveData", difficulty: str, n: int = config.RECORDS_KEEP) -> list[RecordRow]:
    rows = []
    for p in data.profiles:
        done = [r for r in p.diff(difficulty).levels.values() if r.completed]
        if not done:
            continue
        rows.append(RecordRow(p.name, sum(r.best_score for r in done),
                              sum(r.best_time or 0.0 for r in done),
                              sum(r.stars for r in done), levels=len(done)))
    rows.sort(key=lambda r: (-r.score, r.time, r.name.casefold()))
    return rows[:n]

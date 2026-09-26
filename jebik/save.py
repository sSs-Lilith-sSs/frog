"""Persistent save data: profiles, progress and settings (JSON).

Stored at ``~/.jebik/save.json`` (or ``$JEBIK_SAVE_DIR/save.json``). Loading
never raises: a missing file gives defaults, a corrupt one is moved aside to
``save.json.corrupt`` and defaults are used.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

SAVE_VERSION = 2
MAX_NAME_LEN = 16


def save_dir() -> Path:
    env = os.environ.get("JEBIK_SAVE_DIR")
    return Path(env).expanduser() if env else Path.home() / ".jebik"


def save_path() -> Path:
    return save_dir() / "save.json"


@dataclass
class Run:
    """One won run (kept for the records table)."""
    score: int
    time: float
    stars: int
    date: float = 0.0

    @classmethod
    def from_json(cls, d: Any) -> "Run | None":
        if not isinstance(d, dict) or not isinstance(d.get("time"), (int, float)):
            return None
        date = d.get("date")
        return cls(score=_int(d.get("score"), 0, 0, 10**9), time=max(0.0, float(d["time"])),
                   stars=_int(d.get("stars"), 1, 0, 3),
                   date=float(date) if isinstance(date, (int, float)) else 0.0)


def run_order(r: Run) -> tuple[float, float, float]:
    """Records order: higher score, then faster, then earlier."""
    return (-r.score, r.time, r.date)


@dataclass
class LevelRecord:
    stars: int = 0
    best_score: int = 0
    best_time: float | None = None
    completed: bool = False
    runs: list[Run] = field(default_factory=list)      # best first, <= RECORDS_KEEP

    @classmethod
    def from_json(cls, d: Any) -> "LevelRecord":
        if not isinstance(d, dict):
            return cls()
        bt = d.get("best_time")
        runs_raw = d.get("runs", [])
        runs = [r for r in (Run.from_json(x) for x in runs_raw) if r] \
            if isinstance(runs_raw, list) else []
        return cls(stars=_int(d.get("stars"), 0, 0, 3),
                   best_score=_int(d.get("best_score"), 0, 0, 10**9),
                   best_time=float(bt) if isinstance(bt, (int, float)) else None,
                   completed=bool(d.get("completed", False)),
                   runs=sorted(runs, key=run_order)[:config.RECORDS_KEEP])

    def to_json(self) -> dict[str, Any]:
        return {"stars": self.stars, "best_score": self.best_score, "best_time": self.best_time,
                "completed": self.completed, "runs": [vars(r) for r in self.runs]}


@dataclass
class DifficultyProgress:
    """Per-difficulty results. Which levels are open is computed from the
    completed ones (see :mod:`jebik.progression`), never stored."""
    levels: dict[str, LevelRecord] = field(default_factory=dict)

    @classmethod
    def from_json(cls, d: Any) -> "DifficultyProgress":
        if not isinstance(d, dict):
            return cls()
        levels_raw = d.get("levels", {})
        levels = {str(k): LevelRecord.from_json(v) for k, v in levels_raw.items()} \
            if isinstance(levels_raw, dict) else {}
        return cls(levels=levels)

    def completed(self, level_id: str) -> bool:
        return self.record(level_id).completed

    def record(self, level_id: str) -> LevelRecord:
        return self.levels.get(level_id, LevelRecord())

    def total_stars(self) -> int:
        return sum(r.stars for r in self.levels.values())


@dataclass
class Profile:
    name: str
    created: float = field(default_factory=time.time)
    progress: dict[str, DifficultyProgress] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)   # seen cutscenes, unlocks...

    def has(self, flag: str) -> bool:
        return flag in self.flags

    def mark(self, flag: str) -> None:
        if flag not in self.flags:
            self.flags.append(flag)

    def diff(self, difficulty: str) -> DifficultyProgress:
        if difficulty not in self.progress:
            self.progress[difficulty] = DifficultyProgress()
        return self.progress[difficulty]

    def record_result(self, difficulty: str, level_id: str, score: int,
                      stars: int, time_s: float, date: float | None = None) -> bool:
        """Store a win; returns True if it is a new best score."""
        prog = self.diff(difficulty)
        rec = prog.levels.setdefault(level_id, LevelRecord())
        new_best = score > rec.best_score
        rec.completed = True
        rec.stars = max(rec.stars, stars)
        rec.best_score = max(rec.best_score, score)
        rec.best_time = time_s if rec.best_time is None else min(rec.best_time, time_s)
        rec.runs.append(Run(score, time_s, stars, time.time() if date is None else date))
        rec.runs = sorted(rec.runs, key=run_order)[:config.RECORDS_KEEP]
        return new_best

    @classmethod
    def from_json(cls, d: Any) -> "Profile | None":
        if not isinstance(d, dict) or not isinstance(d.get("name"), str):
            return None
        name = d["name"].strip()[:MAX_NAME_LEN]
        if not name:
            return None
        prog_raw = d.get("progress", {})
        progress = {str(k): DifficultyProgress.from_json(v) for k, v in prog_raw.items()} \
            if isinstance(prog_raw, dict) else {}
        created = d.get("created")
        flags_raw = d.get("flags", [])
        flags = [str(f) for f in flags_raw if isinstance(f, str)] if isinstance(flags_raw, list) else []
        return cls(name=name, created=float(created) if isinstance(created, (int, float))
                   else time.time(), progress=progress, flags=flags)


@dataclass
class SaveData:
    settings: dict[str, Any] = field(default_factory=lambda: dict(config.DEFAULT_SETTINGS))
    profiles: list[Profile] = field(default_factory=list)
    current: str | None = None
    path: Path | None = None

    # ------------------------------------------------------------ profiles
    def find(self, name: str) -> Profile | None:
        key = name.strip().casefold()
        return next((p for p in self.profiles if p.name.casefold() == key), None)

    @property
    def profile(self) -> Profile | None:
        return self.find(self.current) if self.current else None

    def create_profile(self, name: str) -> Profile:
        name = name.strip()[:MAX_NAME_LEN]
        if not name:
            raise ValueError("empty name")
        if self.find(name):
            raise ValueError("exists")
        p = Profile(name=name)
        self.profiles.append(p)
        self.current = p.name
        return p

    def delete_profile(self, name: str) -> None:
        p = self.find(name)
        if p:
            self.profiles.remove(p)
        if self.current and self.find(self.current) is None:
            self.current = None

    # ------------------------------------------------------------ io
    def to_json(self) -> dict[str, Any]:
        def prog(dp: DifficultyProgress) -> dict[str, Any]:
            return {"levels": {k: v.to_json() for k, v in dp.levels.items()}}
        return {
            "version": SAVE_VERSION,
            "settings": self.settings,
            "current_profile": self.current,
            "profiles": [{"name": p.name, "created": p.created, "flags": p.flags,
                          "progress": {k: prog(v) for k, v in p.progress.items()}}
                         for p in self.profiles],
        }

    def save(self) -> bool:
        path = self.path or save_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2),
                           encoding="utf-8")
            os.replace(tmp, path)
            return True
        except OSError:
            return False


def _int(v: Any, default: int, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return default
    return max(lo, min(hi, int(v)))


def _clean_settings(raw: Any) -> dict[str, Any]:
    s = dict(config.DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return s
    if raw.get("lang") in ("ua", "en", "ru"):
        s["lang"] = raw["lang"]
    for key in ("music_volume", "sfx_volume"):
        v = raw.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            s[key] = max(0.0, min(1.0, float(v)))
    if raw.get("music_track") in config.MUSIC_TRACKS:
        s["music_track"] = raw["music_track"]
    if raw.get("touch") in config.TOUCH_MODES:
        s["touch"] = raw["touch"]
    for key in ("fullscreen", "show_grid"):
        if isinstance(raw.get(key), bool):
            s[key] = raw[key]
    return s


def load(path: Path | None = None) -> SaveData:
    path = path or save_path()
    data = SaveData(path=path)
    if not path.exists():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("save root is not an object")
    except (OSError, ValueError, UnicodeDecodeError):
        try:
            os.replace(path, path.with_suffix(".json.corrupt"))
        except OSError:
            pass
        return data
    data.settings = _clean_settings(raw.get("settings"))
    profiles_raw = raw.get("profiles", [])
    if isinstance(profiles_raw, list):
        for pr in profiles_raw:
            p = Profile.from_json(pr)
            if p and not data.find(p.name):
                data.profiles.append(p)
    cur = raw.get("current_profile")
    data.current = cur if isinstance(cur, str) and data.find(cur) else None
    return data

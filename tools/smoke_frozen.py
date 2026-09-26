#!/usr/bin/env python3
"""Smoke-test the PyInstaller build headless (used by CI, works on Windows and Linux).

    python3 tools/smoke_frozen.py dist/jebik

1. start the game with ``JEBIK_AUTOQUIT=3 JEBIK_NO_SPLASH=1`` -> must exit 0
   and write ``save.json`` (no ``crash.log``);
2. the same with the studio splash (intro audio, splash art);
3. ``JEBIK_SELFTEST=1``: bundled fonts/audio, all worlds, every playable level
   loaded and played for a moment -> must exit 0 and report ``frozen=True``.

SDL runs on the dummy video/audio drivers; saves go to a temp folder.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 240


def find_exe(target: Path) -> Path:
    if target.is_file():
        return target
    for name in ("jebik.exe", "jebik"):
        if (target / name).is_file():
            return target / name
    sys.exit(f"no jebik executable in {target}")


def run(exe: Path, title: str, extra: dict[str, str]) -> tuple[Path, str]:
    save_dir = Path(tempfile.mkdtemp(prefix="jebik_smoke_"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("JEBIK_")}
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               JEBIK_SAVE_DIR=str(save_dir), **extra)
    print(f"--- {title}: {' '.join(f'{k}={v}' for k, v in extra.items())}", flush=True)
    try:
        proc = subprocess.run([str(exe)], env=env, timeout=TIMEOUT, cwd=exe.parent,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.TimeoutExpired:
        sys.exit(f"FAIL {title}: still running after {TIMEOUT} s")
    out = proc.stdout.decode("utf-8", "replace").strip()
    if out:
        print(out)
    crash = save_dir / "crash.log"
    if crash.exists():
        print(crash.read_text("utf-8", "replace"))
    if proc.returncode != 0:
        sys.exit(f"FAIL {title}: exit code {proc.returncode}")
    print(f"ok   {title}: exit 0", flush=True)
    return save_dir, out


def main() -> None:
    exe = find_exe(Path(sys.argv[1] if len(sys.argv) > 1 else "dist/jebik").resolve())
    print(f"executable: {exe}")
    d, _ = run(exe, "autoquit", {"JEBIK_AUTOQUIT": "3", "JEBIK_NO_SPLASH": "1"})
    if not (d / "save.json").is_file():
        sys.exit("FAIL autoquit: save.json was not written")
    run(exe, "autoquit with splash", {"JEBIK_AUTOQUIT": "3"})
    d, out = run(exe, "selftest", {"JEBIK_SELFTEST": "1"})
    log = d / "selftest.log"
    text = log.read_text("utf-8", "replace") if log.is_file() else ""
    if "SELFTEST" not in out:
        print(text)                    # a windowed .exe has no stdout: show the log
    if "SELFTEST PASSED" not in text or "frozen=True" not in text:
        sys.exit("FAIL selftest: log missing, not frozen, or not passed")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()

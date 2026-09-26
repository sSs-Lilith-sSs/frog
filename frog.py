#!/usr/bin/env python3
"""«жэбик» — запуск гри: python3 frog.py   (перевірка збірки: python3 frog.py --selftest)"""
import sys

if sys.version_info < (3, 10):
    sys.exit("жэбик потребує Python 3.10+ (рекомендовано 3.11)")

try:
    import numpy  # noqa: F401
    import pygame  # noqa: F401
except ImportError as exc:  # pragma: no cover - friendly message only
    sys.exit(f"Не вистачає бібліотеки: {exc.name}. Встанови: pip install -r requirements.txt")

import asyncio

from jebik import paths, selftest
from jebik.app import main


def _write_crash_log() -> None:
    """A windowed .exe has no console: leave the traceback in the save folder."""
    import traceback
    try:
        out = paths.save_dir()
        out.mkdir(parents=True, exist_ok=True)
        (out / "crash.log").write_text(traceback.format_exc(), encoding="utf-8")
    except OSError:
        pass


if __name__ == "__main__":
    if selftest.requested():
        sys.exit(selftest.main())
    try:
        asyncio.run(main())
    except Exception:
        if not paths.is_frozen():
            raise
        _write_crash_log()
        sys.exit(1)

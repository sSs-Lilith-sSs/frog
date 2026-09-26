#!/usr/bin/env python3
"""«жэбик» — запуск гри: python3 frog.py"""
import sys

if sys.version_info < (3, 10):
    sys.exit("жэбик потребує Python 3.10+ (рекомендовано 3.11)")

try:
    import numpy  # noqa: F401
    import pygame  # noqa: F401
except ImportError as exc:  # pragma: no cover - friendly message only
    sys.exit(f"Не вистачає бібліотеки: {exc.name}. Встанови: pip install -r requirements.txt")

from jebik.app import main

if __name__ == "__main__":
    main()

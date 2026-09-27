# /// script
# dependencies = [
#     "pygame-ce",
#     "numpy",
# ]
# ///
"""«жэбик» — browser entry point (pygbag). ``tools/build_web.py`` copies this file
next to the ``jebik`` package and packs both; the desktop entry is ``frog.py``.

pygbag runs the game on CPython compiled to WebAssembly: ``App.run`` awaits
``asyncio.sleep(0)`` every frame, saves go to ``localStorage`` and audio uses the
``.ogg`` copies the build script makes.
"""
import asyncio

import numpy  # noqa: F401  (pygbag installs the imports it sees in main.py)
import pygame  # noqa: F401

from jebik.app import main

asyncio.run(main())

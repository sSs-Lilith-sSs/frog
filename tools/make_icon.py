#!/usr/bin/env python3
"""Draw the program icon (the frog on a lily pad) into packaging/icon.ico.

Uses the game's own procedural art (``draw_frog_front`` + the water world's
``draw_pad``), rendered separately for every icon size so small sizes stay
crisp. The .ico holds PNG-compressed images (Windows Vista+), written by hand —
no Pillow needed.

    python3 tools/make_icon.py              # -> packaging/icon.ico (+ --png preview.png)
"""
from __future__ import annotations

import argparse
import io
import math
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame as pg  # noqa: E402

from jebik.art.chars import draw_frog_front  # noqa: E402
from jebik.art.common import render_ss  # noqa: E402
from jebik.worlds.water.art.pads import draw_pad  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)
OUT = ROOT / "packaging" / "icon.ico"


def icon_surface(size: int) -> pg.Surface:
    def draw(s: pg.Surface, ss: float) -> None:
        S = size * ss
        draw_pad(s, S * .5, S * .57, S * .39, math.radians(60), False, S / 128)
        k = S * .62 / 62                       # the frog is 62k x 50k
        draw_frog_front(s, (S * .5, S * .45), k)
    return render_ss((size, size), draw, ss=4 if size >= 64 else 8)


def png_bytes(surf: pg.Surface) -> bytes:
    buf = io.BytesIO()
    pg.image.save(surf, buf, "icon.png")
    return buf.getvalue()


def write_ico(images: list[tuple[int, bytes]], path: Path) -> None:
    """ICONDIR + ICONDIRENTRY[] + PNG blobs."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, blobs = b"", b""
    for size, data in images:
        dim = 0 if size >= 256 else size          # 0 means 256
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + entries + blobs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", nargs="?", default=str(OUT))
    ap.add_argument("--png", help="also save the 256 px image here (preview)")
    args = ap.parse_args()
    pg.init()
    pg.display.set_mode((1, 1))
    surfs = {s: icon_surface(s) for s in SIZES}
    write_ico([(s, png_bytes(surf)) for s, surf in surfs.items()], Path(args.out))
    if args.png:
        pg.image.save(surfs[256], args.png)
    print(f"wrote {args.out} ({', '.join(map(str, SIZES))} px)")


if __name__ == "__main__":
    main()

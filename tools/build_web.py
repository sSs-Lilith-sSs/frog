#!/usr/bin/env python3
"""Build the browser version of «жэбик» with pygbag -> ``build/web/``.

    pip install "pygbag==0.9.3" soundfile
    python3 tools/build_web.py            # build/web/index.html + jebik.apk ...
    python3 -m http.server -d build/web   # then open http://localhost:8000/

Steps: stage ``web/main.py`` + the ``jebik`` package in ``build/web-src/jebik/``
(every ``.wav`` becomes an ``.ogg`` — browsers decode OGG best and it is ~10x
smaller; the game picks ``.ogg`` on the web, see ``jebik.paths.audio_file``;
the studio splash layers are pre-rendered, see ``jebik.art.splash_layers``),
run ``pygbag --build`` with our page template (``web/jebik.tmpl``: title,
iPhone home-screen metas, rotate hint) and add the icons + web manifest.
The WebAssembly runtime itself (CPython, pygame-ce, numpy) is loaded by the
page from pygbag's CDN (pygame-web.github.io), matching the pinned version.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
PYGBAG_VERSION = "0.9.3"
APP_NAME = "jebik"
TITLE = "жэбик"
BG = "#0d2a1f"


def stage(src: Path, entry: Path) -> int:
    """Copy the game into ``src`` (the folder pygbag packs); returns the .ogg count."""
    import soundfile as sf

    if src.parent.exists():
        shutil.rmtree(src.parent)
    src.mkdir(parents=True)
    shutil.copy2(entry, src / "main.py")
    shutil.copytree(ROOT / "jebik", src / "jebik",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.wav"))
    n = 0
    for wav in sorted((ROOT / "jebik").rglob("*.wav")):
        ogg = src / wav.relative_to(ROOT).with_suffix(".ogg")
        data, rate = sf.read(str(wav), always_2d=True)
        sf.write(str(ogg), data, rate, format="OGG", subtype="VORBIS")
        n += 1
    return n


def bake(src: Path) -> None:
    """Pre-render the studio splash layers at web resolution into the staged package."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    sys.path.insert(0, str(ROOT))
    from jebik.art import splash_layers
    splash_layers.bake(src / "jebik" / Path(*splash_layers.BAKED_DIR))


def icons(out: Path) -> None:
    """favicon + apple-touch-icon (180 px, opaque: iOS draws transparency black)."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg

    icon = pg.image.load(str(ROOT / "jebik" / "assets" / "icon.png"))
    for name, size, opaque in (("favicon.png", 64, False), ("apple-touch-icon.png", 180, True),
                               ("icon-512.png", 512, True)):
        img = pg.transform.smoothscale(icon, (size, size))
        if opaque:
            bg = pg.Surface((size, size))
            bg.fill(BG)
            bg.blit(img, (0, 0))
            img = bg
        pg.image.save(img, str(out / name))


def manifest(out: Path) -> None:
    (out / "manifest.webmanifest").write_text(json.dumps({
        "name": TITLE, "short_name": TITLE, "start_url": ".", "scope": ".",
        "display": "fullscreen", "orientation": "landscape",
        "background_color": BG, "theme_color": BG,
        "icons": [{"src": "apple-touch-icon.png", "sizes": "180x180", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "web", help="output folder")
    ap.add_argument("--cdn", default="", help="override pygbag's runtime CDN URL (testing)")
    ap.add_argument("--main", type=Path, default=WEB / "main.py",
                    help="entry script packed as main.py (e.g. a profiling harness)")
    args = ap.parse_args(argv)

    t0 = time.monotonic()
    from importlib.metadata import PackageNotFoundError, version
    try:
        have = version("pygbag")
    except PackageNotFoundError:
        print(f'pygbag missing: pip install "pygbag=={PYGBAG_VERSION}" soundfile', file=sys.stderr)
        return 1
    if have != PYGBAG_VERSION:
        print(f"warning: pygbag {have} installed, the template is for {PYGBAG_VERSION}", file=sys.stderr)
    work = ROOT / "build" / "web-src"
    src = work / APP_NAME            # pygbag names the archive after this folder
    n = stage(src, args.main)
    bake(src)
    print(f"staged {src} ({n} sounds -> .ogg, splash layers baked)")
    icons(work)                      # pygbag copies favicon.png itself
    cmd = [sys.executable, "-m", "pygbag", "--build", "--no_opt",
           "--title", TITLE, "--package", f"web.jebik.{APP_NAME}",
           "--template", str(WEB / "jebik.tmpl"), "--icon", str(work / "favicon.png"),
           "--width", "1920", "--height", "1080", "--ume_block", "1",
           "--can_close", "1"]            # no "leave this page?" nag on exit
    if args.cdn:
        cmd += ["--cdn", args.cdn]
    subprocess.run(cmd + [str(src)], check=True, cwd=src)
    built = src / "build" / "web"
    if not (built / "index.html").is_file():
        print("pygbag produced no index.html", file=sys.stderr)
        return 1
    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    # the .apk twin of the .tar.gz is only used on itch.io
    shutil.copytree(built, out, ignore=shutil.ignore_patterns("*.apk"))
    icons(out)
    manifest(out)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"web build: {out}  ({size / 1e6:.1f} MB, {time.monotonic() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

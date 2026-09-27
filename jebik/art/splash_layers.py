"""The studio splash's pre-rendered layers, at full or reduced resolution.

Desktop draws the splash at full resolution straight from :mod:`splash_art`.
The browser build (WebAssembly: no SIMD blitters, slower numpy) draws it at
``WEB_SCALE`` and upscales the frame; its layers are baked to PNG at build
time (``tools/build_web.py`` -> :func:`bake`) so the page does not spend
seconds extruding the logo before the first frame. Positions / rects stay in
full-resolution screen coordinates; only the images are scaled by ``k``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pygame as pg

from ..paths import resource_path

WEB_SCALE = 0.5
BAKED_DIR = ("assets", "splash_web")         # under the jebik package (web build only)
IMAGES = ("sky", "beam", "flare", "city", "floor", "vignette", "logo")
ALPHA = ("city", "vignette", "logo")


@dataclass
class Layers:
    k: float
    sky: pg.Surface
    beam: pg.Surface
    flare: pg.Surface
    city: pg.Surface
    lights: list[tuple[float, float]]        # spire lights, full-res city-layer coords
    city_box: pg.Rect
    logo: pg.Surface
    logo_rect: pg.Rect
    floor: pg.Surface
    vignette: pg.Surface
    ground: float


def _full() -> Layers:
    from . import splash_art as art
    city, lights, box = art.city()
    logo, rect = art.logo()
    return Layers(1.0, art.sky(), art.beam(), art.flare(), city, list(lights), box,
                  logo, rect, art.floor(), art.vignette(), art.ground_y())


def _scaled(k: float) -> Layers:
    lay = _full()
    if k == 1.0:
        return lay
    for name in IMAGES:
        img = getattr(lay, name)
        w, h = img.get_size()
        setattr(lay, name, pg.transform.smoothscale(img, (max(1, round(w * k)), max(1, round(h * k)))))
    lay.k = k
    return lay


def bake(folder: Path, k: float = WEB_SCALE) -> None:
    """Render the layers at scale ``k`` into ``folder`` (PNG + meta.json)."""
    lay = _scaled(k)
    folder.mkdir(parents=True, exist_ok=True)
    for name in IMAGES:
        pg.image.save(getattr(lay, name), str(folder / f"{name}.png"))
    meta = {"k": k, "lights": lay.lights, "city_box": list(lay.city_box),
            "logo_rect": list(lay.logo_rect), "ground": lay.ground}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _load(k: float) -> Layers | None:
    folder = resource_path(*BAKED_DIR)
    try:
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        if meta.get("k") != k:
            return None
        imgs = {}
        for name in IMAGES:
            img = pg.image.load(str(folder / f"{name}.png"))
            if pg.display.get_surface() is not None:
                img = img.convert_alpha() if name in ALPHA else img.convert()
            imgs[name] = img
        return Layers(k, lights=[tuple(p) for p in meta["lights"]],
                      city_box=pg.Rect(meta["city_box"]), logo_rect=pg.Rect(meta["logo_rect"]),
                      ground=float(meta["ground"]), **imgs)
    except (OSError, ValueError, KeyError, TypeError, pg.error):
        return None


def layers(k: float = 1.0) -> Layers:
    """The splash layers at scale ``k`` (baked ones if shipped, else rendered now)."""
    if k == 1.0:
        return _full()
    return _load(k) or _scaled(k)

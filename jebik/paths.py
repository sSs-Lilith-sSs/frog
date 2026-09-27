"""Where the game's files live: bundled resources and the user's save folder.

*Resources* (fonts, music, level maps, world audio) ship inside the ``jebik``
package. From a source checkout they are next to the code; in a PyInstaller
build (``sys.frozen``) they are unpacked under ``sys._MEIPASS/jebik`` —
:func:`resource_path` hides the difference, so every loader (including level
auto-discovery via ``glob``) works the same in both cases.

*Save data* goes to ``$JEBIK_SAVE_DIR`` if set, else ``~/.jebik`` — on Windows
``%APPDATA%\\jebik`` unless an older ``~/.jebik/save.json`` already exists. The
browser build keeps it in ``localStorage`` instead (:mod:`jebik.web`).

No pygame here: safe to import from headless logic and tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SAVE_DIR_ENV = "JEBIK_SAVE_DIR"


def is_web() -> bool:
    """True in the browser build (pygbag / CPython on WebAssembly)."""
    return sys.platform in ("emscripten", "wasi")


def audio_file(path: Path) -> Path:
    """In the browser, prefer the ``.ogg`` twin of a ``.wav`` (the web build ships
    OGG only: smaller, and what browsers decode best). Desktop: unchanged."""
    if is_web() and path.suffix.lower() == ".wav":
        ogg = path.with_suffix(".ogg")
        if ogg.is_file() or not path.is_file():
            return ogg
    return path


def is_frozen() -> bool:
    """True inside a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False))


def package_dir() -> Path:
    """The ``jebik`` package folder that holds the bundled data files."""
    meipass = getattr(sys, "_MEIPASS", None)
    if is_frozen() and meipass:
        return Path(meipass) / "jebik"
    return Path(__file__).resolve().parent


def resource_path(*parts: str | os.PathLike) -> Path:
    """``resource_path("assets", "fonts", "x.ttf")`` -> absolute path of a bundled file."""
    return package_dir().joinpath(*parts)


def app_dir() -> Path:
    """Folder of the launched program: the ``.exe`` when frozen, else the repo root.
    Users may drop extra files (e.g. ``intro_custom.ogg``) here."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def save_dir() -> Path:
    env = os.environ.get(SAVE_DIR_ENV)
    if env:
        return Path(env).expanduser()
    legacy = Path.home() / ".jebik"
    if sys.platform == "win32" and not (legacy / "save.json").exists():
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "jebik"
    return legacy

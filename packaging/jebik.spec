# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build of «жэбик»:  pyinstaller --noconfirm --clean packaging/jebik.spec

Output: ``dist/jebik/`` = ``jebik.exe`` (``jebik`` on Linux) + ``_internal/``.

Why *onedir* (zipped for download) and not *onefile*: a onefile exe unpacks
Python, SDL and numpy (~60 MB) into a temp folder on **every** start — a few
seconds of black screen, leftovers in %TEMP% after a crash, and it is the
pattern antivirus heuristics most often flag. Onedir starts instantly; the
player just unzips the folder and runs ``jebik.exe``.

Data: every non-Python file inside ``jebik/`` is bundled at the same relative
path (fonts, music/sfx, ``worlds/<id>/levels/*.txt``, ``worlds/<id>/audio``),
so ``jebik.paths.resource_path()`` finds them under ``sys._MEIPASS/jebik``.
Hidden imports: every module of the package — world packages and their
``.art`` modules are imported by name at runtime (``importlib``), which the
static analysis cannot see; listing all of them keeps new worlds/enemies safe.
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent          # noqa: F821 (SPECPATH is set by PyInstaller)
PKG = ROOT / "jebik"
SKIP_SUFFIXES = {".py", ".pyc", ".pyo"}

datas = []
hiddenimports = []
for p in sorted(PKG.rglob("*")):
    if p.is_dir() or "__pycache__" in p.parts:
        continue
    rel = p.relative_to(ROOT)
    if p.suffix == ".py":
        parts = rel.with_suffix("").parts
        hiddenimports.append(".".join(parts[:-1] if parts[-1] == "__init__" else parts))
    elif p.suffix not in SKIP_SUFFIXES:
        datas.append((str(p), str(rel.parent)))

# sanity: fail the build early if the level maps / assets were not picked up
for world in ("water", "earth", "sky"):
    assert any(d[1].replace("\\", "/") == f"jebik/worlds/{world}/levels" for d in datas), world
assert any(d[0].endswith(".ttf") for d in datas) and any(d[0].endswith(".wav") for d in datas)

a = Analysis(                                   # noqa: F821
    [str(ROOT / "frog.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "_pytest", "IPython", "matplotlib", "PIL",
              "requests", "urllib3", "charset_normalizer"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)                               # noqa: F821

exe = EXE(                                      # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,                      # onedir
    name="jebik",                               # -> jebik.exe on Windows
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                                  # UPX-packed exes trip antivirus heuristics
    console=False,                              # windowed: no console window
    disable_windowed_traceback=False,
    icon=str(ROOT / "packaging" / "icon.ico"),
)
coll = COLLECT(                                 # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="jebik",
)

"""Every sound the code asks for exists (scan of the source + the worlds' sound
tables), world sound files are all used, and the generated WAVs are clean."""
import importlib
import re
import wave
from pathlib import Path

import numpy as np
import pytest

from jebik import config
from jebik.worlds import all_worlds

ROOT = Path(__file__).resolve().parents[1]
PLAY = re.compile(r"""\bplay\(\s*["']([\w.]+)["']""")        # audio.play("x") / widgets play("x")
EMIT = re.compile(r"""Event\(\s*["']([\w.]+)["']""")


def _source_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "jebik").rglob("*.py"):
        names.update(PLAY.findall(path.read_text(encoding="utf-8")))
    return names


def _field_classes():
    for w in all_worlds():
        yield w.id, importlib.import_module(w.art_module).ART.field_cls


def _table_names() -> dict[str, set[str]]:
    """world id -> sounds named in its field's event_sounds / tell_sounds."""
    out = {}
    for wid, cls in _field_classes():
        out[wid] = {spec[0] for spec in list(cls.event_sounds.values()) + list(cls.tell_sounds.values())}
    return out


def _boss_worlds() -> set[str]:
    """Worlds with a boss level: the game scene plays ``<world>.boss_hit``."""
    from jebik.worlds import catalog
    return {catalog.load_level(lid).world for lid in catalog.playable_levels()
            if catalog.load_level(lid).boss}


def _file_of(name: str) -> Path:
    if "." in name:
        world, _, rest = name.partition(".")
        return config.WORLDS_DIR / world / "audio" / f"{rest}.wav"
    return config.AUDIO_DIR / f"sfx_{name}.wav"


def _all_names() -> set[str]:
    names = _source_names()
    for table in _table_names().values():
        names |= table
    names |= {f"{w}.boss_hit" for w in _boss_worlds()}
    names.add("sky.boss_defeated")
    return names


def test_source_scan_finds_the_calls():
    names = _source_names()
    assert {"jump", "tongue", "click", "denied"} <= names          # scenes + widgets
    assert all(names for names in _table_names().values())          # every world has sounds


@pytest.mark.parametrize("name", sorted(_all_names()))
def test_every_played_sound_has_a_file(name):
    if "." not in name:
        assert name in config.SFX_NAMES, f"{name!r} is not a core SFX name"
    assert _file_of(name).is_file(), f"missing sound file for {name!r}: {_file_of(name)}"


def test_world_sound_files_are_all_used():
    used = _all_names()
    for w in all_worlds():
        for f in sorted((config.WORLDS_DIR / w.id / "audio").glob("*.wav")):
            assert f"{w.id}.{f.stem}" in used, f"unused sound file {f}"


def test_world_sound_events_are_emitted_by_the_logic():
    """Every world event a field maps to a sound is emitted somewhere."""
    emitted: set[str] = set()
    for path in (ROOT / "jebik").rglob("*.py"):
        emitted.update(EMIT.findall(path.read_text(encoding="utf-8")))
    for wid, cls in _field_classes():
        for kind in cls.event_sounds:
            if kind.startswith(wid + "."):
                assert kind in emitted, f"{kind} has a sound but is never emitted"


def _read(path: Path) -> tuple[np.ndarray, wave._wave_params]:
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767
    return x, params


def _sfx_files() -> list[Path]:
    files = [config.AUDIO_DIR / f"sfx_{n}.wav" for n in config.SFX_NAMES]
    for w in all_worlds():
        files += sorted((config.WORLDS_DIR / w.id / "audio").glob("*.wav"))
    return files


@pytest.mark.parametrize("path", _sfx_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_sound_effects_are_normalised_and_click_free(path):
    x, p = _read(path)
    assert p.nchannels == 1 and p.sampwidth == 2 and p.framerate == 22050
    assert 0.02 < len(x) / p.framerate < 3.5
    peak_db = 20 * np.log10(np.max(np.abs(x)))
    assert -3.3 < peak_db < -2.7                               # about -3 dBFS
    assert abs(x[0]) < 0.01 and abs(x[-1]) < 0.01               # faded ends: no clicks
    assert abs(np.mean(x)) < 0.01                               # no DC offset

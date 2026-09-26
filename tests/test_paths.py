"""Resource / save paths: source checkout vs. a PyInstaller build (sys._MEIPASS)."""
import sys
from pathlib import Path

import jebik
from jebik import config, paths, save
from jebik.worlds import all_worlds, catalog


def test_dev_paths_are_the_package():
    pkg = Path(jebik.__file__).resolve().parent
    assert not paths.is_frozen()
    assert paths.package_dir() == pkg == config.PACKAGE_DIR
    assert paths.resource_path("assets", "fonts") == config.FONT_DIR
    assert config.FONT_BOLD.is_file() and config.AUDIO_DIR.is_dir()
    for w in all_worlds():
        assert w.levels_dir == pkg / "worlds" / w.id / "levels"
        assert w.levels_dir.is_dir()
    assert set(catalog.discovered()) >= set(catalog.playable_levels())


def test_frozen_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "jebik.exe"))
    assert paths.is_frozen()
    assert paths.package_dir() == tmp_path / "jebik"
    assert paths.resource_path("worlds", "sky", "levels") == tmp_path / "jebik/worlds/sky/levels"
    assert paths.app_dir() == (tmp_path / "app").resolve()


def test_save_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path / "s"))
    assert save.save_dir() == tmp_path / "s"
    assert save.save_path() == tmp_path / "s" / "save.json"


def test_save_dir_linux_default_unchanged(monkeypatch, tmp_path):
    monkeypatch.delenv("JEBIK_SAVE_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert paths.save_dir() == tmp_path / ".jebik"


def test_save_dir_windows_appdata_unless_legacy_save(monkeypatch, tmp_path):
    monkeypatch.delenv("JEBIK_SAVE_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    home, appdata = tmp_path / "home", tmp_path / "AppData" / "Roaming"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("APPDATA", str(appdata))
    assert paths.save_dir() == appdata / "jebik"
    (home / ".jebik").mkdir(parents=True)
    (home / ".jebik" / "save.json").write_text("{}", encoding="utf-8")
    assert paths.save_dir() == home / ".jebik"          # keep an existing save
    monkeypatch.delenv("APPDATA")
    (home / ".jebik" / "save.json").unlink()
    assert paths.save_dir() == home / ".jebik"          # no %APPDATA%: fall back


def test_selftest_passes_from_source(monkeypatch, tmp_path):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path))
    from jebik import selftest
    monkeypatch.setattr(selftest, "FRAMES_PER_LEVEL", 3)
    assert selftest.requested(["--selftest"]) and not selftest.requested([])
    assert selftest.main() == 0
    log = (tmp_path / "selftest.log").read_text("utf-8")
    assert "SELFTEST PASSED" in log and "frozen=False" in log

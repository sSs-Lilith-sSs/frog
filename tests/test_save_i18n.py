import json

from jebik import config, i18n, save


def test_missing_file_gives_defaults(tmp_path):
    data = save.load(tmp_path / "save.json")
    assert data.profiles == []
    assert data.current is None
    assert data.settings == config.DEFAULT_SETTINGS


def test_roundtrip(tmp_path):
    path = tmp_path / "save.json"
    data = save.load(path)
    p = data.create_profile("Кыця")
    data.settings["lang"] = "en"
    data.settings["music_track"] = "C"
    assert p.record_result("ezzz", "1-1", 1600, 3, 42.5) is True
    assert data.save()
    back = save.load(path)
    assert back.current == "Кыця"
    assert back.settings["lang"] == "en" and back.settings["music_track"] == "C"
    prog = back.profile.diff("ezzz")
    rec = prog.record("1-1")
    assert rec.completed and rec.stars == 3 and rec.best_score == 1600
    assert rec.best_time == 42.5
    assert [(r.score, r.time, r.stars) for r in rec.runs] == [(1600, 42.5, 3)]


def test_best_values_are_kept(tmp_path):
    data = save.load(tmp_path / "save.json")
    p = data.create_profile("A")
    p.record_result("ezzz", "1-1", 1600, 3, 40)
    assert p.record_result("ezzz", "1-1", 900, 1, 70) is False
    rec = p.diff("ezzz").record("1-1")
    assert rec.stars == 3 and rec.best_score == 1600 and rec.best_time == 40


def test_corrupt_file_falls_back_and_is_moved_aside(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{not json!!", encoding="utf-8")
    data = save.load(path)
    assert data.profiles == [] and data.settings == config.DEFAULT_SETTINGS
    assert (tmp_path / "save.json.corrupt").exists()
    data.create_profile("B")
    assert data.save()
    assert save.load(path).current == "B"


def test_wrong_types_are_sanitised(tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({
        "settings": {"lang": "xx", "music_volume": 7, "sfx_volume": "loud",
                     "music_track": "Z", "fullscreen": "yes"},
        "profiles": [{"name": "  "}, {"name": "Ok", "progress": {"ezzz": {"levels": {
            "1-1": {"stars": 99, "best_score": -5}}}}}, "garbage"],
        "current_profile": "Missing",
    }), encoding="utf-8")
    data = save.load(path)
    s = data.settings
    assert s["lang"] == "ua" and s["music_volume"] == 1.0
    assert s["sfx_volume"] == config.DEFAULT_SETTINGS["sfx_volume"]
    assert s["music_track"] == config.DEFAULT_SETTINGS["music_track"]
    assert s["fullscreen"] is False
    assert [p.name for p in data.profiles] == ["Ok"]
    assert data.current is None
    rec = data.profiles[0].diff("ezzz").record("1-1")
    assert rec.stars == 3 and rec.best_score == 0


def test_profiles_unique_and_delete(tmp_path):
    data = save.load(tmp_path / "save.json")
    data.create_profile("Кыця")
    try:
        data.create_profile("кыця")
        raise AssertionError("duplicate accepted")
    except ValueError:
        pass
    data.delete_profile("Кыця")
    assert data.profiles == [] and data.current is None


def test_env_save_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("JEBIK_SAVE_DIR", str(tmp_path / "x"))
    assert save.save_path() == tmp_path / "x" / "save.json"


def test_next_level_ids():
    from jebik.worlds import catalog
    assert catalog.next_level("1-1", playable_only=False) == "1-2"
    assert catalog.next_level("1-4", playable_only=False) == "2-1"
    assert catalog.next_level("3-4", playable_only=False) is None


def test_i18n_every_key_has_all_languages():
    for key in i18n.keys():
        entry = i18n.raw(key)
        assert len(entry) == len(i18n.LANGS), key
        for text in entry:
            assert isinstance(text, str) and text.strip(), key


def test_i18n_placeholders_match_across_languages():
    import string
    fmt = string.Formatter()
    for key in i18n.keys():
        fields = [sorted(f for _, f, _, _ in fmt.parse(s) if f) for s in i18n.raw(key)]
        assert fields[0] == fields[1] == fields[2], key


def test_i18n_translate_and_fallback():
    i18n.set_lang("en")
    assert i18n.t("menu.play") == "Play"
    assert i18n.t("game.need_exact", n=5) == "need exactly 5"
    i18n.set_lang("ru")
    assert i18n.t("menu.play") == "Играть"
    i18n.set_lang("ua")
    assert i18n.t("menu.play") == "Грати"
    assert i18n.t("no.such.key") == "no.such.key"
    assert i18n.TITLE == "жэбик"


def test_i18n_all_used_keys_exist():
    """Every t("...") literal in the source must be a known key."""
    import re
    from pathlib import Path
    root = Path(i18n.__file__).parent
    known = set(i18n.keys())
    missing = []
    for py in root.rglob("*.py"):
        for key in re.findall(r"""\bt\(\s*["']([a-z_]+\.[a-z0-9_.]+)["']""", py.read_text("utf-8")):
            if key not in known:
                missing.append((py.name, key))
    assert not missing, missing

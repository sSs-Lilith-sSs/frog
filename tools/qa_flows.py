"""Scripted flows for ``tools/qa_soak.py``: splash, profiles, settings, window /
touch events, the EZZZ campaign 1-1…3-4 (cutscenes, credits), TOBI PIZDA,
records, save reload / corruption and a UA / EN / RU text-overflow scan."""
from __future__ import annotations

import json
import sys

import pygame as pg

from jebik import config, i18n, progression, save
from jebik.game.rules import EZZZ, TOBI
from qa_soak import DT, SAVE_DIR, LevelRun, kev, soak_levels

WIDE = "ШШШШШШШШШШШШШШШШ"          # 16 wide letters = MAX_NAME_LEN


def expect(h, cond: bool, kind: str, detail: str) -> bool:
    if not cond:
        h.issue(kind, detail)
    return cond


def text(h, s):
    h.frame([pg.event.Event(pg.TEXTINPUT, text=s)])


# ---------------------------------------------------------------- splash + profile
def splash_and_profile(h):
    h.run(0.6)
    expect(h, h.top_name() == "SplashScene", "flow", f"boot: {h.top_name()} instead of splash")
    h.key(pg.K_SPACE)
    h.settle(0.6)
    expect(h, h.top_name() == "ProfileScene", "flow", f"after splash: {h.top_name()}")
    ps = h.top
    h.key(pg.K_RETURN)                                      # empty name
    expect(h, bool(ps.error) and h.top is ps, "profile", "empty name accepted")
    text(h, "    ")
    h.key(pg.K_RETURN)
    expect(h, h.top is ps and not h.app.save.profiles, "profile", "blank name accepted")
    for _ in range(4):
        h.key(pg.K_BACKSPACE)
    text(h, "Ж" * 40)
    expect(h, len(ps.input.text) <= save.MAX_NAME_LEN, "profile", "name longer than max")
    h.run(0.1)
    h.key(pg.K_BACKSPACE, pg.KMOD_CTRL)
    expect(h, ps.input.text == "", "profile", "ctrl+backspace does not clear")
    text(h, "\x00\t\n")                                     # control chars dropped
    text(h, "Кыця")
    h.key(pg.K_RETURN)
    h.settle(0.5)
    expect(h, h.top_name() == "MainMenuScene" and h.app.save.current == "Кыця", "profile",
           f"create Кыця -> {h.top_name()} current={h.app.save.current}")
    expect(h, save.load().current == "Кыця", "save", "profile not persisted")
    # a second profile with an emoji + a wide max-length one, then back to Кыця
    for name in ("🐸 жабка", WIDE):
        h.app.scenes.top._profiles()
        h.settle(0.4)
        ps = h.top
        ps._start_create()
        text(h, name)
        h.key(pg.K_RETURN)
        h.settle(0.4)
        expect(h, h.app.save.current == name[:16].strip(), "profile", f"create {name!r}")
        h.run(0.3)
    h.top._profiles()
    h.settle(0.4)
    h.top._select("Кыця")
    h.settle(0.4)
    expect(h, h.top_name() == "MainMenuScene", "flow", "select profile")


# ---------------------------------------------------------------- settings
def settings_flow(h):
    h.to_menu()
    s = h.app.settings
    menu = h.top
    menu.focus.index = 0
    menu.focus._fix_index()
    for _ in range(3):
        h.key(pg.K_DOWN)
    h.key(pg.K_RETURN)
    h.settle(0.4)
    expect(h, h.top_name() == "SettingsScene", "flow", f"settings: {h.top_name()}")
    sc = h.top
    rows = sc.focus.widgets
    for i, row in enumerate(rows[:-1]):
        sc.focus.focus(row)
        for k in [pg.K_RIGHT] * 3 + [pg.K_LEFT] * 25 + [pg.K_RIGHT] * 25 + [pg.K_LEFT, pg.K_RETURN]:
            h.key(k, wait=DT)
        h.run(0.2)
    for key in ("music_volume", "sfx_volume"):
        expect(h, 0.0 <= s[key] <= 1.0, "settings", f"{key}={s[key]}")
    expect(h, s["music_track"] in config.MUSIC_TRACKS, "settings", f"track {s['music_track']}")
    expect(h, h.app.audio.track in (None, s["music_track"]), "settings",
           f"audio track {h.app.audio.track} != {s['music_track']}")
    # every language / music / touch value directly, with mouse clicks on the pills
    for row in rows:
        opts = getattr(row, "options", None)
        if not opts:
            continue
        for (value, _), r in zip(opts, row._pill_rects()):
            h.frame([pg.event.Event(pg.MOUSEMOTION, pos=r.center, rel=(0, 0), buttons=(0, 0, 0)),
                     pg.event.Event(pg.MOUSEBUTTONDOWN, pos=r.center, button=1)])
            h.frame([pg.event.Event(pg.MOUSEBUTTONUP, pos=r.center, button=1)])
            expect(h, row.get() == value, "settings", f"click pill {value!r} -> {row.get()!r}")
    slider = rows[0]
    tr = slider.track
    p = (tr.x + int(tr.w * 0.3), tr.centery)
    h.frame([pg.event.Event(pg.MOUSEBUTTONDOWN, pos=p, button=1)])
    h.frame([pg.event.Event(pg.MOUSEMOTION, pos=(tr.right + 400, tr.centery), rel=(0, 0), buttons=(1, 0, 0))])
    h.frame([pg.event.Event(pg.MOUSEBUTTONUP, pos=(tr.right + 400, tr.centery), button=1)])
    expect(h, s["music_volume"] == 1.0, "settings", f"slider drag past end -> {s['music_volume']}")
    h.frame([pg.event.Event(pg.MOUSEWHEEL, x=0, y=-1, flipped=False, precise_y=-1.0, precise_x=0.0)])
    h.app.set_lang("ua")
    h.key(pg.K_ESCAPE)
    h.settle(0.4)
    expect(h, h.top_name() == "MainMenuScene", "flow", "settings back")
    saved = save.load().settings
    expect(h, saved == {**saved, **{k: s[k] for k in saved}}, "save", "settings not persisted")
    s.update(touch="auto", fullscreen=False, show_grid=False)


# ---------------------------------------------------------------- window / touch
def window_and_touch(h):
    from jebik.scenes.game_scene import GameScene
    from jebik.scenes.touch_hud import PAUSE_CENTER
    h.to_menu()
    g = GameScene(h.app, "1-1", seed=3)
    h.app.scenes.push(g, fade=False)
    h.run(0.5)
    for e in (pg.event.Event(pg.VIDEORESIZE, size=(800, 450), w=800, h=450),
              pg.event.Event(pg.WINDOWRESIZED, x=800, y=450),
              pg.event.Event(pg.WINDOWSIZECHANGED, x=640, y=360)):
        h.frame([e])
    h.key(pg.K_F11)
    h.key(pg.K_F11)
    h.frame([kev(pg.KEYDOWN, pg.K_RIGHT)])                  # held...
    h.run(0.3)
    h.frame([pg.event.Event(pg.WINDOWFOCUSLOST)])
    h.settle(0.3)
    expect(h, h.top_name() == "PauseScene", "window", f"focus lost -> {h.top_name()}")
    h.key(pg.K_ESCAPE)
    h.settle(0.3)
    expect(h, h.top is g and not g.held, "window", f"held keys survive pause: {g.held}")
    cell = g.world.frog.cell
    h.run(0.6)
    expect(h, g.world.frog.cell == cell or g.world.frog.state != "idle", "window",
           "frog keeps hopping after pause with no key held")
    # touch: swipe + keyboard at once, then the pause button
    h.app.settings["touch"] = "on"
    for i in range(40):
        x = 0.3 + 0.01 * i
        evs = [pg.event.Event(pg.FINGERDOWN, finger_id=1, x=x, y=0.5, dx=0, dy=0, touch_id=1),
               pg.event.Event(pg.FINGERMOTION, finger_id=1, x=x + 0.2, y=0.5, dx=0, dy=0, touch_id=1),
               pg.event.Event(pg.FINGERUP, finger_id=1, x=x + 0.2, y=0.5, dx=0, dy=0, touch_id=1),
               kev(pg.KEYDOWN, pg.K_UP), kev(pg.KEYUP, pg.K_UP),
               kev(pg.KEYDOWN, pg.K_SPACE), kev(pg.KEYUP, pg.K_SPACE)]
        h.frame(evs)
        h.run(0.1)
        if h.top is not g:
            break
    if h.top is g:
        px, py = PAUSE_CENTER
        fe = dict(finger_id=2, x=px / 1920, y=py / 1080, dx=0, dy=0, touch_id=1)
        h.frame([pg.event.Event(pg.FINGERDOWN, **fe)])
        h.frame([pg.event.Event(pg.FINGERUP, **fe)])
        h.settle(0.3)
        expect(h, h.top_name() == "PauseScene", "touch", f"pause button -> {h.top_name()}")
    h.app.settings["touch"] = "auto"
    h.to_menu()


# ---------------------------------------------------------------- campaign
def campaign(h, stats):
    """Play → EZZZ → 1-1 … 3-4 through the real flow (story, «Далі», finale)."""
    h.to_menu()
    h.app.difficulty = EZZZ
    menu = h.top
    menu.focus.index = 0
    menu.focus._fix_index()
    h.key(pg.K_RETURN)
    h.settle(0.4)
    expect(h, h.top_name() == "DifficultyScene", "flow", f"play -> {h.top_name()}")
    h.key(pg.K_RETURN)
    h.settle(0.4)
    played, cards = [], 0
    h.draw_every = 6
    for _ in range(4000):
        name = h.top_name()
        if name == "CutsceneScene":
            cards += 1
            h.key(pg.K_RETURN, wait=0.3)
        elif name == "GameScene":
            g = h.top
            played.append(g.level_id)
            run = LevelRun(h, g.level_id, len(played), "bot", 150.0)
            run._hook(g)
            out = run.play(start=False)
            stats[("campaign", g.level_id)][out] += 1
            stats[("campaign", g.level_id)]["t"] += int(run.t)
            if out not in ("win", "forced"):
                h.issue("campaign", f"{g.level_id}: {out}")
                break
        elif name == "WinScene":
            h.run(1.0)
            h.key(pg.K_RETURN)
            h.settle(0.5)
        elif name == "LevelSelectScene":
            break
        else:
            h.issue("campaign", f"unexpected {name}")
            break
    h.draw_every = 1
    from jebik.worlds import catalog
    expect(h, played == catalog.playable_levels(), "campaign", f"order {played}")
    p = h.app.profile
    expect(h, p.has("story.final") and p.has("story.intro"), "campaign", f"story flags {p.flags}")
    expect(h, progression.tobi_unlocked(p), "campaign", "TOBI not unlocked after EZZZ")
    expect(h, h.top_name() == "LevelSelectScene", "campaign", f"after credits: {h.top_name()}")
    expect(h, cards >= 5, "campaign", f"only {cards} cutscene cards seen")


# ---------------------------------------------------------------- TOBI
def tobi_flow(h, levels, runs, stats):
    from jebik.scenes.game_scene import GameScene
    p = h.app.profile
    if not progression.tobi_unlocked(p):
        h.issue("tobi", "TOBI locked when the TOBI phase started; unlocking by flag")
        p.mark(progression.TOBI_FLAG)
    h.app.difficulty = TOBI
    for lid in levels:
        h.ctx = f"tobi checks {lid}"
        # time-out -> lose panel
        h.to_menu()
        g = GameScene(h.app, lid, seed=5)
        h.app.scenes.push(g, fade=False)
        h.run(0.3)
        w = g.world
        expect(h, w.time_left is not None and w.hearts == 1, "tobi", f"{lid} rules {w.rules}")
        w.time_left = 0.4
        w.frog.invuln = 99
        h.run(3.0)
        expect(h, h.top_name() == "LoseScene" and w.lose_reason == "timeout", "tobi",
               f"{lid} timeout -> {h.top_name()} {w.lose_reason}")
        # one hit -> automatic restart with a fresh timer
        h.to_menu()
        g = GameScene(h.app, lid, seed=6)
        h.app.scenes.push(g, fade=False)
        h.run(2.5)
        g.world.frog.invuln = 0
        if g.world.frog.state in ("idle", "tongue"):
            g.world.hurt_frog(None)
            h.run(config.TOBI_RESTART_DELAY + 0.6)
            g2 = h.game
            ok = g2 is not None and g2 is not g and h.top is g2
            expect(h, ok, "tobi", f"{lid} one-hit restart -> {h.top_name()}")
            if ok:
                w2 = g2.world
                expect(h, abs(w2.time_left - w2.level.tobi_time) < 1.0 and w2.eaten == 0 and not w2.damaged,
                       "tobi", f"{lid} restart state: t={w2.time_left} eaten={w2.eaten}")
                g = g2
        # golden fly = +10 s
        w = g.world
        f = w.frog
        h.run(0.1)
        if f.can_act and w.state == "playing":
            for d in range(4):
                from jebik.game.grid import step
                n = step(f.cell, d)
                if w.tiles.standable(n) and not w.blocked(n) and not w.flies.at_cell(n):
                    f.invuln = 5
                    w.flies.spawn_at("gold", n, rest=5.0)
                    before = w.time_left
                    h.frame([kev(pg.KEYDOWN, {0: pg.K_UP, 1: pg.K_RIGHT, 2: pg.K_DOWN, 3: pg.K_LEFT}[d])])
                    h.run(0.4)
                    expect(h, w.time_left > before + 9, "tobi", f"{lid} gold: {before:.1f} -> {w.time_left:.1f}")
                    break
        # overeat after full -> restart
        if w.state == "playing" and h.top is g:
            w.eaten = w.needed - 1
            w.flies.spawn_at("dragon", w.frog.cell)
            fly = w.flies.flies[-1]
            w._eat(fly)
            expect(h, w.state == "lost" and w.lose_reason == "overeat", "tobi",
                   f"{lid} dragon at N-1 in TOBI: state={w.state} reason={w.lose_reason}")
            h.run(config.TOBI_RESTART_DELAY + 0.6)
            expect(h, h.game is not g, "tobi", f"{lid} overeat did not restart")
    soak_levels(h, levels, runs, stats, TOBI, budget=200.0)
    h.app.difficulty = EZZZ


def memory_loop(h, stats):
    h.app.difficulty = EZZZ
    h.draw_every = 4
    for i in range(25):
        run = LevelRun(h, "1-1", 50 + i, "random", 8.0)
        run.start()
        for _ in range(int(8 / DT)):
            h.frame(run._random_events())
            if h.game is None:
                break
        if h.game is not None and h.top is h.game:
            h.key(pg.K_ESCAPE)
            h.settle(0.2)
            if h.top_name() == "PauseScene":
                h.top.restart()
                h.settle(0.4)
    h.draw_every = 1


# ---------------------------------------------------------------- records, profiles, saves
def records_profiles_saves(h):
    from jebik.scenes.records import RecordsScene
    h.to_menu()
    for lang in i18n.LANGS:
        h.app.set_lang(lang)
        h.app.scenes.push(RecordsScene(h.app), fade=False)
        for _ in range(15):
            h.key(pg.K_RIGHT, wait=DT)
        h.key(pg.K_TAB)
        for _ in range(15):
            h.key(pg.K_LEFT, wait=DT)
        h.key(pg.K_ESCAPE)
        h.settle(0.3)
    h.app.set_lang("ua")
    # profile switching: TOBI must not carry over to a profile that has not unlocked it
    h.app.difficulty = TOBI
    h.top._profiles()
    h.settle(0.4)
    ps = h.top
    ps._start_create()
    text(h, "Друга")
    h.key(pg.K_RETURN)
    h.settle(0.5)
    p = h.app.profile
    expect(h, p is not None and p.name == "Друга", "profile", "switch to new profile")
    expect(h, progression.is_unlocked(p, h.app.difficulty, "1-1"), "profile",
           f"new profile sees 1-1 locked (difficulty {h.app.difficulty} carried over)")
    # delete Кыця with the Delete key + "Yes"
    h.top._profiles()
    h.settle(0.4)
    ps = h.top
    row = next(w for w in ps.focus.widgets if getattr(w, "profile_name", None) == "Кыця")
    ps.focus.focus(row)
    h.key(pg.K_DELETE)
    expect(h, ps.mode == "confirm", "profile", "Delete key did not ask")
    ps.focus.index = 0
    h.key(pg.K_RETURN)
    expect(h, h.app.save.find("Кыця") is None, "profile", "Кыця not deleted")
    # delete the current profile: no way back to a menu without a profile
    row = next(w for w in ps.focus.widgets if getattr(w, "profile_name", None) == "Друга")
    ps._ask_delete("Друга")
    ps._do_delete()
    h.key(pg.K_ESCAPE)
    h.settle(0.3)
    expect(h, h.top is ps and h.app.save.current is None, "profile",
           f"Esc after deleting current -> {h.top_name()} current={h.app.save.current}")
    names = [q.name for q in h.app.save.profiles]
    ps._select(names[0])
    h.settle(0.4)
    h.app.persist()
    # reload the save in a fresh App
    before = save.load().to_json()
    h.new_app(splash=False)
    h.run(0.3)
    after = h.app.save.to_json()
    expect(h, before == after, "save", "save changed across an App restart")
    expect(h, h.top_name() == "ProfileScene", "flow", f"restart -> {h.top_name()}")
    # corrupt / odd saves
    path = SAVE_DIR / "save.json"
    for raw in (b"{not json", b"\xff\xfe\x00garbage", b"[]", b"null",
                json.dumps({"settings": [], "profiles": "x", "current_profile": 5}).encode(),
                json.dumps({"settings": {"music_volume": 1e309, "lang": "de", "touch": 3},
                            "profiles": [{"name": " "}, {"name": "A" * 99, "progress": {"ezzz": {"levels": {
                                "1-1": {"stars": 99, "best_score": -5, "runs": [{"time": "x"}, 5]}}}}},
                                         {"name": "a"}, {"name": "A"}],
                            "current_profile": "a"}).encode()):
        path.write_bytes(raw)
        try:
            h.new_app(splash=False)
            h.run(0.3)
            h.app.persist()
            data = save.load()
            expect(h, all(1 <= len(q.name) <= save.MAX_NAME_LEN for q in data.profiles), "save",
                   f"bad names after {raw[:20]!r}")
        except Exception as exc:                          # noqa: BLE001
            h.issue("save", f"load {raw[:24]!r}: {exc!r}")
    h.new_app(splash=False)
    h.to_menu()


# ---------------------------------------------------------------- locale overflow
def locale_scan(h):
    import qa_locale
    qa_locale.scan(h)


if __name__ == "__main__":
    sys.exit("run tools/qa_soak.py")

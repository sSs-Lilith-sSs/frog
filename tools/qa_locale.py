"""Text-overflow scan for ``tools/qa_soak.py``: renders every screen in UA / EN /
RU and checks, from the rects ``draw_text`` returns, that no text leaves the
screen, sticks out of the panel / button it sits in, or overlaps another text."""
from __future__ import annotations

import sys

import pygame as pg

from jebik import config, i18n
from jebik.game.rules import EZZZ, TOBI, compute_result

WIDE = "ШШШШШШШШШШШШШШШШ"
_calls: list[tuple[str, pg.Rect]] = []
_orig = None


def _install():
    global _orig
    from jebik.art import common
    if _orig is not None:
        return
    _orig = common.draw_text

    def rec(surf, text, *a, **k):
        r = _orig(surf, text, *a, **k)
        if surf.get_size() == (config.SCREEN_W, config.SCREEN_H) and str(text).strip():
            _calls.append((str(text), pg.Rect(r)))
        return r
    for name, mod in list(sys.modules.items()):
        if name.startswith("jebik") and getattr(mod, "draw_text", None) is _orig:
            mod.draw_text = rec


def _containers(scene) -> list[tuple[str, pg.Rect]]:
    out = []
    focus = getattr(scene, "focus", None)
    for w in (focus.widgets if focus else []):
        if w.visible:
            out.append((type(w).__name__, pg.Rect(w.rect)))
    for attr in ("panel",):
        r = getattr(scene, attr, None)
        if isinstance(r, pg.Rect):
            out.append((attr, pg.Rect(r)))
    name = type(scene).__name__
    if name == "RecordsScene":
        from jebik.scenes.records import PANEL
        out.append(("records.PANEL", PANEL))
    if name == "CutsceneScene" and scene.card.art != "credits":
        from jebik.scenes.cutscene import TEXT
        out.append(("cutscene.TEXT", TEXT))
    if name == "HowToScene":
        out += [("howto.card", r) for r in scene.cards]
    return out


def check(h, label: str):
    _calls.clear()
    h.frame([])
    scene = h.top
    scr = pg.Rect(0, 0, config.SCREEN_W, config.SCREEN_H).inflate(4, 4)
    conts = _containers(scene)
    for s in h.app.scenes.stack:            # overlays: also the panels below the top
        if s is not scene:
            conts += [c for c in _containers(s) if c[0] == "panel"]
    for text, r in _calls:
        if not scr.contains(r):
            h.issue("text_offscreen", f"{label}: {text!r} {tuple(r)}")
        for cname, c in conts:
            if c.collidepoint(r.center) and not c.inflate(6, 6).contains(r):
                h.issue("text_overflow", f"{label}: {text!r} {tuple(r)} out of {cname} {tuple(c)}")
                break
    for i, (ta, ra) in enumerate(_calls):
        for tb, rb in _calls[i + 1:]:
            if ta == tb:
                continue
            a, b = ra.inflate(-10, -10), rb.inflate(-10, -10)
            if a.colliderect(b):
                inter = a.clip(b)
                if inter.w * inter.h > 0.15 * min(a.w * a.h, b.w * b.h):
                    h.issue("text_overlap", f"{label}: {ta!r} overlaps {tb!r}")


def scan(h):
    from jebik.scenes.cutscene import CutsceneScene
    from jebik.scenes.difficulty import DifficultyScene
    from jebik.scenes.game_scene import GameScene
    from jebik.scenes.howto import HowToScene
    from jebik.scenes.level_select import LevelSelectScene
    from jebik.scenes.main_menu import MainMenuScene
    from jebik.scenes.overlays import LoseScene, PauseScene, WinScene
    from jebik.scenes.profile import ProfileScene
    from jebik.scenes.records import RecordsScene
    from jebik.scenes.settings import SettingsScene
    from jebik import story
    from jebik.worlds import all_worlds
    _install()
    app = h.app
    if app.save.find(WIDE) is None:
        app.save.create_profile(WIDE)
    app.save.current = WIDE
    prof = app.save.profile
    prof.record_result(EZZZ, "1-1", 123456, 3, 3599.9)
    app.save.find("Кыця") or app.save.create_profile("Кыця")
    app.save.current = WIDE

    def reset(scene):
        app.scenes.reset(MainMenuScene(app), fade=False)
        if scene is not None:
            app.scenes.push(scene, fade=False)
        h.run(0.5)

    for lang in i18n.LANGS:
        app.set_lang(lang)
        L = lang.upper()
        for diff in (EZZZ, TOBI):
            app.difficulty = diff
            reset(None)
            check(h, f"{L} MainMenu")
            for cls in (DifficultyScene, LevelSelectScene, RecordsScene, SettingsScene, HowToScene):
                reset(cls(app))
                check(h, f"{L} {cls.__name__} {diff}")
            reset(RecordsScene(app))
            h.top.selector.index = 1
            h.top._refresh()
            check(h, f"{L} Records 1-1 {diff}")
            for lid in ("1-1", "1-4", "2-4", "3-4"):
                g = GameScene(app, lid, seed=1)
                reset(g)
                check(h, f"{L} Game {lid} {diff}")
                w = g.world
                w.eaten, w.full = w.needed, True
                check(h, f"{L} Game {lid} full {diff}")
                app.scenes.push(PauseScene(app, g), fade=False)
                h.run(0.3)
                check(h, f"{L} Pause {lid}")
                app.scenes.push(SettingsScene(app, over_game=True), fade=False)
                h.run(0.3)
                check(h, f"{L} Settings over game")
                app.scenes.pop(fade=False)
                app.scenes.pop(fade=False)
                w.result = compute_result(lid, diff, 3599.9, w.needed, 3, True, 60,
                                          999.0 if diff == TOBI else None)
                g.new_best = True
                app.scenes.push(WinScene(app, g), fade=False)
                h.run(2.0)
                check(h, f"{L} Win {lid} {diff}")
                app.scenes.pop(fade=False)
                w.lose_reason = "timeout" if diff == TOBI else "hearts"
                app.scenes.push(LoseScene(app, g), fade=False)
                h.run(0.5)
                check(h, f"{L} Lose {lid} {diff}")
        app.difficulty = EZZZ
        for mode in ("list", "create", "confirm"):
            ps = ProfileScene(app, from_menu=True)
            reset(ps)
            if mode == "create":
                ps._start_create()
                ps.input.text = WIDE
                ps.error = i18n.t("profile.err_exists")
            elif mode == "confirm":
                ps._ask_delete(WIDE)
            h.run(0.2)
            check(h, f"{L} Profile {mode}")
        cards = list(story.INTRO) + [c for w in all_worlds() for c in story.world_cards(w.id)] \
            + list(story.FINAL)
        cut = CutsceneScene(app, cards, on_done=lambda: None)
        reset(cut)
        for i in range(len(cards)):
            cut.index, cut.card_t = i, 99.0
            h.run(0.2)
            check(h, f"{L} Cutscene {cards[i].text_key or cards[i].art}")
    app.set_lang("ua")
    app.save.current = "Кыця"
    reset(None)


if __name__ == "__main__":
    sys.exit("run tools/qa_soak.py")

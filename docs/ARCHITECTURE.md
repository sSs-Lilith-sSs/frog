# жэбик — architecture & world-agent guide

The game is split so that the three worlds (water, earth, sky) can be built
**in parallel**, each by its own agent in its own git worktree, touching only
its own files.

## 1. Layers

| Layer | Where | Rule |
|---|---|---|
| Logic | `jebik/game/`, `jebik/worlds/<id>/*.py` | **no pygame**; deterministic with a seed; covered by tests |
| Art | `jebik/art/`, `jebik/worlds/<id>/art/` | pygame drawing only; supersample, cache, never logic |
| Glue | `jebik/scenes/` | turns logic events into view/effects/audio; menus, HUD |
| Data | `jebik/worlds/<id>/levels/*.txt`, `strings.py`, `config.py` | text maps, UA/EN/RU strings, tunables |

Core pieces a world uses:

* `game/grid.py` — `Level` + the **level file format** (docstring has the full spec).
* `game/tiles.py` — live `TileMap`: `SOLID` / `HOLE` / `OBSTACLE` tiles + generic
  hazards (unstable tiles, moving rows, temporary holes). Tiles keep a stable `id`.
* `game/enemy.py` — `Enemy` / `Boss` base classes, `Telegraph`, `@register_enemy`.
* `game/world.py` (+ `actions.py`, `goals.py`, `damage.py` mixins) — one running level.
* `worlds/base.py` — `WorldDef` + `Theme`; `worlds/catalog.py` — level discovery,
  the fixed 1-1…3-4 order, "playable" levels.
* `art/field.py` — `FieldRenderer` base; `art/enemy_art.py` — `EnemyArt` base +
  `@register_enemy_art`; `art/world_art.py` — `WorldArt` base + `art_for(world_id)`.
* `progression.py` (unlocks), `records.py` (tables), `story.py` (cutscene hooks).

## 2. Files a world agent may touch

Only these (replace `<id>` with `water`, `earth` or `sky`):

```
jebik/worlds/<id>/**                 # the whole package: logic, art, levels, strings, config, audio
tests/test_<id>_*.py                 # your tests (flat in tests/, conftest helpers are importable)
tools/shots/<id>.py                  # your screenshot hook (shots(d)); PNG names start with "<id>_"
tools/gen_audio_<id>.py              # optional: generator for jebik/worlds/<id>/audio/*.wav
```

Everything else is framework. If you truly need a framework change, keep it
minimal, additive and mention it in your report — the three worktrees are merged
afterwards. Do **not** edit `jebik/i18n.py`, `jebik/config.py`, `tools/screenshot.py`,
`tests/conftest.py`, other worlds, or the core flow. The water agent must keep the
names `pad_sprite`, `exit_sprite` (`art/pads.py`) and `SnakeArt` (`art/snake_art.py`)
because the "How to play" screen draws with them.

## 3. A world package

```
jebik/worlds/<id>/
  __init__.py       WORLD = register_world(WorldDef(id, index, theme, playable, levels_dir,
                                                    art_module, strings, story));
                    imports the enemy modules so they register
  config.py         your tunables (never hard-code numbers in logic)
  strings.py        STRINGS = {"<id>.key": (ua, en, ru)}  — merged into i18n automatically
  enemies.py / *.py logic: @register_enemy classes (no pygame!)
  levels/<w>-<n>.txt
  audio/<name>.wav  optional, played as audio.play("<id>.<name>")
  art/__init__.py   ART = <Id>Art()  (WorldArt subclass); imports the enemy renderers
  art/*.py          field renderer, decor, characters
```

* **Theme** (`WorldDef.theme`): HUD bar colour + accent line (water dark green,
  earth brown-green + gold, sky plum + pink), level-select tile colours, popup outline.
* **Playable levels**: `playable=(1, 2, …)`. A level is offered (level select,
  «Далі», unlock chain) only if its file exists **and** it is listed here — keep
  WIP maps in `levels/` without exposing them. Unbuilt levels show «скоро».
* **Story**: `story=("<id>.story.1", …)` — cards shown before `<w>-1` the first time.
  Draw your own illustration in `WorldArt.draw_story(card, surf, rect, t)`
  (return True), else a generic picture with your world icon is used.
* **Strings**: keys must start with `<id>.` (enforced). Needed ones:
  `<id>.name`, `<id>.exit_hint` («стрибай на лотос / у нору / на веселку»),
  your boss name (e.g. `<id>.boss`), `<id>.story.*`. Placeholders `{n}` must
  match across languages (tested).

## 4. Levels

Full format in the `jebik/game/grid.py` docstring. Summary:

```
id: 2-3                     world: earth           size: 18x11
flies_needed: 14            par_time: 90           tobi_time: 95
spawn: H=hedgehog, P=pike:hole          # map letter -> enemy kind (":hole" = not a tile)
enemies: fox @ 3 4 speed=1.2; crow      # more enemies; "@ x y" and key=value optional
boss: boar hp=3                         # the boss (also an enemy); reserves the HUD pill row
unstable: warn=1.5 gone=4 trigger=step  # 'U' tiles (step = when landed on, cycle = own timer)
moving: 2 right 3.0; 5 left 2.5         # rows shifting one cell every N s
cell: 50                                # fixed cell px (default adaptive, <= 80)
top_reserve: 160                        # px kept free above the field (Jesus on his cloud)
---
O solid · # hole · F frog start · U unstable · X obstacle (stump) · letters from spawn:
```

Levels are discovered automatically; `catalog.load_level()` checks that `id`
matches the file name and `world` matches the package. Sizes / flies / timers:
see `docs/TZ.md` §4. Spawn params reach the enemy as `spawn.param("speed", 1.0)`.

## 5. Enemies (logic)

```python
from jebik.game.enemy import Enemy, Telegraph, register_enemy, GROUND

@register_enemy("hedgehog")
class Hedgehog(Enemy):
    layer = GROUND                      # UNDER (below tiles, e.g. whale shadow) / GROUND / AIR

    @classmethod
    def create(cls, world, spawn):      # optional; default puts pos at spawn.cell
        e = super().create(world, spawn)
        e.speed = spawn.param("speed", cfg.HEDGEHOG_SPEED)
        return e

    def update(self, dt, world):
        super().update(dt, world)       # anim clock + stun countdown
        target = world.frog_target      # frog cell, or None (splashing / level over)
        ...                             # move self.pos (float cell units)
```

Hooks (all optional, harmless defaults): `hurts(world, frog_pos)` contact damage
(default: distance < `contact_radius`, not while `stunned`), `occupied()` cells
the exit/respawn avoid, `telegraphs()` → `[Telegraph(style, cells, progress, direction)]`
(generic looks: `zone`, `line`, `arrow`, `shadow`, `bubbles`/`shake`),
`supports(cell)` frog can stand on you (whale back), `blocks(cell)`,
`tongue_hit(world, line)` → index where the tongue stops at you, then
`on_tongued(world)`, `on_frog_hit`, `on_frog_respawn`, `on_frog_land`, `stun(s)`.

World API for enemies: `world.frog`, `world.frog_target`, `world.tiles`
(`standable`, `is_hole`, `blocks`, `neighbors`, `make_hole`, `set_kind`,
`row_offset`), `world.can_stand(cell)`, `world.make_hole(cell, s)`,
`world.hurt_frog(self)` (direct strike; respects invulnerability / super-jump
air time), `world.push_frog(dir, n)` (wave, gulp, wind — may drop into a hole),
`world.haste(factor, s)` + `world.enemy_speed` (crow), `world.flies`
(`spawn_at`, `spawn_from_edge`, `at_cell`, `remove`), `world.rng` (always use it —
tests are seeded), `world.emit(Event("<id>.whatever", ...))`, `world.eaten/needed`.
Snake (`jebik/worlds/water/snake.py`) is the reference implementation.

## 6. Bosses

Subclass `Boss` (hp = `config.BOSS_HP` = 3 or `boss: kind hp=N`):
`name_key` (HUD pill name), `hit_text_key` (popup on a hit — sky uses
`"sky.sasat"` «SASAT!»), `open_window(seconds)` starts a vulnerability window
(glowing pill border), `take_hit(world)` only works inside it and closes it; at
hp 0 → `defeated`, `BOSS_DEFEATED` event. Default `on_tongued` = `take_hit`, so a
tongue-vulnerable boss only needs `tongue_hit()` + windows. The exit appears when
**exactly** N flies are eaten **and** the boss is defeated (either order).
`enraged(world)` = half the flies eaten. Portrait for the pill:
`WorldArt.boss_icon(kind, 44)`.

## 7. Hazards (generic, just use them in level files / from enemies)

* Unstable tiles `U`: STABLE → WARNING (flicker, 1.5 s) → GONE (N s) → STABLE.
  The frog on a vanishing tile falls; resting flies take off.
* Temporary holes: `world.make_hole(cell, seconds)` (mole 8 s, whale 5 s, boar trail).
* Obstacles `X`: nobody can hop in; super jump flies over; enemies path around.
* Moving rows: whole row shifts (wrapping); grounded frog + resting flies ride
  along; carried off the edge = fall. The exit / respawn avoid moving rows and unstable tiles.

Events for renderers: `TILE_WARN/GONE/BACK`, `HOLE_OPEN/CLOSE`, `ROW_SHIFT`.

## 8. Art

* `FieldRenderer` subclass: `build_static()` (full-screen backdrop + field floor —
  water/pit/abyss everywhere; tiles are drawn on top), `tile_sprite(tile, cell)`
  (cached per tile id), optional `tile_image` (animation frames), `tile_center`,
  `obstacle_sprite`, `draw_exit(surf, center, age)` (lotus / burrow / rainbow),
  `update(dt, world, effects, view)` ambience, `on_event(event, view, effects,
  audio)` — **every** world event passes here first (return True to replace the
  default reaction). Hazard animations (flicker, sink, pop-in, row slide, landing
  dip) are done by the base. `level_cache()` keeps surfaces across restarts.
  Moving rows are clipped to the field frame (their tiles slide / wrap through it).
* **Sounds**: map events to sounds in the field class —
  `event_sounds = {"earth.stomp": ("earth.stomp", 1.2), ev.TILE_WARN: ("earth.crumble_warn", 1.1, .35)}`
  (sound, volume[, min gap s]) and `tell_sounds = {"charge": (...)}` for `BOSS_TELL`
  attack names — then call `self.event_sound(event, audio)` first thing in
  `on_event`. The game scene plays `"<id>.boss_hit"` / `"<id>.boss_defeated"` if the
  world ships them (else the core `hit` / `win`). Generate the WAVs with
  `tools/gen_audio_<id>.py` (shared kit: `tools/synth.py`: soft envelopes, filtered
  noise, bells, room tail, -3 dBFS peak, faded ends). `tests/test_audio_assets.py`
  checks that every played name has a file and every world file is used.
* Enemies: `@register_enemy_art("kind") class XArt(EnemyArt)` with
  `draw(surf, enemy, off)`; `self.px(pos, off)`, `self.k` (= cell/64), `self.cs`,
  `self.view.t`. Optional `draw_telegraph(...)` → True to replace the generic
  warning. Unregistered kinds render as a labelled placeholder disc.
  UNDER / GROUND enemies (and their warnings) are clipped to the field frame,
  AIR ones are not (birds, a leaping pike, a boss above the field); set
  `clip = True / False` on the art class to force it.
* `WorldArt`: `field_cls`, `icon(size)`, `boss_icon(kind, size)`, `draw_story(...)`.
* **Style**: port the approved mockups; draw at ×3 (`render_ss(size, draw, ss=3)`,
  which supersamples then `smooth_down`s with clean alpha); cache every static
  surface (`functools.lru_cache` / `level_cache()`); numpy only at build time —
  **never per frame** — and at screen resolution when the result is soft anyway
  (blurs, noise, shading); supersample only the crisp vector parts. A level must
  load in well under 1.5 s. Keep drawing code in units of `k` so all cell sizes work
  (≈50 px on 3-4 up to 80 px). Keep files < 400 lines.

## 9. Tests & screenshots

* `tests/test_<id>_*.py`; `from conftest import make_level, make_world, run`
  (`make_world(rows, flies_needed, enemies=True, header="spawn: H=hedgehog")`).
  Test logic headless with fixed seeds: movement rules, telegraph timing, hits,
  boss windows, exit condition, level files parse (`catalog.load_level`).
  `tests/test_framework_*.py` show the patterns. Run `python3 -m pytest -q`.
* `tools/shots/<id>.py`: `def shots(d)`; `g = d.play("2-3", seed=5)` pushes a
  GameScene, `d.run(sec)`, `d.key(pg.K_RIGHT)`, `d.shot("<id>_05_boar")`,
  `d.go_menu()`. Run `python3 tools/screenshot.py screenshots --only <id>`.
* Also run `JEBIK_AUTOQUIT=3 python3 frog.py` (headless: `SDL_VIDEODRIVER=dummy`).

## 10. Progression, modes, cutscenes (framework, for reference)

* Unlock chain over playable levels (`progression.py`); TOBI PIZDA opens after all
  playable EZZZ levels (sticky profile flag). Progress/records per difficulty.
* TOBI PIZDA (`rules_for(TOBI, level)`): no hearts, `tobi_time` countdown in the
  HUD, golden fly +10 s, any hit / fall / extra fly → automatic restart; time-out →
  lose panel.
* Records: each profile keeps its top 10 runs per level; tables merge profiles.
* Cutscenes (`story.py` + `scenes/cutscene.py`): intro before 1-1, world story
  before 2-1 / 3-1, finale + credits after 3-4.
* Studio splash (`scenes/splash.py`, `art/splash_art.py`): skippable; plays
  `assets/audio/intro_custom.ogg|wav` if present, else the generated fanfare.

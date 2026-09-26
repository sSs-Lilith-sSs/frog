"""Sky-world enemies (TODO: sky agent).

Planned (docs/TZ.md §8), each ``@register_enemy("<kind>")`` subclassing
:class:`jebik.game.enemy.Enemy` / :class:`jebik.game.enemy.Boss`:

* ``swallow`` — edge arrow for 1 s (``Telegraph("arrow")``), then flies
  through a whole row / column;
* ``hawk`` — flies over the abyss, slower than the frog, dashes 2 cells when close;
* ``crow`` — eats flies (``world.flies``), caws: ``world.haste(1.5, 3)``, pecks nearby;
* ``jesus`` (Boss, ``layer = AIR``, lives in the level's ``top_reserve`` area)
  — palm beams along a row/column, multiplies flies (10–15), halo boomerang,
  rebuilds clouds (``world.tiles.set_kind``). Catch the halo with the tongue
  (``tongue_hit``) -> it flies back -> ``take_hit`` with ``hit_text_key =
  "sky.sasat"`` («SASAT!»). After 3 hits: sad face, final credits.

Nothing is registered yet, so sky levels must not reference these kinds.
"""
from __future__ import annotations

"""Earth-world enemies (TODO: earth agent).

Planned (docs/TZ.md §8), each ``@register_enemy("<kind>")`` subclassing
:class:`jebik.game.enemy.Enemy` / :class:`jebik.game.enemy.Boss`:

* ``hedgehog`` — rolls straight along the frog's row/column; falls into a pit
  and is gone for 5 s;
* ``fox`` — fast chaser, jumps over pits, 1 s recovery after a jump;
* ``mole`` — a trembling mound underground (``Telegraph("shake")``), pops up
  under the frog and leaves a pit for 8 s (``world.make_hole(cell, 8)``);
* ``boar`` (Boss, 2x2) — charges in a line leaving pits, stunned 2 s at the
  edge, stomp crumbles 5 cells; lure it into a stump (``X`` tiles) ->
  stunned 3 s (``open_window(3)``) -> tongue hit.

Nothing is registered yet, so earth levels must not reference these kinds.
"""
from __future__ import annotations

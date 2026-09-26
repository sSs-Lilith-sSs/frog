"""Earth-world enemies (docs/TZ.md §8) — importing this registers them:

* ``hedgehog`` (:mod:`.hedgehog`) — rolls along the frog's clear row/column; a pit hides it for 5 s;
* ``fox`` (:mod:`.fox`) — fast BFS chaser, leaps single pits, 1 s recovery after a leap;
* ``mole`` (:mod:`.mole`) — underground mound, tremor under the frog, pops -> pit for 8 s;
* ``boar`` (:mod:`.boar`, Boss 2x2) — lane charges leaving pits, stumps stun it, stomps crumble cells.
"""
from __future__ import annotations

from .boar import Boar
from .fox import Fox
from .hedgehog import Hedgehog
from .mole import Mole

__all__ = ["Boar", "Fox", "Hedgehog", "Mole"]

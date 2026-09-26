"""The heron: a shadow falls on the frog's cell, 1.2 s later the beak strikes (no pygame).

Between strikes she circles high above (not drawn on the field). The shadow
stays on the cell where it appeared, so hopping away dodges the beak.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...game.enemy import AIR, Enemy, Telegraph, register_enemy
from ...game.events import Event
from ...game.grid import Cell, Spawn
from . import config as wc

if TYPE_CHECKING:
    from ...game.world import World

AWAY = "away"
SHADOW = "shadow"
STRIKE = "strike"
LEAVE = "leave"


@register_enemy("heron")
class Heron(Enemy):
    layer = AIR
    contact_radius = 0.5

    def __init__(self) -> None:
        self.state = AWAY
        self.timer = 0.0
        self.target: Cell | None = None
        self.pos = (-3.0, -3.0)
        self.anim = 0.0
        self.stunned = 0.0
        self.strikes = 0

    @classmethod
    def create(cls, world: "World", spawn: Spawn) -> "Heron":
        heron = cls()
        heron.timer = world.rng.uniform(*wc.HERON_FIRST)
        return heron

    def occupied(self) -> set[Cell]:
        return {self.target} if self.target is not None and self.state != AWAY else set()

    def hurts(self, world: "World", frog_pos) -> bool:
        return (self.state == STRIKE and self.target is not None
                and math.dist(frog_pos, self.target) < self.contact_radius)

    def telegraphs(self) -> list[Telegraph]:
        if self.state == SHADOW and self.target is not None:
            return [Telegraph("shadow", (self.target,), 1 - self.timer / wc.HERON_WARN)]
        return []

    def phase(self) -> float:
        """0 -> 1 progress of the current state (for the renderer)."""
        total = {SHADOW: wc.HERON_WARN, STRIKE: wc.HERON_STRIKE, LEAVE: wc.HERON_LEAVE}.get(self.state)
        return 1 - self.timer / total if total else 0.0

    def on_frog_respawn(self, world: "World", cell: Cell) -> None:
        if self.state == SHADOW:                      # no strike on a fresh respawn
            self.state, self.timer, self.target = AWAY, world.rng.uniform(*wc.HERON_INTERVAL), None

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.timer -= dt * world.enemy_speed
        if self.state == AWAY:
            frog = world.frog_target
            if self.timer <= 0 and frog is not None:
                self.state, self.timer, self.target = SHADOW, wc.HERON_WARN, frog
                self.pos = (float(frog[0]), float(frog[1]))
                world.emit(Event("water.heron_shadow", cell=frog))
            return
        if self.timer > 0:
            return
        if self.state == SHADOW:
            self.state, self.timer = STRIKE, wc.HERON_STRIKE
            self.strikes += 1
            world.emit(Event("water.heron_strike", cell=self.target))
        elif self.state == STRIKE:
            self.state, self.timer = LEAVE, wc.HERON_LEAVE
        else:
            self.state, self.timer, self.target = AWAY, world.rng.uniform(*wc.HERON_INTERVAL), None

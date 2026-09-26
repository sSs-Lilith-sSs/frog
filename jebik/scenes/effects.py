"""Game-feel effects: particles, water rings, floating popups, banners, shake."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame as pg

from ..art.common import disc_sprite, heart_sprite, star_sprite, text_surface


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    color: tuple
    gravity: float = 0.0
    drag: float = 1.5
    kind: str = "dot"           # dot | star | heart
    age: float = 0.0
    spin: float = 0.0


@dataclass
class Ring:
    x: float
    y: float
    r0: float
    r1: float
    life: float
    color: tuple
    width: int = 3
    squash: float = 0.5
    age: float = 0.0


@dataclass
class Popup:
    img: pg.Surface
    x: float
    y: float
    life: float = 1.1
    rise: float = 60.0
    age: float = 0.0
    icon: pg.Surface | None = None


@dataclass
class Banner:
    text: str
    sub: str
    color: tuple
    outline: tuple
    life: float = 2.2
    age: float = 0.0
    size: int = 130


@dataclass
class Effects:
    particles: list[Particle] = field(default_factory=list)
    rings: list[Ring] = field(default_factory=list)
    popups: list[Popup] = field(default_factory=list)
    banners: list[Banner] = field(default_factory=list)
    shake_amount: float = 0.0
    rng: random.Random = field(default_factory=random.Random)

    # ------------------------------------------------------------ spawners
    def burst(self, x: float, y: float, color: tuple, n: int = 12, speed: float = 220,
              size: float = 5, life: float = 0.6, gravity: float = 0, kind: str = "dot",
              up: float = 0.0) -> None:
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(0.35, 1.0) * speed
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp - up,
                                           life * self.rng.uniform(0.7, 1.2),
                                           size * self.rng.uniform(0.6, 1.2), color, gravity,
                                           kind=kind, spin=self.rng.uniform(-6, 6)))

    def splash(self, x: float, y: float, k: float) -> None:
        for col in ((230, 248, 255), (170, 225, 245)):
            self.burst(x, y, col, n=14, speed=260 * k, size=5 * k, life=0.7, gravity=900 * k, up=260 * k)
        for i in range(3):
            self.rings.append(Ring(x, y, 8 * k, (40 + i * 22) * k, 0.7 + i * 0.15, (220, 245, 255), 3))

    def ring(self, x: float, y: float, r0: float, r1: float, life: float = 0.6,
             color: tuple = (200, 238, 245), width: int = 2, squash: float = 0.5) -> None:
        self.rings.append(Ring(x, y, r0, r1, life, color, width, squash))

    def popup(self, text: str, x: float, y: float, color: tuple = (255, 255, 255),
              size: int = 40, outline: tuple = (40, 70, 40), icon: pg.Surface | None = None,
              life: float = 1.1) -> None:
        img = text_surface(text, size, color, True, outline, max(2, size // 11))
        self.popups.append(Popup(img, x, y, life=life, icon=icon))

    def banner(self, text: str, sub: str = "", color: tuple = (255, 225, 110),
               outline: tuple = (120, 60, 20), life: float = 2.2, size: int = 130) -> None:
        self.banners = [Banner(text, sub, color, outline, life, size=size)]

    def shake(self, amount: float) -> None:
        self.shake_amount = max(self.shake_amount, amount)

    def shake_offset(self) -> tuple[int, int]:
        if self.shake_amount <= 0.3:
            return (0, 0)
        a = self.shake_amount
        return (round(self.rng.uniform(-a, a)), round(self.rng.uniform(-a, a)))

    # ------------------------------------------------------------ update/draw
    def update(self, dt: float) -> None:
        self.shake_amount = max(0.0, self.shake_amount - dt * 40)
        for p in self.particles:
            p.age += dt
            p.vy += p.gravity * dt
            f = max(0.0, 1 - p.drag * dt)
            p.vx *= f
            p.vy *= f if p.gravity == 0 else 1
            p.x += p.vx * dt
            p.y += p.vy * dt
        self.particles = [p for p in self.particles if p.age < p.life]
        for r in self.rings:
            r.age += dt
        self.rings = [r for r in self.rings if r.age < r.life]
        for p in self.popups:
            p.age += dt
        self.popups = [p for p in self.popups if p.age < p.life]
        for b in self.banners:
            b.age += dt
        self.banners = [b for b in self.banners if b.age < b.life]

    def draw_rings(self, surf: pg.Surface, off: tuple[int, int] = (0, 0)) -> None:
        for r in self.rings:
            t = r.age / r.life
            rad = r.r0 + (r.r1 - r.r0) * (1 - (1 - t) ** 2)
            w, h = max(2, int(rad * 2)), max(2, int(rad * 2 * r.squash))
            tmp = pg.Surface((w + 4, h + 4), pg.SRCALPHA)
            pg.draw.ellipse(tmp, (*r.color, int(220 * (1 - t))), (2, 2, w, h), r.width)
            surf.blit(tmp, (r.x - w / 2 - 2 + off[0], r.y - h / 2 - 2 + off[1]))

    def draw_particles(self, surf: pg.Surface, off: tuple[int, int] = (0, 0)) -> None:
        for p in self.particles:
            t = p.age / p.life
            alpha = int(255 * min(1.0, (1 - t) * 1.6))
            size = p.size * (1 - 0.5 * t)
            if p.kind == "dot":
                img = disc_sprite(max(1.0, round(size * 2) / 2), p.color)
            elif p.kind == "star":
                img = star_sprite(max(6, int(size * 3)))
            else:
                img = heart_sprite(max(8, int(size * 3)), p.color)
            if alpha < 255:
                img = img.copy()
                img.set_alpha(alpha)
            surf.blit(img, img.get_rect(center=(round(p.x + off[0]), round(p.y + off[1]))))

    def draw_popups(self, surf: pg.Surface) -> None:
        for p in self.popups:
            t = p.age / p.life
            pop = 1 + 0.35 * math.sin(min(1.0, t / 0.18) * math.pi) if t < 0.18 else 1.0
            img = p.img
            if pop != 1.0:
                img = pg.transform.smoothscale(img, (int(img.get_width() * pop), int(img.get_height() * pop)))
            else:
                img = img.copy()
            img.set_alpha(int(255 * min(1.0, (1 - t) * 2.5)))
            y = p.y - p.rise * (1 - (1 - t) ** 2)
            rect = img.get_rect(center=(round(p.x), round(y)))
            if p.icon is not None:
                ic = p.icon.copy()
                ic.set_alpha(img.get_alpha())
                rect.x -= ic.get_width() // 2 + 4
                surf.blit(ic, ic.get_rect(midleft=(rect.right + 6, rect.centery)))
            surf.blit(img, rect)

    def draw_banners(self, surf: pg.Surface, center: tuple[int, int]) -> None:
        for b in self.banners:
            t = b.age
            if t < 0.45:          # elastic pop in
                u = t / 0.45
                scale = 1 + math.sin(u * math.pi * 1.5) * (1 - u) * 0.6 - (1 - u) * 0.7
            else:
                scale = 1.0
            alpha = 255 if t < b.life - 0.4 else int(255 * (b.life - t) / 0.4)
            img = text_surface(b.text, b.size, b.color, True, b.outline, max(4, b.size // 16))
            if scale != 1.0:
                scale = max(0.05, scale)
                img = pg.transform.smoothscale(img, (max(1, int(img.get_width() * scale)),
                                                     max(1, int(img.get_height() * scale))))
            else:
                img = img.copy()
            img.set_alpha(max(0, alpha))
            surf.blit(img, img.get_rect(center=center))
            if b.sub:
                sub = text_surface(b.sub, 40, (255, 255, 255), True, b.outline, 4).copy()
                sub.set_alpha(max(0, min(alpha, int(255 * min(1.0, (t - 0.25) / 0.3))) if t > 0.25 else 0))
                surf.blit(sub, sub.get_rect(center=(center[0], center[1] + b.size * 0.62)))

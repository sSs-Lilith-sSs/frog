"""Meadow around the field: fences, bushes, mushrooms, flowers — ported from the mockup."""
from __future__ import annotations

import math
import random

import numpy as np
import pygame as pg

from .... import config
from ....art.common import lerp
from .paint import alpha_circle, alpha_ellipse, vnoise

W, H = config.SCREEN_W, config.SCREEN_H
HB = config.HUD_H


def daisy(S, x, y, r, q, kind="daisy"):
    petal, mid, n = {"daisy": ((252, 252, 246), (255, 205, 60), 10), "poppy": ((235, 70, 60), (60, 30, 30), 5),
                     "corn": ((110, 150, 240), (60, 70, 160), 8), "dand": ((255, 215, 50), (240, 170, 30), 12),
                     "pink": ((250, 185, 215), (255, 225, 110), 6)}[kind]
    for i in range(n):
        a = i * 2 * math.pi / n
        pr = r * (.55 if kind != "poppy" else .7)
        pg.draw.circle(S, petal, ((x + math.cos(a) * r * .75) * q, (y + math.sin(a) * r * .75) * q), pr * q)
    pg.draw.circle(S, mid, (x * q, y * q), r * .45 * q)


def mushroom(S, x, y, r, q, red=True):
    alpha_ellipse(S, (30, 50, 20, 90), ((x - r * .9 + r * .25) * q, (y - r * .5 + r * .5) * q, r * 2 * q, r * 1.6 * q))
    cap = (215, 55, 50) if red else (170, 110, 60)
    light = (240, 100, 90) if red else (205, 150, 95)
    pg.draw.circle(S, cap, (x * q, y * q), r * q)
    pg.draw.circle(S, light, ((x - r * .25) * q, (y - r * .25) * q), r * .6 * q)
    if red:
        rnd = random.Random(int(x * 7 + y))
        for _ in range(5):
            a = rnd.uniform(0, 6.28)
            rr = rnd.uniform(.15, .7) * r
            pg.draw.circle(S, (255, 250, 240), ((x + math.cos(a) * rr) * q, (y + math.sin(a) * rr) * q),
                           rnd.uniform(.12, .2) * r * q)
    else:
        pg.draw.circle(S, (230, 190, 130), ((x - r * .3) * q, (y - r * .3) * q), r * .22 * q)


def stone(S, x, y, r, q):
    alpha_ellipse(S, (30, 50, 20, 90), ((x - r + r * .25) * q, (y - r * .75 + r * .35) * q, 2 * r * q, 1.6 * r * q))
    pg.draw.ellipse(S, (140, 142, 134), ((x - r) * q, (y - r * .8) * q, 2 * r * q, 1.6 * r * q))
    pg.draw.ellipse(S, (180, 182, 172), ((x - r * .75) * q, (y - r * .7) * q, 1.3 * r * q, 1 * r * q))
    pg.draw.ellipse(S, (215, 216, 208), ((x - r * .5) * q, (y - r * .55) * q, .5 * r * q, .35 * r * q))


def bush(S, x, y, r, q, rnd):
    alpha_circle(S, (30, 50, 20, 90), ((x + r * .2) * q, (y + r * .35) * q), r * 1.05 * q)
    blobs = [(rnd.uniform(-.5, .5) * r, rnd.uniform(-.5, .5) * r, rnd.uniform(.45, .65) * r) for _ in range(7)]
    for dx, dy, rr in blobs:
        pg.draw.circle(S, (60, 125, 55), ((x + dx) * q, (y + dy) * q), rr * q)
    for dx, dy, rr in blobs:
        pg.draw.circle(S, (85, 155, 70), ((x + dx - rr * .2) * q, (y + dy - rr * .2) * q), rr * .7 * q)
    for dx, dy, rr in blobs[:4]:
        pg.draw.circle(S, (125, 190, 95), ((x + dx - rr * .35) * q, (y + dy - rr * .35) * q), rr * .3 * q)
    for _ in range(5):
        a, rr = rnd.uniform(0, 6.28), rnd.uniform(.2, .7) * r
        pg.draw.circle(S, (215, 50, 70), ((x + math.cos(a) * rr) * q, (y + math.sin(a) * rr) * q), r * .09 * q)


def tuft(S, x, y, h, q, rnd):
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * .28 + rnd.uniform(-.1, .1)
        ln = h * rnd.uniform(.6, 1)
        pg.draw.line(S, (70, 140, 60) if i % 2 else (100, 170, 75), (x * q, y * q),
                     ((x + math.cos(a) * ln) * q, (y + math.sin(a) * ln) * q), max(1, int(2.5 * q)))


def molehill(S, x, y, r, q):
    pg.draw.ellipse(S, (105, 75, 48), ((x - r) * q, (y - r * .7 + 3) * q, 2 * r * q, 1.5 * r * q))
    pg.draw.ellipse(S, (150, 110, 70), ((x - r) * q, (y - r * .75) * q, 2 * r * q, 1.5 * r * q))
    pg.draw.ellipse(S, (185, 140, 95), ((x - r * .6) * q, (y - r * .6) * q, 1 * r * q, .6 * r * q))


def fence_col(S, x, y0, y1, q, gap=None):
    """Vertical rail fence seen from above: posts + two planks."""
    ys = list(range(int(y0), int(y1), 96))
    for a, b in zip(ys, ys[1:]):
        if gap and gap[0] <= a < gap[1]:
            continue
        for dx in (-6, 6):
            pg.draw.rect(S, (90, 60, 35), ((x + dx - 3 + 3) * q, (a + 4) * q, 7 * q, (b - a) * q), border_radius=3 * q)
            pg.draw.rect(S, (190, 145, 95), ((x + dx - 3) * q, a * q, 6 * q, (b - a) * q), border_radius=3 * q)
    for i, a in enumerate(ys):
        if gap and gap[0] < a < gap[1]:
            continue
        pg.draw.rect(S, (70, 45, 28), ((x - 10 + 3) * q, (a - 10 + 5) * q, 20 * q, 20 * q), border_radius=5 * q)
        pg.draw.rect(S, (150, 105, 65), ((x - 10) * q, (a - 10) * q, 20 * q, 20 * q), border_radius=5 * q)
        pg.draw.circle(S, (185, 140, 95), (x * q, a * q), 6 * q)
        pg.draw.circle(S, (150, 105, 65), (x * q, a * q), 3 * q, max(1, q))


def meadow_backdrop(field: pg.Rect, seed=21):
    q = 2
    rnd = random.Random(seed)
    S = pg.Surface((W * q, H * q))
    for y in range(H):
        pg.draw.rect(S, lerp((168, 212, 112), (126, 186, 88), y / H), (0, y * q, W * q, q))
    # soft darker/lighter meadow patches + mowing stripes
    arr = pg.surfarray.pixels3d(S)
    n1 = vnoise(W * q, H * q, (14, 8), seed)
    n2 = vnoise(W * q, H * q, (60, 34), seed + 1)
    xs = np.arange(W * q, dtype=np.float32)[:, None]
    ys = np.arange(H * q, dtype=np.float32)[None, :]
    stripes = (np.sin((xs + ys * .6) / (70 * q)) > 0).astype(np.float32)
    f = (0.9 + 0.16 * n1 + 0.06 * n2 + 0.03 * stripes)[..., None]
    arr[...] = np.clip(arr.astype(np.float32) * f, 0, 255).astype(np.uint8)
    del arr
    frame = field.inflate(24, 24)
    placed = []

    def free(x, y, r):
        if y - r < HB + 4:
            return False
        if frame.inflate(r * 2 + 10, r * 2 + 10).collidepoint(x, y):
            return False
        for (px, py, pr) in placed:
            if math.hypot(px - x, py - y) < pr + r + 6:
                return False
        return True

    left_w = frame.left
    # fences
    fx_l = max(34, left_w * .2)
    fx_r = min(W - 34, W - (W - frame.right) * .2)
    for fx in (fx_l, fx_r):
        placed.append((fx, 600, 0))
    # dirt path meandering in left margin area
    for side, fx in ((0, fx_l), (1, fx_r)):
        fence_col(S, fx, HB + 30, H + 96, q, gap=(560, 760) if side == 0 else (300, 480))
        for yy in range(HB + 20, H, 8):
            placed.append((fx, yy, 14))
    # decor
    kinds = ["bush"] * 8 + ["stone"] * 10 + ["mush"] * 12 + ["flower"] * 75 + ["tuft"] * 45 + ["hill"] * 4
    rnd.shuffle(kinds)
    tries = 0
    while kinds and tries < 20000:
        tries += 1
        kind = kinds[-1]
        r = {"bush": 40, "stone": 16, "mush": 16, "flower": 14, "tuft": 12, "hill": 22}[kind]
        side = rnd.random()
        if side < .42:
            x = rnd.uniform(12, frame.left - 8)
        elif side < .84:
            x = rnd.uniform(frame.right + 8, W - 12)
        else:
            x = rnd.uniform(frame.left, frame.right)
        y = rnd.uniform(HB + 12, H - 6)
        if not free(x, y, r):
            continue
        kinds.pop()
        placed.append((x, y, r))
        if kind == "bush":
            bush(S, x, y, rnd.uniform(28, 40), q, rnd)
        elif kind == "stone":
            stone(S, x, y, rnd.uniform(10, 18), q)
        elif kind == "mush":
            red = rnd.random() < .6
            mushroom(S, x, y, rnd.uniform(8, 12), q, red)
            if rnd.random() < .6:
                mushroom(S, x + rnd.uniform(10, 16), y + rnd.uniform(4, 10), rnd.uniform(5, 7), q, red)
        elif kind == "flower":
            k2 = rnd.choice(("daisy", "daisy", "poppy", "corn", "dand", "pink"))
            for _ in range(rnd.randint(1, 3)):
                daisy(S, x + rnd.uniform(-12, 12), y + rnd.uniform(-12, 12), rnd.uniform(7, 10), q, k2)
        elif kind == "tuft":
            tuft(S, x, y + 8, rnd.uniform(16, 26), q, rnd)
        else:
            molehill(S, x, y, rnd.uniform(16, 22), q)
    # field frame: dark soil border with shadow
    pg.draw.rect(S, (60, 42, 26), (frame.x * q, (frame.y + 7) * q, frame.w * q, frame.h * q), border_radius=20 * q)
    pg.draw.rect(S, (112, 80, 52), (frame.x * q, frame.y * q, frame.w * q, frame.h * q), border_radius=20 * q)
    pg.draw.rect(S, (140, 104, 70), ((frame.x + 3) * q, (frame.y + 3) * q, (frame.w - 6) * q, (frame.h - 6) * q),
                 2 * q, border_radius=18 * q)
    return pg.transform.smoothscale(S, (W, H))

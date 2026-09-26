"""The friendly chibi «Ісус», his big cloud and halo (ported from the mockup)."""
from __future__ import annotations

import math

import pygame as pg

from .paint import CLOUD_SH, GOLD, GOLD_D, GOLD_L, PAL_B, T, glow

SKIN, SKIN_D = (252, 216, 182), (235, 185, 150)
HAIR, HAIR_D, HAIR_L = (120, 78, 48), (90, 56, 34), (150, 102, 64)
ROBE, ROBE_S, ROBE_D = (253, 251, 245), (232, 226, 240), (200, 190, 215)
SASH, SASH_D, SASH_L = (80, 135, 220), (55, 100, 185), (130, 175, 240)
INK = (70, 42, 30)

ARMS = {
    "open": ((-1, (-16, -60), (-50, -80), (-58, -86)), (1, (16, -60), (50, -80), (58, -86))),
    "up": ((-1, (-16, -60), (-40, -96), (-44, -104)), (1, (16, -60), (40, -96), (44, -104))),
    "down": ((-1, (-16, -58), (-30, -26), (-32, -18)), (1, (16, -58), (30, -26), (32, -18))),
    "point": ((-1, (-16, -60), (-30, -30), (-32, -23)), (1, (16, -60), (50, -84), (57, -90))),
}
HEAD_Y = -88          # head centre above the robe/cloud line (units)
HALO_Y = HEAD_Y - 33


def halo_flat(s, x, y, u, dim=False, tilt=0.0) -> None:
    rx, ry = 22 * u, 7.5 * u
    lay = pg.Surface((int(rx * 2 + 12 * u), int(rx * 2 + 12 * u)), pg.SRCALPHA)
    c = lay.get_width() / 2
    g, gl, gd = (GOLD, GOLD_L, GOLD_D) if not dim else ((205, 185, 140), (230, 215, 180), (170, 150, 110))
    pg.draw.ellipse(lay, gd, (c - rx, c - ry + 1.5 * u, rx * 2, ry * 2), int(4.5 * u))
    pg.draw.ellipse(lay, g, (c - rx, c - ry, rx * 2, ry * 2), int(4.5 * u))
    pg.draw.arc(lay, gl, (c - rx + 1.2 * u, c - ry + 1 * u, rx * 2 - 2.4 * u, ry * 2 - 2 * u),
                math.radians(20), math.radians(160), max(1, int(1.8 * u)))
    if tilt:
        lay = pg.transform.rotate(lay, tilt)
    s.blit(lay, lay.get_rect(center=(x, y)))


def halo_ring(s, x, y, u) -> None:
    """Halo seen flying (boomerang): a more open ellipse."""
    rx, ry = 20 * u, 13 * u
    lay = pg.Surface((int(rx * 2 + 12 * u), int(rx * 2 + 12 * u)), pg.SRCALPHA)
    c = lay.get_width() / 2
    pg.draw.ellipse(lay, GOLD_D, (c - rx, c - ry + 1.5 * u, rx * 2, ry * 2), int(5 * u))
    pg.draw.ellipse(lay, GOLD, (c - rx, c - ry, rx * 2, ry * 2), int(5 * u))
    pg.draw.arc(lay, GOLD_L, (c - rx + 1.4 * u, c - ry + 1.2 * u, rx * 2 - 2.8 * u, ry * 2 - 2.4 * u),
                math.radians(30), math.radians(150), max(1, int(2 * u)))
    s.blit(lay, lay.get_rect(center=(x, y)))


def boss_cloud(s, cx, cy, u, pal=PAL_B) -> None:
    top, mid, shade, rim = pal
    puffs = [(-62, 4, 20), (-38, -6, 26), (-10, -12, 30), (22, -10, 28), (48, -4, 24), (68, 6, 17),
             (-78, 10, 13), (0, 8, 30)]

    def body(col, dx, dy, k):
        pg.draw.rect(s, col, (cx - 84 * u + dx, cy - 2 * u + dy, 168 * u, 26 * u), border_radius=int(13 * u))
        for x, y, r in puffs:
            pg.draw.circle(s, col, (cx + x * u + dx, cy + y * u + dy), r * u * k)
    body(CLOUD_SH, 4 * u, 8 * u, 1)
    body(shade, 0, 4 * u, 1)
    body(mid, 0, 0, 1)
    body(top, -2.5 * u, -4 * u, .8)
    for x, y, r in puffs[:6]:
        pg.draw.circle(s, rim, (cx + x * u - r * u * .3, cy + y * u - r * u * .45), r * u * .2)


def _sleeve(t: T, sx, sh, wr, hand) -> None:
    dx, dy = wr[0] - sh[0], wr[1] - sh[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    w0, w1 = 7.5, 10.5
    pts = [(sh[0] + nx * w0, sh[1] + ny * w0), (wr[0] + nx * w1, wr[1] + ny * w1),
           (wr[0] - nx * w1, wr[1] - ny * w1), (sh[0] - nx * w0, sh[1] - ny * w0)]
    t.poly(ROBE_D, [(x + .8, y + 2) for x, y in pts])
    t.poly(ROBE, pts)
    t.line(ROBE_S, (sh[0] - nx * 2 + dx * .3, sh[1] - ny * 2 + dy * .3), (wr[0] - nx * 5, wr[1] - ny * 5), 1.6)
    t.ell(ROBE_S, wr[0], wr[1], 5.5, 9.5, rot=math.atan2(dy, dx))
    hx, hy = hand
    t.circ(SKIN_D, hx + .6, hy + 1, 6.4)
    t.circ(SKIN, hx, hy, 6.2)
    t.ell(SKIN, hx - sx * 5, hy + 1.5, 2.4, 3.6, rot=sx * .6)
    t.ell(SKIN_D, hx + sx * .5, hy + 1, 3, 3.2)
    t.ell(SKIN, hx + sx * .8, hy - .2, 2.8, 3)


def _face(s, t: T, u, face: str) -> None:
    hy = HEAD_Y
    ey = hy + 1
    lw = 1.7
    if face in ("smile", "wink", "surprised", "sad"):
        for sx in (-1, 1):
            if face == "wink" and sx > 0:
                pg.draw.arc(s, INK, (*t.p(sx * 8 - 4, ey - 3), 8 * u, 6 * u), math.radians(20),
                            math.radians(160), max(1, int(lw * u)))
                continue
            t.ell(INK, sx * 8, ey, 3.4, 4.6 if face != "surprised" else 5.2)
            t.circ((255, 255, 255), sx * 8 + 1.1, ey - 1.8, 1.3)
            t.circ((255, 255, 255), sx * 8 - 1, ey + 1.8, .6)
    if face == "happy":
        for sx in (-1, 1):
            x0, y0 = t.p(sx * 8 - 4.5, ey - 3)
            pg.draw.arc(s, INK, (x0, y0, 9 * u, 8 * u), math.radians(15), math.radians(165), max(1, int(2 * u)))
    if face == "ouch":
        for sx in (-1, 1):
            pts = [t.p(sx * 8 - 3.5 * sx, ey - 3), t.p(sx * 8 + 3 * sx, ey), t.p(sx * 8 - 3.5 * sx, ey + 3)]
            pg.draw.lines(s, INK, False, pts, max(1, int(2 * u)))
    if face == "sad":
        for sx in (-1, 1):
            t.line(HAIR_D, (sx * 4, ey - 8.5), (sx * 12, ey - 6), 1.8)
            t.poly(SKIN, [(sx * 4.2, ey - 5), (sx * 12, ey - 5), (sx * 12, ey - 1.5), (sx * 4.2, ey - 3.6)])
        t.poly((140, 200, 250), [(-11, ey + 3), (-13, ey + 8), (-11, ey + 10), (-9, ey + 8)])   # the tear
        t.circ((140, 200, 250), -11, ey + 8.4, 2)
        t.circ((230, 245, 255), -11.6, ey + 7.6, .7)
    elif face in ("smile", "happy", "wink", "surprised"):
        lift = 12.5 if face == "surprised" else 10.5
        for sx in (-1, 1):
            x0, y0 = t.p(sx * 8 - 4, ey - lift)
            pg.draw.arc(s, HAIR_D, (x0, y0, 8 * u, 5 * u), math.radians(30), math.radians(150), max(1, int(1.4 * u)))
    for sx in (-1, 1):
        t.ell((255, 165, 170), sx * 12.5, ey + 5.5, 3.4, 2.2)
    t.ell(SKIN_D, 0, ey + 5, 1.6, 1.2)
    my = hy + 15.5
    if face in ("smile", "happy", "wink"):
        t.poly((140, 55, 60), [(-5.5, my - 1.5), (5.5, my - 1.5), (4, my + 2.5), (0, my + 4), (-4, my + 2.5)])
        t.ell((240, 125, 135), 0, my + 2.2, 2.8, 1.3)
        t.poly((255, 255, 255), [(-4.5, my - 1.4), (4.5, my - 1.4), (4, my - .2), (-4, my - .2)])
    elif face == "sad":
        x0, y0 = t.p(-4.5, my - .5)
        pg.draw.arc(s, (240, 150, 155), (x0, y0 + 1.2 * u, 9 * u, 6 * u), math.radians(25), math.radians(155),
                    max(1, int(2.4 * u)))
    elif face == "surprised":
        t.ell((140, 55, 60), 0, my + 1, 2.6, 3.2)
    elif face == "ouch":
        pts = [t.p(-5, my + 1), t.p(-2.5, my - 1), t.p(0, my + 1), t.p(2.5, my - 1), t.p(5, my + 1)]
        pg.draw.lines(s, (130, 50, 55), False, pts, max(1, int(1.6 * u)))


def draw_jesus(s, cx, cy, u, arms="open", face="smile") -> list[tuple[float, float]]:
    """Friendly chibi, no halo / cloud. (cx, cy) = where the robe meets the
    cloud; height ≈ 115u. Returns the palm positions."""
    t = T(s, cx, cy, u)
    cfg = ARMS[arms]
    behind = arms in ("open", "up", "point")
    hy = HEAD_Y
    t.ell(HAIR_D, 0, hy + 6, 27, 29)
    for sx in (-1, 1):
        t.ell(HAIR_D, sx * 17, hy + 24, 8, 13, rot=sx * .3)
    if behind:
        for arm in cfg:
            _sleeve(t, *arm)
    robe = [(-18, -64), (18, -64), (26, -40), (33, -8), (35, 4), (-35, 4), (-33, -8), (-26, -40)]
    t.poly(ROBE_D, [(x + 1.5, y + 2) for x, y in robe])
    t.poly(ROBE, robe)
    t.poly(ROBE_S, [(10, -60), (18, -64), (26, -40), (33, -8), (35, 4), (20, 4), (22, -30)])
    for x0 in (-12, 4):
        t.line(ROBE_S, (x0, -30), (x0 - 3, 2), 1.4)
    sash = [(-18, -64), (-9, -64), (30, -18), (33, -8), (25, -6)]
    t.poly(SASH_D, [(x, y + 1.6) for x, y in sash])
    t.poly(SASH, sash)
    t.line(SASH_L, (-14, -62), (26, -14), 1.3)
    t.poly(SASH_D, [(26, -10), (34, 4), (29, 6), (22, -6)])
    if not behind:
        for arm in cfg:
            _sleeve(t, *arm)
    t.ell(HAIR, 0, hy + 3, 25.5, 26)
    for sx in (-1, 1):
        t.ell(HAIR, sx * 19.5, hy + 14, 6, 12, rot=sx * .18)
        t.ell(HAIR_L, sx * 20.5, hy + 11, 1.6, 6.5, rot=sx * .18)
    t.ell(SKIN, 0, hy + 3, 20.5, 21.5)
    for sx in (-1, 1):
        t.poly(HAIR, [(sx * 23, hy + 4), (sx * 22, hy - 10), (sx * 13, hy - 20), (sx * 1, hy - 21), (sx * 3, hy - 15),
                      (sx * 9, hy - 11), (sx * 16, hy - 7), (sx * 19, hy - 1)])
    t.ell(HAIR, 0, hy - 16, 17, 7)
    t.ell(HAIR_L, -9, hy - 18, 5, 1.8, rot=-.25)
    t.ell(HAIR_L, 10, hy - 17, 3.5, 1.4, rot=.3)
    beard = [(-19, hy + 4), (-17, hy + 15), (-10, hy + 23), (0, hy + 26), (10, hy + 23), (17, hy + 15),
             (19, hy + 4), (15, hy + 9), (9, hy + 14), (0, hy + 15.5), (-9, hy + 14), (-15, hy + 9)]
    t.poly(HAIR, beard)
    t.ell(HAIR_L, -8, hy + 20, 3, 1.6, rot=.4)
    t.ell(HAIR_L, 7, hy + 21, 2.4, 1.3, rot=-.4)
    for sx in (-1, 1):
        t.ell(HAIR, sx * 4.8, hy + 11, 5.6, 2.4, rot=-sx * .3)
    _face(s, t, u, face)
    return [t.p(*arm[3]) for arm in cfg]


def palm_rays(s, px, py, u, t: float, strength: float = 1.0) -> None:
    glow(s, px, py, 34 * u * (0.8 + .4 * strength), (255, 240, 150), int(150 + 80 * strength))
    for a in range(0, 360, 45):
        r = math.radians(a + 22 + t * 40)
        pg.draw.line(s, (255, 245, 190), (px + 14 * u * math.cos(r), py + 14 * u * math.sin(r)),
                     (px + (20 + 4 * strength) * u * math.cos(r), py + (20 + 4 * strength) * u * math.sin(r)),
                     max(1, int(2.5 * u)))

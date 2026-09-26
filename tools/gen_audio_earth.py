#!/usr/bin/env python3
"""Earth-world sounds -> jebik/worlds/earth/audio/<name>.wav (played as "earth.<name>").

Original, soft cartoon sounds (numpy synthesis via ``tools/synth.py``):
hedgehog roll / bump / fall, fox leap / landing, mole tremor / pop,
crumbling ground, and the boar: snort (tell), charge, stomp, crash,
stump break / regrowth and its «oink!» when it is hit.

    python3 tools/gen_audio_earth.py [out_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth as S  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "jebik" / "worlds" / "earth" / "audio"


def thump(f0: float = 150, f1: float = 60, d: float = .16, decay: float = .05) -> np.ndarray:
    """Soft round body thud (upper partials keep it audible on small speakers)."""
    return S.tone(S.glide(f0, f1, d, 1.5), (1, .5, .25, .1)) * S.perc(d, .003, decay)


def dirt(r, d: float, cutoff: float = 1600, decay: float = .06) -> np.ndarray:
    """A puff of soil: dark filtered noise with a short tail."""
    return S.lowpass(S.noise(r, d), cutoff, .6) * S.perc(d, .003, decay)


def hedgehog_roll(r):
    """Curl-up squeak, then a bumpy rolling 'brrrr' that speeds up."""
    d = .9
    squeak = S.tone(S.glide(1100, 1500, .07), (1, .2)) * S.perc(.07, .004, .03)
    t = S.tt(.75)
    bumps = .55 + .45 * np.sin(2 * np.pi * (14 * t + 10 * t * t)) ** 2
    roll = S.lowpass(S.pink(r, .75), 700 + 800 * t, .8) * bumps * S.swell(.75, .35, .8)
    spines = S.bandpass(S.noise(r, .75), 1100, 2.0) * bumps ** 3 * S.swell(.75, .35, 1.0)
    rumble = S.tone(S.glide(110, 150, .75), (1, .6, .35, .15)) * bumps * S.swell(.75, .35, 1.0)
    return S.mix(d, (0, squeak, .45), (.08, roll, 1), (.08, spines, .5), (.08, rumble, .3))


def bump(r):
    """Rolled into something: soft thud + small boing."""
    return S.mix(.4, (0, thump(190, 90, .14), 1), (.02, S.boing(360, 220, .25, 16, .9), .4))


def fall(r):
    """Tumbling into a pit: slide-whistle down, then a soft 'plomp'."""
    whistle = S.tone(S.glide(950, 280, .5, .8), (1, .12), vib=.3, vib_rate=7) * S.env(S.n_of(.5), .02, .3, .2, .06)
    out = S.mix(.85, (0, whistle, .55), (.5, thump(160, 70, .2, .07), 1), (.5, dirt(r, .2, 1200), .35))
    return S.room(out, r, .15, .12)


def fox_leap(r):
    """Swish up + a tiny 'yip'."""
    yip = S.tone(np.concatenate([S.glide(800, 1250, .05), S.glide(1250, 950, .07)]), (1, .45, .25, .1))
    yip = S.lowpass(yip * S.env(len(yip), .005, .05, 0, .02), 3200)
    return S.mix(.4, (0, S.whoosh(r, .3, 600, 2200, .9, .55), .6), (.03, yip, .55))


def fox_land(r):
    """Light paws on grass."""
    return S.mix(.22, (0, thump(230, 120, .1, .03), .9), (0, dirt(r, .12, 2200, .03), .45),
                 (.05, thump(210, 110, .08, .025), .5))


def mole_tremor(r):
    """The ground shivers under the frog: a low wobbling rumble."""
    d = .85
    t = S.tt(d)
    shake = .6 + .4 * np.sin(2 * np.pi * 13 * t)
    rumble = S.lowpass(S.pink(r, d), 260, .8) * shake * S.swell(d, .75, .8)
    rattle = S.stack(S.bandpass(S.noise(r, d), 480, 1.4), (S.bandpass(S.noise(r, d), 850, 1.6), .7))
    rattle *= (.5 + .5 * np.sin(2 * np.pi * 17 * t)) * S.swell(d, .75, 1.0)
    low = S.tone(S.const(62, d), (1, .7, .5, .3)) * shake * S.swell(d, .8, 1.0)
    return S.mix(d, (0, rumble, .7), (0, rattle, .9), (0, low, .3))


def mole_pop(r):
    """Out he pops: 'pomp!' + flying soil crumbs + a little squeak."""
    pomp = S.tone(S.glide(240, 520, .14, .8), (1, .3, .1)) * S.perc(.14, .003, .06)
    out = S.mix(.55, (0, pomp, 1), (0, dirt(r, .25, 1800, .07), .5), (.02, thump(130, 60, .14), .6))
    for k in range(5):
        S.add(out, .08 + k * .05 + r.uniform(0, .03), S.wood(r.uniform(1400, 2400), .03, .008), .12)
    squeak = S.tone(S.glide(1400, 1700, .06), (1, .2)) * S.perc(.06, .004, .02)
    S.add(out, .2, squeak, .25)
    return S.room(out, r, .12, .1)


def crumble(r):
    """A patch of ground falls in: grains + a soft low thud."""
    out = S.silence(.55)
    for k in range(9):
        S.add(out, r.uniform(0, .3), dirt(r, .08, r.uniform(1200, 2600), .02), r.uniform(.4, .7))
    S.add(out, .12, thump(160, 70, .22, .07), .45)
    return S.room(out, r, .1, .1)


def crumble_warn(r):
    """Ground starts to crack: faint crackles."""
    out = S.silence(.45)
    for k in range(7):
        S.add(out, k * .055 + r.uniform(0, .02), S.wood(r.uniform(900, 1700), .04, .01), r.uniform(.3, .6))
    S.add(out, 0, dirt(r, .4, 1300, .15), .25)
    return S.lowpass(out, 3000)


def boar_snort(r):
    """'hmf-HMF!' snort + a grumbly grunt (the boar gets ready)."""
    out = S.silence(.75)
    for k, (st, v) in enumerate(((0, .6), (.17, 1.0))):
        puff = S.bandpass(S.noise(r, .13), S.glide(950, 600, .13), 1.5) * S.env(S.n_of(.13), .01, .05, 0, .03)
        S.add(out, st, puff, v)
    t = S.tt(.4)
    grunt = S.tone(S.glide(150, 115, .4), (1, .8, .6, .45, .3, .15)) * (.7 + .3 * np.sin(2 * np.pi * 26 * t))
    S.add(out, .3, S.lowpass(grunt * S.env(len(t), .02, .15, .3, .08), 1100), .8)
    return out


def charge(r):
    """Galloping hooves + rumble."""
    d = 1.0
    out = S.silence(d + .1)
    k = 0
    st = 0.0
    while st < d - .1:
        v = .8 if k % 2 == 0 else .55
        S.add(out, st, thump(150, 75, .09, .025), v * .6)
        S.add(out, st, S.wood(r.uniform(430, 520), .06, .018), v * .9)        # clip-clop
        S.add(out, st, dirt(r, .05, 1500, .015), .15)
        st += .11 if k % 2 == 0 else .07
        k += 1
    rumble = S.lowpass(S.pink(r, d), 200, .7) * S.swell(d, .3, 1.0)
    S.add(out, 0, rumble, .5)
    return S.soft_clip(out, 2.2)


def stomp(r):
    """Heavy STOMP: deep thud, soil burst, trembling tail."""
    boom = S.tone(S.glide(105, 38, .55, 1.4), (1, .6, .35, .2, .1)) * S.perc(.55, .004, .16)
    whump = S.tone(S.glide(240, 95, .25, 1.4), (1, .4, .15)) * S.perc(.25, .003, .07)
    t = S.tt(.7)
    tail = S.lowpass(S.pink(r, .7), 300, .7) * S.env(len(t), .01, .25, 0, .1) * (.7 + .3 * np.sin(2 * np.pi * 11 * t))
    rattle = S.bandpass(S.noise(r, .7), 600, 1.3) * S.env(len(t), .01, .2, 0, .1)
    rattle *= .6 + .4 * np.sin(2 * np.pi * 15 * t)
    out = S.mix(1.0, (0, boom, .45), (0, whump, 1), (0, dirt(r, .35, 1400, .08), .8), (.02, tail, .5),
                (.03, rattle, .6))
    return S.room(out, r, .18, .2)


def crash(r):
    """Boar bonks into the edge / a stump: BONK + boing + dizzy tweets."""
    bonk = S.stack(S.wood(300, .16, .06), (thump(110, 45, .25, .08), .9))
    out = S.mix(1.2, (0, bonk, 1), (.03, S.boing(380, 190, .4, 13, 1.2), .45))
    for k, m in enumerate((91, 94, 91, 94)):
        S.add(out, .42 + k * .14, S.bell(S.midi(m), .18, 2.0, .5, .06), .18)
    return S.room(out, r, .15, .15)


def stump(r):
    """A stump splinters: woody cracks + chunky thud."""
    out = S.silence(.6)
    for k in range(6):
        S.add(out, k * .025 + r.uniform(0, .01), S.wood(r.uniform(550, 1300), .07, .02), r.uniform(.4, .8))
    crunch = S.bandpass(S.noise(r, .2), 1300, .9) * S.perc(.2, .002, .04)
    S.add(out, 0, crunch, .45)
    S.add(out, .03, thump(140, 60, .2, .06), .8)
    return S.room(out, r, .15, .12)


def stump_grow(r):
    """The stump pops back up: a cheerful sprouting 'bloop'."""
    sprout = S.tone(S.glide(280, 720, .22, .9), (1, .3, .1)) * S.env(S.n_of(.22), .01, .12, 0, .04)
    return S.room(S.mix(.45, (0, sprout, 1), (.16, S.sparkle(r, .2, 2, 2200, 3200, .3), 1)), r, .12, .1)


def boss_hit(r):
    """The stunned boar gets licked: a round, surprised «oink!»."""
    f = np.concatenate([S.glide(430, 620, .08), S.glide(620, 430, .2, 1.2)])
    oink = S.tone(f, (1, .8, .6, .45, .3, .2, .12)) * S.env(len(f), .01, .12, .3, .05)
    oink = S.bandpass(oink, 1100, .5) * 2 + S.lowpass(oink, 800) * .5
    out = S.mix(.7, (0, S.wood(420, .1, .03), .6), (.04, oink, .8))
    return S.room(S.soft_clip(out, 1.8), r, .15, .12)


SOUNDS = {"hedgehog_roll": hedgehog_roll, "bump": bump, "fall": fall, "fox_leap": fox_leap,
          "fox_land": fox_land, "mole_tremor": mole_tremor, "mole_pop": mole_pop, "crumble": crumble,
          "crumble_warn": crumble_warn, "boar_snort": boar_snort, "charge": charge, "stomp": stomp,
          "crash": crash, "stump": stump, "stump_grow": stump_grow, "boss_hit": boss_hit}


def main(argv: list[str]) -> int:
    S.render_all(SOUNDS, Path(argv[0]) if argv else OUT, np.random.default_rng(202))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

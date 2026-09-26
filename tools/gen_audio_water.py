#!/usr/bin/env python3
"""Water-world sounds -> jebik/worlds/water/audio/<name>.wav (played as "water.<name>").

Original, soft cartoon sounds (numpy synthesis via ``tools/synth.py``):
pike bubbles + lunge, heron wings + beak, sinking pad, and the whale:
song (surfacing warning), surfacing splash, fountain jet, wave, gulp and
the «ПИРХ!» blowhole spray when it is hit.

    python3 tools/gen_audio_water.py [out_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth as S  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "jebik" / "worlds" / "water" / "audio"


def underwater(x: np.ndarray, cutoff: float = 1800) -> np.ndarray:
    return S.lowpass(x, cutoff, .6)


def pike_bubbles(r):
    """Something is lurking: bubbles rising faster and louder (0.8 s warning)."""
    d = .85
    out = S.silence(d + .1)
    t = 0.0
    i = 0
    while t < d - .05:
        u = t / d
        S.add(out, t, S.bubble(r.uniform(260, 420) * (1 + u * .7), r.uniform(.05, .08), 1.9), .35 + .5 * u)
        t += (.13 - .08 * u) * r.uniform(.8, 1.2)
        i += 1
    return underwater(out, 2400)


def pike_lunge(r):
    """Splash out of the water + a toothy 'chomp'."""
    d = .45
    splash = S.lowpass(S.noise(r, .3), S.glide(3800, 700, .3, 1.5), .7) * S.env(S.n_of(.3), .003, .06, 0, .04)
    chomp = S.stack(S.wood(620, .09, .03), (S.tone(S.glide(900, 480, .06), (1, .3)) * S.perc(.06, .002, .02), .6))
    out = S.mix(d, (0, splash, .7), (.1, chomp, 1), (.15, S.wood(560, .07, .025), .6))
    for k in range(3):
        S.add(out, .2 + k * .06, S.bubble(r.uniform(500, 900), .05), .2)
    return S.room(out, r, .12, .08)


def heron_whoosh(r):
    """Big soft wing beats coming down (the shadow grows)."""
    d = 1.1
    out = S.silence(d)
    for k, st in enumerate((0, .36, .7)):
        S.add(out, st, S.whoosh(r, .3, 1300, 500, .8, .35), .45 + .25 * k)
    return S.lowpass(out, 2600)


def heron_strike(r):
    """Beak jab: a hollow 'tok' and a little water flick."""
    tok = S.wood(520, .1, .035)
    flick = S.lowpass(S.noise(r, .18), S.glide(3000, 900, .18), .7) * S.perc(.18, .002, .04)
    return S.room(S.mix(.3, (0, tok, 1), (.01, flick, .35)), r, .1, .07)


def sink(r):
    """A lily pad starts to sink: slow glug-glug bubbles."""
    d = 1.2
    out = S.silence(d + .1)
    for k in range(7):
        S.add(out, .05 + k * .16 + r.uniform(0, .04), S.bubble(r.uniform(260, 420) * (1 - k * .05), .1, 1.5),
              .6 - k * .05)
    return underwater(out, 1500)


def whale_song(r):
    """Deep, friendly whale call from below (surfacing warning)."""
    f = np.concatenate([S.glide(210, 330, .55, .8), S.glide(330, 250, .85)])
    body = S.tone(f, (1, .6, .35, .15), vib=.25, vib_rate=4.5) * S.env(len(f), .18, .5, .4, .35)
    return S.room(underwater(body, 1300), r, .3, .35)


def whale_surface(r):
    """The whale breaks the surface: big whoomp + wash + falling droplets."""
    d = 1.3
    boom = S.tone(S.glide(120, 50, .6, 1.4), (1, .3)) * S.perc(.6, .006, .2)
    wash = S.lowpass(S.pink(r, 1.0), S.glide(3000, 350, 1.0, 1.3), .6) * S.env(S.n_of(1.0), .02, .3, 0, .1)
    out = S.mix(d, (0, boom, .7), (0, wash, .9))
    for k in range(9):
        S.add(out, .25 + r.uniform(0, .8), S.bubble(r.uniform(600, 1300), .05, 1.5), r.uniform(.12, .25))
    return S.room(out, r, .2, .25)


def jet(r):
    """Fountain jet: a gurgle, then a rising spray 'fsssh'."""
    d = .75
    gurgle = S.silence(.2)
    for k in range(3):
        S.add(gurgle, k * .05, S.bubble(r.uniform(250, 380), .06, 1.8), .5)
    spray = S.lowpass(S.bandpass(S.noise(r, .6), S.glide(900, 2300, .6, .7), .9), 4500) * S.swell(.6, .25, 1.2)
    rise = S.tone(S.glide(300, 620, .35), (1, .2)) * S.env(S.n_of(.35), .03, .12, 0, .05)
    return S.room(S.mix(d, (0, gurgle, .6), (.12, spray, 1), (.12, rise, .35)), r, .15, .12)


def wave(r):
    """A rolling wave: swelling 'shhhWOOSH' with a low body."""
    d = 1.3
    cut = 600 + 2300 * S.swell(d, .55, 1.4)
    body = S.lowpass(S.pink(r, d), cut, .7) * S.swell(d, .55, 1.2)
    low = S.tone(S.glide(90, 70, d), (1, .3)) * S.swell(d, .5, 1.5)
    return S.room(S.mix(d, (0, body, 1), (0, low, .2)), r, .15, .2)


def gulp(r):
    """The whale's huge slurp toward its mouth, ending in a 'GULP'."""
    d = 1.7
    t = S.tt(1.3)
    suction = S.lowpass(S.pink(r, 1.3), 500 + 500 * np.sin(2 * np.pi * 3.2 * t) ** 2, 1.2) * S.swell(1.3, .6, 1.0)
    slurp = S.tone(S.glide(420, 160, 1.3, .9), (1, .5, .3, .15), vib=.8, vib_rate=7) * S.swell(1.3, .7, 1.2)
    big = S.tone(S.glide(260, 110, .22, 1.3), (1, .4, .15)) * S.perc(.22, .004, .08)
    out = S.mix(d, (0, suction, .6), (0, S.lowpass(slurp, 1400), .5), (1.28, big, 1))
    return S.room(out, r, .15, .15)


def boss_hit(r):
    """«ПИРХ!»: a spray from the blowhole with a surprised honk."""
    d = .9
    t = S.tt(.45)
    pfff = S.bandpass(S.noise(r, .45), S.glide(2400, 1300, .45), 1.1)
    pfff *= S.env(len(t), .005, .12, 0, .05) * (.7 + .3 * np.sin(2 * np.pi * 32 * t))
    honk = S.tone(S.glide(240, 170, .35, 1.2), (1, .7, .5, .3, .15)) * S.env(S.n_of(.35), .01, .12, .3, .08)
    out = S.mix(d, (0, pfff, .8), (.05, S.lowpass(honk, 1300), .8))
    for k in range(5):
        S.add(out, .3 + k * .08, S.bubble(r.uniform(700, 1200), .05), .2)
    return S.room(out, r, .15, .12)


SOUNDS = {"pike_bubbles": pike_bubbles, "pike_lunge": pike_lunge, "heron_whoosh": heron_whoosh,
          "heron_strike": heron_strike, "sink": sink, "whale_song": whale_song,
          "whale_surface": whale_surface, "jet": jet, "wave": wave, "gulp": gulp, "boss_hit": boss_hit}


def main(argv: list[str]) -> int:
    S.render_all(SOUNDS, Path(argv[0]) if argv else OUT, np.random.default_rng(101))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

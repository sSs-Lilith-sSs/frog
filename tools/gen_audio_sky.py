#!/usr/bin/env python3
"""Sky-world sounds -> jebik/worlds/sky/audio/<name>.wav (played as "sky.<name>").

Original, soft cartoon sounds (numpy synthesis via ``tools/synth.py``):
swallow whistle + whoosh, a soft hawk cry, crow caw / peck / snack, melting
cloud, and «Ісус»: beam charge + beam, fly multiplication sparkle, halo
whirl + catch, cloud rebuild, the «SASAT!» bonk and his sad giving-up.

    python3 tools/gen_audio_sky.py [out_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth as S  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "jebik" / "worlds" / "sky" / "audio"


def chirp(f0: float, f1: float, d: float, vib: float = 0.0) -> np.ndarray:
    return S.tone(S.glide(f0, f1, d, 1.3), (1, .12), vib=vib, vib_rate=28) * S.env(S.n_of(d), .006, d * .5, 0, .02)


def whistle(r):
    """Swallow incoming: two bright little 'tsweet!' chirps."""
    out = S.silence(.5)
    S.add(out, 0, chirp(2100, 2900, .09, .3), .8)
    S.add(out, .14, chirp(2300, 3200, .12, .4), 1)
    return S.room(S.lowpass(out, 4200), r, .12, .1)


def swallow(r):
    """The swallow zips past: a quick doppler whoosh."""
    d = .5
    air = S.lowpass(S.whoosh(r, d, 900, 2600, 1.0, .45), 3500)
    buzz = S.tone(S.glide(1500, 900, d, .8), (1, .2)) * S.swell(d, .45, 2.0)
    return S.mix(d, (0, air, 1), (0, buzz, .15))


def hawk(r):
    """A soft, distant 'kee-yeer' (the hawk winds up)."""
    f = np.concatenate([S.glide(1300, 1750, .12), S.glide(1750, 1150, .38, 1.4)])
    cry = S.tone(f, (1, .35, .12), vib=.25, vib_rate=16) * S.env(len(f), .02, .25, .2, .08)
    breath = S.bandpass(S.noise(r, .5), 2200, 1.0) * S.swell(.5, .3, 1.5)
    return S.room(S.lowpass(S.stack(cry, (breath, .08)), 3600), r, .2, .18)


def caw(r):
    """Crow 'caw-caw!' — round and cartoonish, not shrill."""
    out = S.silence(.75)
    for k, (st, f0) in enumerate(((0, 640), (.27, 590))):
        t = S.tt(.2)
        f = S.glide(f0, f0 * .82, .2, 1.4)
        voice = S.tone(f, (1, .9, .7, .5, .35, .2, .1)) * (.75 + .25 * np.sin(2 * np.pi * 55 * t))
        voice = S.bandpass(voice, 1200, .7) * S.env(len(t), .012, .1, .35, .05)
        S.add(out, st, S.lowpass(voice, 2600), 1 if k == 0 else .8)
    return S.room(out, r, .15, .12)


def peck(r):
    """'tok-tok'."""
    return S.mix(.2, (0, S.wood(1150, .05, .012), 1), (.085, S.wood(1050, .05, .012), .8))


def crow_eat(r):
    """The crow snaps up a fly: a tiny 'nk'."""
    return S.mix(.16, (0, S.wood(900, .04, .01), .6), (.03, S.bubble(700, .06, .6), .8))


def melt(r):
    """A cloud starts melting: soft fizz + drips going down."""
    d = 1.0
    out = S.silence(d + .1)
    fizz = S.highpass(S.noise(r, d), 2500) * S.swell(d, .3, 1.5)
    S.add(out, 0, S.lowpass(fizz, 6000), .12)
    for k, m in enumerate((84, 81, 77, 74, 72)):
        S.add(out, .05 + k * .16, S.bell(S.midi(m), .3, 1.0, .3, .12), .35)
    for k in range(3):
        S.add(out, .3 + k * .22, S.bubble(r.uniform(900, 1200), .05, .6), .2)
    return S.room(out, r, .18, .15)


def pad(freqs, d: float, attack: float = .3) -> np.ndarray:
    """Soft choir-like pad: detuned sines with slow attack."""
    out = np.zeros(S.n_of(d))
    for f in freqs:
        for det in (-.004, .004):
            out += S.tone(S.const(f * (1 + det), d), (1, .25, .08), vib=.08, vib_rate=5)
    return out * S.env(len(out), attack, 10, 1, .12) / (2 * len(freqs))


def beam_charge(r):
    """Palms light up: a rising heavenly 'aaah' (beam warning)."""
    d = 1.0
    body = pad([S.midi(m) for m in (60, 64, 67, 72)], d, .6)
    rise = S.tone(S.glide(500, 1000, d, .7), (1, .2)) * S.swell(d, .9, 1.5)
    return S.room(S.stack(body, (rise, .25), (S.sparkle(r, d, 5, 2600, 4200, .15), 1)), r, .25, .25)


def beam(r):
    """The beam burns across: warm, bright 'vwoooom'."""
    d = .7
    t = S.tt(d)
    chord = pad([S.midi(m) for m in (48, 60, 64, 67, 72)], d, .02) * (.8 + .2 * np.sin(2 * np.pi * 11 * t))
    air = S.lowpass(S.bandpass(S.noise(r, d), 1800, .7), 5000) * S.env(len(t), .01, .25, .2, .1)
    return S.room(S.stack(chord, (air, .12)), r, .2, .25)


def multiply(r):
    """«Примноження»: a cascade of magic pings and soft pops."""
    d = 1.2
    out = S.silence(d)
    for k in range(12):
        m = 72 + (0, 4, 7, 12, 16, 19)[k % 6] + 12 * (k // 6)
        S.add(out, k * .06, S.bell(S.midi(m), .3, 2.0, .6, .1), .28)
    for k in range(8):
        S.add(out, .15 + r.uniform(0, .8), S.bubble(r.uniform(700, 1300), .05, 1.7), .25)
    return S.room(out, r, .2, .25)


def halo(r):
    """The halo boomerang takes off: a whirring 'whup-whup-whup' flying away."""
    d = 1.3
    t = S.tt(d)
    rate = 9 + 5 * t
    whirr = .5 + .5 * np.sin(2 * np.pi * np.cumsum(rate) / S.SR) ** 2
    ring = S.tone(S.glide(880, 700, d), (1, .3, .1)) * whirr * S.env(len(t), .03, .5, .3, .2)
    air = S.bandpass(S.noise(r, d), S.glide(1600, 900, d), 1.2) * whirr * S.swell(d, .3, 1.0)
    return S.room(S.stack((ring, .5), (air, .7)), r, .15, .15)


def halo_catch(r):
    """Tongue catches the halo: a clear 'ding!'."""
    out = S.mix(.9, (0, S.bell(S.midi(88), .8, 1.4, 1.0, .35), .7), (0, S.bell(S.midi(95), .6, 1.4, .8, .2), .35))
    S.add(out, .05, S.sparkle(r, .5, 4, 3000, 4500, .2), 1)
    return S.room(out, r, .2, .25)


def rebuild(r):
    """Clouds rearrange: a magic swish up with shimmer."""
    d = .9
    return S.room(S.mix(d, (0, S.lowpass(S.whoosh(r, .8, 500, 2400, .8, .6), 3500), .6),
                        (.1, S.sparkle(r, .75, 7, 2200, 4800, .3), 1)), r, .2, .2)


def cloud_pop(r):
    """A new cloud puffs in: soft 'pff' + bloop."""
    puff = S.lowpass(S.noise(r, .15), 1500, .6) * S.perc(.15, .005, .04)
    return S.mix(.3, (0, puff, .7), (0, S.bubble(420, .09, 1.6), .8))


def boss_hit(r):
    """«SASAT!»: the halo bonks his head — BONK, a metallic ring, a wobble and tweets."""
    bonk = S.stack(S.wood(380, .15, .05), (S.tone(S.glide(170, 80, .15), (1, .5, .2)) * S.perc(.15, .002, .05), .8))
    ring = S.bell(560, .8, 1.41, 1.2, .3, .05)
    out = S.mix(1.3, (0, bonk, 1), (0, ring, .35), (.06, S.boing(460, 230, .35, 15, 1.2), .4))
    for k, m in enumerate((93, 96, 93, 96, 93)):
        S.add(out, .45 + k * .13, S.bell(S.midi(m), .15, 2.0, .5, .05), .15)
    return S.room(out, r, .15, .15)


def boss_defeated(r):
    """He gives up: a gentle sad 'awww'… that resolves into a soft harp run."""
    d = 2.4
    f = np.concatenate([S.glide(520, 440, .35), S.glide(440, 330, .6, 1.2)])
    aww = S.tone(f, (1, .5, .3, .15, .08), vib=.3, vib_rate=5) * S.env(len(f), .06, .5, .5, .15)
    out = S.mix(d, (0, S.lowpass(aww, 1500), .7))
    for k, m in enumerate((60, 64, 67, 72, 76, 79, 84)):
        S.add(out, 1.05 + k * .08, S.marimba(S.midi(m), .7, .25), .35)
    S.add(out, 1.55, S.sparkle(r, .8, 6, 2600, 4500, .2), 1)
    return S.room(out, r, .25, .3)


SOUNDS = {"whistle": whistle, "swallow": swallow, "hawk": hawk, "caw": caw, "peck": peck,
          "crow_eat": crow_eat, "melt": melt, "beam_charge": beam_charge, "beam": beam,
          "multiply": multiply, "halo": halo, "halo_catch": halo_catch, "rebuild": rebuild,
          "cloud_pop": cloud_pop, "boss_hit": boss_hit, "boss_defeated": boss_defeated}


def main(argv: list[str]) -> int:
    S.render_all(SOUNDS, Path(argv[0]) if argv else OUT, np.random.default_rng(303))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

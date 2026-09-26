#!/usr/bin/env python3
"""Synthesise the game's music and sound effects into jebik/assets/audio/.

Port of the approved ``music.py`` sketch: three music tracks (A 8-bit,
B cartoon ukulele+marimba, C swamp polka), the SFX set and the original
studio-splash fanfare (``intro_fanfare.wav``). Music is written as
a seamless loop: notes ringing past the end are folded back onto the start
and there is no fade-out.

    python3 tools/gen_audio.py
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "jebik" / "assets" / "audio"
SR = 22050
rng = np.random.default_rng(7)


def f(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def env(n, a=.005, d=.08, s=.6, r=.05):
    e = np.ones(n) * s
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    if ai:
        e[:ai] = np.linspace(0, 1, ai, endpoint=False)[:len(e[:ai])]
    e[ai:ai + di] = np.linspace(1, s, len(e[ai:ai + di]))
    if ri:
        e[-ri:] *= np.linspace(1, 0, len(e[-ri:]))
    return e


def osc(kind, freq, n, duty=.5):
    t = np.arange(n) / SR
    ph = (t * freq) % 1
    if kind == "sq":
        return np.where(ph < duty, 1., -1.)
    if kind == "tri":
        return 4 * abs(ph - .5) - 1
    if kind == "sin":
        return np.sin(2 * np.pi * ph)
    return 2 * ph - 1  # saw


def pluck(freq, n, decay=5):
    t = np.arange(n) / SR
    w = sum(np.sin(2 * np.pi * freq * k * t) / k ** 1.3 * np.exp(-t * decay * k * .7) for k in range(1, 7))
    return w * np.minimum(1, t * 400)


def marimba(freq, n):
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * freq * t) * np.exp(-t * 7)
            + .35 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t * 20)) * np.minimum(1, t * 800)


def kick(n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (55 + 120 * np.exp(-t * 30)) * t) * np.exp(-t * 14)


def snare(n):
    t = np.arange(n) / SR
    return (rng.uniform(-1, 1, n) * .7 + .3 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 22)


def hat(n):
    t = np.arange(n) / SR
    return rng.uniform(-1, 1, n) * np.exp(-t * 70) * .5


def write_wav(path: Path, buf: np.ndarray, peak: float = .85) -> None:
    b = buf / (np.max(np.abs(buf)) + 1e-9) * peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((b * 32767).astype(np.int16).tobytes())


class Track:
    def __init__(self, bpm, bars):
        self.beat = 60 / bpm
        self.loop_len = int(bars * 4 * self.beat * SR)
        self.buf = np.zeros(self.loop_len + 2 * SR)

    def add(self, start_beat, wave_, vol):
        i = int(start_beat * self.beat * SR)
        n = min(len(wave_), len(self.buf) - i)
        self.buf[i:i + n] += wave_[:n] * vol

    def n(self, beats):
        return int(beats * self.beat * SR)

    def save_loop(self, path: Path) -> None:
        loop = self.buf[:self.loop_len].copy()
        tail = self.buf[self.loop_len:]
        loop[:len(tail)] += tail          # ring-out wraps around -> seamless loop
        edge = int(.004 * SR)             # tiny de-click at the seam only
        loop[:edge] *= np.linspace(.6, 1, edge)
        loop[-edge:] *= np.linspace(1, .6, edge)
        write_wav(path, loop)


PROG = [(48, [60, 64, 67]), (43, [59, 62, 67]), (45, [60, 64, 69]), (41, [60, 65, 69])]
MEL = [(0, 72, .5), (.5, 74, .5), (1, 76, 1), (2, 79, .5), (2.5, 76, .5), (3, 74, 1),
       (4, 74, .5), (4.5, 76, .5), (5, 79, 1), (6, 81, .5), (6.5, 79, .5), (7, 74, 1),
       (8, 72, .5), (8.5, 76, .5), (9, 81, 1), (10, 79, .5), (10.5, 76, .5), (11, 72, 1),
       (12, 77, .5), (12.5, 76, .5), (13, 74, .5), (13.5, 72, .5), (14, 74, 1), (15, 79, 1)]


def music_a() -> Track:
    T = Track(150, 16)
    for rep in range(4):
        o = rep * 16
        for bar in range(4):
            root, ch = PROG[bar]
            b0 = o + bar * 4
            for k in range(8):
                T.add(b0 + k * .5, osc("tri", f(root + (12 if k % 2 else 0)), T.n(.45)) * env(T.n(.45), s=.8), .5)
            for k in range(4):
                T.add(b0 + k, osc("sq", f(ch[k % 3] + 12), T.n(.2), .25) * env(T.n(.2), s=.3), .12)
            for k in range(4):
                T.add(b0 + k, kick(T.n(.5)) if k % 2 == 0 else snare(T.n(.5)), .6 if k % 2 == 0 else .35)
                T.add(b0 + k + .5, hat(T.n(.25)), .25)
        if rep >= 1:
            for b, m, d in MEL:
                T.add(o + b, osc("sq", f(m), T.n(d * .9), .5) * env(T.n(d * .9), s=.55), .22)
        if rep == 3:
            for b, m, d in MEL:
                T.add(o + b, osc("sq", f(m + 12), T.n(d * .9), .125) * env(T.n(d * .9), s=.4), .08)
    return T


def music_b() -> Track:
    T = Track(118, 16)
    for rep in range(4):
        o = rep * 16
        for bar in range(4):
            root, ch = PROG[bar]
            b0 = o + bar * 4
            T.add(b0, pluck(f(root), T.n(1.5), 3), .5)
            T.add(b0 + 2, pluck(f(root + 7), T.n(1.5), 3), .4)
            for st in [0, .75, 1.5, 2, 2.75, 3.5]:
                for j, m in enumerate(ch):
                    T.add(b0 + st + j * .02, pluck(f(m), T.n(.7), 6), .16)
            for k in range(4):
                T.add(b0 + k + .5, hat(T.n(.2)), .12)
            T.add(b0, kick(T.n(.5)), .4)
            T.add(b0 + 2, kick(T.n(.5)), .3)
            T.add(b0 + 1, snare(T.n(.3)), .12)
            T.add(b0 + 3, snare(T.n(.3)), .12)
        if rep >= 1:
            for b, m, d in MEL:
                T.add(o + b, marimba(f(m), T.n(1.2)), .35)
    return T


def music_c() -> Track:
    T = Track(160, 16)
    mel3 = [(0, 76, .5), (.5, 77, .5), (1, 79, .5), (1.5, 76, .5), (2, 72, 1), (3, 79, 1), (4, 79, .5),
            (4.5, 81, .5), (5, 79, .5), (5.5, 77, .5), (6, 74, 1), (7, 71, 1), (8, 72, .5), (8.5, 74, .5),
            (9, 76, .5), (9.5, 77, .5), (10, 81, 1), (11, 79, 1), (12, 77, .5), (12.5, 76, .5),
            (13, 74, .5), (13.5, 71, .5), (14, 72, 2)]
    for rep in range(4):
        o = rep * 16
        for bar in range(4):
            root, ch = PROG[bar]
            b0 = o + bar * 4
            for k in range(4):
                if k % 2 == 0:
                    T.add(b0 + k, osc("tri", f(root - 12 + (7 if k == 2 else 0)), T.n(.4)) * env(T.n(.4), s=.7), .6)
                    T.add(b0 + k, kick(T.n(.4)), .35)
                else:
                    for m in ch:
                        T.add(b0 + k, osc("saw", f(m), T.n(.3)) * env(T.n(.3), s=.4), .05)
                    T.add(b0 + k, snare(T.n(.2)), .12)
        if rep >= 1:
            for b, m, d in mel3:
                n = T.n(d * .9)
                t = np.arange(n) / SR
                vib = np.sin(2 * np.pi * 5.5 * t) * .004
                w = np.sign(np.sin(2 * np.pi * f(m) * t * (1 + vib))) * .5 + np.sin(2 * np.pi * f(m) * 2 * t) * .3
                T.add(o + b, w * env(n, s=.7), .18)
    return T


# ---------------------------------------------------------------- sfx
def tt(d):
    return np.arange(int(d * SR)) / SR


def sweep(f0, f1, d, kind="sin", decay=4.0):
    t = tt(d)
    fr = np.linspace(f0, f1, len(t))
    ph = np.cumsum(fr) / SR
    w = np.sin(2 * np.pi * ph) if kind == "sin" else np.where(ph % 1 < .5, 1., -1.)
    return w * np.exp(-t * decay)


def lowpass(x, k=6):
    return np.convolve(x, np.ones(k) / k, mode="same")


def fade(x, ms=8):
    n = int(ms / 1000 * SR)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


def notes(seq, kind="sq", duty=.25, gap=.13, last=.45, sustain=.5):
    total = int((len(seq) * gap + last + .1) * SR)
    out = np.zeros(total)
    for i, m in enumerate(seq):
        st = int(i * gap * SR)
        n = int((gap * 1.3 if i < len(seq) - 1 else last) * SR)
        seg = osc(kind, f(m), n, duty) * env(n, s=sustain)
        out[st:st + n] += seg[:total - st]
    return out


def make_sfx() -> dict[str, np.ndarray]:
    s: dict[str, np.ndarray] = {}
    s["jump"] = sweep(300, 700, .15)
    s["tongue"] = np.concatenate([sweep(900, 1400, .08, "sq"), sweep(1400, 700, .08, "sq")]) * .6
    s["eat"] = np.concatenate([sweep(500, 300, .07), np.zeros(800), sweep(600, 350, .07)])
    noise = lowpass(rng.uniform(-1, 1, int(.5 * SR)), 5) * np.exp(-tt(.5) * 6)
    s["splash"] = noise + sweep(200, 80, .5) * .5
    s["hit"] = kick(int(.3 * SR)) + snare(int(.3 * SR)) * .5
    s["win"] = notes([72, 76, 79, 84, 79, 84], last=.5)
    # sad trombone: wah-wah-wah-waaah
    lose = np.zeros(int(1.6 * SR))
    for i, m in enumerate([67, 66, 65, 64]):
        d = .28 if i < 3 else .8
        n = int(d * SR)
        t = np.arange(n) / SR
        vib = (1 + .012 * np.sin(2 * np.pi * 6 * t)) if i == 3 else 1
        ph = np.cumsum(np.full(n, f(m - 12)) * vib) / SR
        w = lowpass(2 * (ph % 1) - 1, 10) * env(n, a=.03, s=.8, r=.08)
        st = int(i * .3 * SR)
        lose[st:st + n] += w[:len(lose) - st]
    s["lose"] = lose
    sj = sweep(220, 1100, .32, decay=3)
    t = tt(.32)
    s["superjump"] = sj * (1 + .3 * np.sin(2 * np.pi * 18 * t)) + sweep(440, 2200, .32, decay=5) * .25
    arp = notes([72, 76, 79, 84, 88], kind="tri", duty=.5, gap=.06, last=.3, sustain=.6)
    sparkle = sweep(2400, 3200, .25, decay=10) * .2
    st = int(.2 * SR)
    arp[st:st + len(sparkle)] += sparkle[:len(arp) - st]
    s["powerup"] = arp
    t = tt(.05)
    s["click"] = osc("tri", 1250, len(t)) * np.exp(-t * 90)
    t = tt(.4)
    burp_f = np.linspace(120, 70, len(t))
    ph = np.cumsum(burp_f) / SR
    burp = lowpass(2 * (ph % 1) - 1, 8) * (0.6 + .4 * np.sin(2 * np.pi * 24 * t)) * env(len(t), a=.02, s=.9, r=.1)
    s["overeat"] = burp
    s["full"] = notes([76, 79, 84, 88], kind="sq", duty=.25, gap=.09, last=.35, sustain=.45)
    s["denied"] = np.concatenate([osc("sq", 220, int(.06 * SR), .5) * env(int(.06 * SR), s=.6),
                                  np.zeros(int(.03 * SR)),
                                  osc("sq", 165, int(.09 * SR), .5) * env(int(.09 * SR), s=.6)])
    t = tt(.025)
    s["tick"] = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 160)
    return s


# ---------------------------------------------------------------- studio fanfare
# An ORIGINAL pompous fanfare for the «21th MANGO CAT» splash (not the Fox
# melody): snare + timpani roll crescendo, then a C-major brass fanfare with
# timpani hits and a cymbal on the final chord. ~6.8 s.
FANFARE_LEN = 6.9
MELODY = [(1.60, .18, 67), (1.80, .10, 67), (1.92, .55, 72), (2.47, .18, 71), (2.67, .18, 72),
          (2.87, .66, 76), (3.55, .18, 74), (3.75, .18, 72), (3.95, .34, 69), (4.30, .28, 71),
          (4.60, 2.00, 72)]
CHORDS = [(1.60, 1.27, (48, 52, 55, 60)), (2.87, .68, (45, 52, 57, 60)), (3.55, .75, (41, 53, 57, 60)),
          (4.30, .30, (43, 55, 59, 62)), (4.60, 2.10, (36, 48, 55, 60, 64))]
TIMPANI = [(1.60, 36, 1.0), (1.92, 43, .7), (2.87, 33, .8), (3.55, 29, .8), (4.30, 31, .8),
           (4.45, 31, .8), (4.60, 36, 1.1)]


def brass(freq: float, dur: float, vol: float = 1.0) -> np.ndarray:
    """Additive brass: brightness opens on the attack, gentle late vibrato."""
    n = int((dur + .25) * SR)
    t = np.arange(n) / SR
    amp = np.minimum(1, t / .045) * np.where(t < dur, 1.0, np.exp(-(t - dur) * 14))
    amp *= 1 - .12 * np.minimum(1, t / max(dur, .01))
    bright = .35 + .5 * np.minimum(1, t / .09) - .15 * np.minimum(1, t / 1.5)
    vib = np.sin(2 * np.pi * 5.2 * t) * .004 * np.minimum(1, np.maximum(0, t - .25) * 3)
    out = np.zeros(n)
    for det in (-.0025, 0, .003):
        ph = 2 * np.pi * freq * (1 + det) * (t + np.cumsum(vib) / SR)
        for k in range(1, 13):
            if freq * k > SR / 2.2:
                break
            out += np.sin(k * ph) * (bright ** (k - 1)) / k
    return out * amp * vol / 3


def timpani(m: float, vol: float, dur: float = 1.6) -> np.ndarray:
    t = tt(dur)
    fr = f(m) * (1 + .06 * np.exp(-t * 20))
    body = np.sin(2 * np.pi * np.cumsum(fr) / SR) + .4 * np.sin(2 * np.pi * np.cumsum(fr * 1.5) / SR) * np.exp(-t * 6)
    thump = lowpass(rng.uniform(-1, 1, len(t)), 12) * np.exp(-t * 30)
    return (body * np.exp(-t * 2.6) + thump * .8) * vol


def cymbal(dur: float = 2.5) -> np.ndarray:
    noise = rng.uniform(-1, 1, int(dur * SR))
    hi = noise - lowpass(noise, 4)
    return hi * np.exp(-tt(dur) * 1.6) * np.minimum(1, tt(dur) * 300)


def intro_fanfare() -> np.ndarray:
    out = np.zeros(int(FANFARE_LEN * SR))

    def add(start: float, w: np.ndarray, vol: float) -> None:
        i = int(start * SR)
        n = min(len(w), len(out) - i)
        out[i:i + n] += w[:n] * vol
    # snare roll + timpani rumble crescendo (0 .. 1.6 s)
    k = 0.0
    while k < 1.58:
        grow = (k / 1.58) ** 1.7
        add(k, snare(int(.06 * SR)), .06 + .5 * grow)
        k += 1 / 26
    k = 0.0
    while k < 1.58:
        add(k, timpani(31, 1.0, .25), .05 + .35 * (k / 1.58) ** 2)
        k += 1 / 14
    for start, dur, notes_ in CHORDS:                   # brass section
        for m in notes_:
            add(start, brass(f(m), dur), .22)
    for start, dur, m in MELODY:                        # trumpets (two octaves)
        add(start, brass(f(m), dur, 1.0), .5)
        add(start, brass(f(m + 12), dur, .6), .18)
    for start, m, vol in TIMPANI:
        add(start, timpani(m, vol), .75)
    add(1.60, cymbal(1.6), .25)
    add(4.60, cymbal(2.3), .4)
    k = 5.2
    while k < 6.4:                                      # final timpani roll
        add(k, timpani(36, 1.0, .3), .12 + .15 * (k - 5.2))
        k += 1 / 16
    add(6.4, timpani(24, 1.2, .5), .9)
    hall = out.copy()                                   # a little hall reverb
    for delay, g in ((.043, .35), (.071, .28), (.113, .22), (.167, .16), (.241, .1)):
        d = int(delay * SR)
        hall[d:] += out[:-d] * g
    fade_n = int(.35 * SR)
    hall[-fade_n:] *= np.linspace(1, 0, fade_n)
    return hall


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("music_a.wav", music_a), ("music_b.wav", music_b), ("music_c.wav", music_c)):
        fn().save_loop(OUT / name)
        print("wrote", name)
    for name, buf in make_sfx().items():
        write_wav(OUT / f"sfx_{name}.wav", fade(buf, 4), peak=.8)
        print("wrote", f"sfx_{name}.wav")
    write_wav(OUT / "intro_fanfare.wav", fade(intro_fanfare(), 6), peak=.9)   # last: keeps rng order
    print("wrote intro_fanfare.wav")
    return 0


if __name__ == "__main__":
    sys.exit(main())

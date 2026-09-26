"""Tiny numpy synthesis kit for the game's sound effects (tools only, no pygame).

Soft, cartoon-style building blocks: pitch-swept sines with rounded
harmonics, FM bells / wood blocks, filtered noise (swept state-variable
filter), bubbles, a short room reverb, smooth envelopes, and a writer that
removes DC, fades the ends (no clicks) and normalises the peak to -3 dBFS.

Used by ``tools/gen_audio.py`` (core SFX) and ``tools/gen_audio_<world>.py``.
Everything is deterministic: pass a ``np.random.Generator`` where noise is used.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

SR = 22050
PEAK = 10 ** (-3 / 20)            # -3 dBFS


# ---------------------------------------------------------------- basics
def tt(d: float) -> np.ndarray:
    """Time axis (s) for ``d`` seconds."""
    return np.arange(int(round(d * SR))) / SR


def n_of(d: float) -> int:
    return int(round(d * SR))


def midi(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def glide(f0: float, f1: float, d: float, curve: float = 1.0) -> np.ndarray:
    """Exponential (musical) pitch glide f0 -> f1; ``curve`` > 1 = fast start."""
    u = np.linspace(0.0, 1.0, n_of(d)) ** (1 / curve)
    return f0 * (f1 / f0) ** u


def phase(freq) -> np.ndarray:
    """Phase (radians) of a frequency curve (array) or constant."""
    return 2 * np.pi * np.cumsum(np.asarray(freq, dtype=np.float64)) / SR


def tone(freq, harmonics=(1.0,), vib: float = 0.0, vib_rate: float = 6.0) -> np.ndarray:
    """Sine partials 1, 2, 3... with the given amplitudes (round timbre), ``freq``
    an array (see :func:`glide`); optional vibrato depth in semitones."""
    f = np.asarray(freq, dtype=np.float64)
    if vib:
        t = np.arange(len(f)) / SR
        f = f * 2 ** (vib * np.sin(2 * np.pi * vib_rate * t) / 12)
    ph = phase(f)
    out = np.zeros(len(f))
    for k, a in enumerate(harmonics, start=1):
        if a:
            alias = f * k < SR * 0.45                  # drop partials above ~10 kHz
            out += a * np.sin(k * ph) * alias
    return out


def const(f: float, d: float) -> np.ndarray:
    return np.full(n_of(d), float(f))


# ---------------------------------------------------------------- envelopes
def env(n: int, attack: float = 0.005, decay: float = 0.2, sustain: float = 0.0,
        release: float = 0.02, hold: float = 0.0) -> np.ndarray:
    """Smooth envelope: raised-cosine attack, exponential decay toward
    ``sustain`` (time constant ``decay``), raised-cosine release at the end."""
    t = np.arange(n) / SR
    e = sustain + (1 - sustain) * np.exp(-np.maximum(0.0, t - attack - hold) / max(decay, 1e-4))
    a = n_of(attack)
    if a > 0:
        e[:a] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    r = min(n, n_of(release))
    if r > 0:
        e[-r:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r))
    return e


def perc(d: float, attack: float = 0.004, decay: float = 0.08) -> np.ndarray:
    """Percussive envelope over ``d`` seconds."""
    return env(n_of(d), attack, decay, 0.0, min(0.03, d * 0.3))


def swell(d: float, peak_at: float = 0.5, power: float = 1.5) -> np.ndarray:
    """Soft rise-and-fall (whooshes, rumbles): a skewed sine hump."""
    u = np.linspace(0, 1, n_of(d))
    k = np.where(u < peak_at, u / max(peak_at, 1e-6) * 0.5, 0.5 + (u - peak_at) / max(1 - peak_at, 1e-6) * 0.5)
    return np.sin(np.pi * k) ** power


# ---------------------------------------------------------------- filters
def svf(x: np.ndarray, cutoff, q: float = 0.7, mode: str = "lp") -> np.ndarray:
    """Zavalishin TPT state-variable filter with a per-sample cutoff (Hz)."""
    x = np.asarray(x, dtype=np.float64)
    fc = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
    g = np.tan(np.pi * np.clip(fc, 10, SR * 0.45) / SR)
    k = 1.0 / max(q, 0.05)
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    out = np.empty_like(x)
    ic1 = ic2 = 0.0
    want = {"lp": 0, "bp": 1, "hp": 2}[mode]
    xs, a1s, a2s, a3s = x.tolist(), a1.tolist(), a2.tolist(), a3.tolist()
    res = [0.0] * len(xs)
    for i in range(len(xs)):
        v0 = xs[i]
        v3 = v0 - ic2
        v1 = a1s[i] * ic1 + a2s[i] * v3
        v2 = ic2 + a2s[i] * ic1 + a3s[i] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        res[i] = v2 if want == 0 else (v1 if want == 1 else v0 - k * v1 - v2)
    out[:] = res
    return out


def lowpass(x: np.ndarray, cutoff, q: float = 0.6) -> np.ndarray:
    return svf(x, cutoff, q, "lp")


def bandpass(x: np.ndarray, cutoff, q: float = 1.5) -> np.ndarray:
    return svf(x, cutoff, q, "bp")


def highpass(x: np.ndarray, cutoff, q: float = 0.6) -> np.ndarray:
    return svf(x, cutoff, q, "hp")


def noise(rng: np.random.Generator, d: float) -> np.ndarray:
    return rng.uniform(-1, 1, n_of(d))


def pink(rng: np.random.Generator, d: float) -> np.ndarray:
    """Soft pink-ish noise (1/f via FFT shaping)."""
    n = n_of(d)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec /= np.sqrt(np.maximum(f, 20.0))
    x = np.fft.irfft(spec, n)
    return x / (np.max(np.abs(x)) + 1e-9)


# ---------------------------------------------------------------- instruments
def bell(f: float, d: float, ratio: float = 3.5, index: float = 1.2, decay: float = 0.35,
         bright_decay: float = 0.08) -> np.ndarray:
    """FM bell / glockenspiel: the brightness fades faster than the body."""
    t = tt(d)
    mod = index * np.exp(-t / bright_decay) * np.sin(2 * np.pi * f * ratio * t)
    return np.sin(2 * np.pi * f * t + mod) * env(len(t), 0.002, decay, 0.0, 0.03)


def marimba(f: float, d: float, decay: float = 0.18) -> np.ndarray:
    t = tt(d)
    body = np.sin(2 * np.pi * f * t) * np.exp(-t / decay)
    knock = 0.3 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t / (decay * 0.15))
    return (body + knock) * env(len(t), 0.002, 10, 1.0, 0.02)


def wood(f: float, d: float = 0.08, decay: float = 0.025) -> np.ndarray:
    """Soft wood block / 'pok'."""
    t = tt(d)
    fr = f * (1 + 0.25 * np.exp(-t / 0.006))
    return (np.sin(phase(fr)) + 0.25 * np.sin(phase(fr * 2.7))) * env(len(t), 0.001, decay, 0.0, 0.01)


def bubble(f0: float, d: float = 0.07, rise: float = 1.8) -> np.ndarray:
    """A water bubble 'bloop': sine whose pitch rises as it pops."""
    t = tt(d)
    fr = f0 * (1 + (rise - 1) * (t / d) ** 1.5)
    return np.sin(phase(fr)) * env(len(t), 0.003, d * 0.45, 0.0, 0.012)


def boing(f0: float, f1: float, d: float, wobble: float = 14.0, depth: float = 0.6,
          harmonics=(1.0, 0.18, 0.05)) -> np.ndarray:
    """Cartoon spring: a glide with a decaying pitch wobble."""
    t = tt(d)
    base = glide(f0, f1, d, 1.6)
    wob = 2 ** (depth * np.sin(2 * np.pi * wobble * t) * np.exp(-t / (d * 0.5)) / 12)
    return tone(base * wob, harmonics) * env(len(t), 0.004, d * 0.4, 0.0, 0.03)


def whoosh(rng: np.random.Generator, d: float, f0: float, f1: float, q: float = 1.2,
           peak_at: float = 0.5) -> np.ndarray:
    """Air rush: band-passed noise whose band sweeps f0 -> f1, rise-and-fall."""
    x = bandpass(noise(rng, d), glide(f0, f1, d), q)
    return x * swell(d, peak_at)


def sparkle(rng: np.random.Generator, d: float, n: int = 6, lo: float = 2200, hi: float = 5200,
            vol: float = 0.35) -> np.ndarray:
    """A few tiny high bell pings scattered over ``d`` seconds."""
    out = np.zeros(n_of(d))
    for _ in range(n):
        f = rng.uniform(lo, hi)
        st = rng.uniform(0, max(0.0, d - 0.15))
        add(out, st, bell(f, 0.15, ratio=2.0, index=0.6, decay=0.05), vol * rng.uniform(0.5, 1.0))
    return out


# ---------------------------------------------------------------- mixing
def silence(d: float) -> np.ndarray:
    return np.zeros(n_of(d))


def add(buf: np.ndarray, start: float, x: np.ndarray, vol: float = 1.0) -> np.ndarray:
    """Mix ``x`` into ``buf`` at ``start`` seconds (clipped to the buffer)."""
    i = n_of(start)
    if i >= len(buf):
        return buf
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * vol
    return buf


def mix(d: float, *parts: tuple[float, np.ndarray, float]) -> np.ndarray:
    """``mix(total, (start, wave, vol), ...)``"""
    out = silence(d)
    for start, x, vol in parts:
        add(out, start, x, vol)
    return out


def stack(*parts) -> np.ndarray:
    """Sum waves of different lengths (zero-padded); a part may be ``(wave, vol)``."""
    items = [(x, 1.0) if isinstance(x, np.ndarray) else x for x in parts]
    out = np.zeros(max(len(x) for x, _ in items))
    for x, vol in items:
        out[:len(x)] += x * vol
    return out


def soft_clip(x: np.ndarray, drive: float = 1.5) -> np.ndarray:
    """Gentle tanh saturation: tames spiky transients so a dense sound is not
    quieter than the rest at the same peak level."""
    x = x / (np.max(np.abs(x)) + 1e-12)
    return np.tanh(drive * x) / np.tanh(drive)


def room(x: np.ndarray, rng: np.random.Generator, mix_: float = 0.18, decay: float = 0.25,
         tone_hz: float = 3000.0, tail: float | None = None) -> np.ndarray:
    """Gentle reverb-ish tail: convolution with a short, dark, decaying noise
    burst. Extends the sound by ``tail`` seconds (default 2.5 x decay)."""
    tail = decay * 2.5 if tail is None else tail
    t = tt(tail)
    ir = lowpass(rng.standard_normal(len(t)), tone_hz, 0.5) * np.exp(-t / decay)
    ir[:n_of(0.012)] *= np.linspace(0, 1, n_of(0.012))    # pre-delay-ish soft onset
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    y = np.concatenate([x, np.zeros(len(t))])
    wet = np.fft.irfft(np.fft.rfft(y, 2 * len(y)) * np.fft.rfft(ir, 2 * len(y)), 2 * len(y))[:len(y)]
    return y * (1 - mix_ * 0.5) + wet * mix_ * 3.0


def trim_tail(x: np.ndarray, floor_db: float = -60.0) -> np.ndarray:
    """Cut the silent end (below ``floor_db`` relative to the peak)."""
    peak = np.max(np.abs(x)) + 1e-12
    idx = np.nonzero(np.abs(x) > peak * 10 ** (floor_db / 20))[0]
    return x[:idx[-1] + n_of(0.02)] if len(idx) else x


def finish(x: np.ndarray, fade_in: float = 0.003, fade_out: float = 0.03,
           peak: float = PEAK) -> np.ndarray:
    """Remove DC, trim the silent tail, raised-cosine fade in/out, normalise."""
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x)
    x = highpass(x, 35.0, 0.6)                          # no DC / sub rumble
    x = trim_tail(x)
    a, r = min(len(x), n_of(fade_in)), min(len(x), n_of(fade_out))
    if a:
        x[:a] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if r:
        x[-r:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r))
    return x / (np.max(np.abs(x)) + 1e-12) * peak


def write(path: Path, x: np.ndarray) -> None:
    """16-bit mono WAV at :data:`SR` (``x`` already finished)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def loudness(x: np.ndarray) -> tuple[float, float, float]:
    """(peak dBFS, whole-file RMS dBFS, max 100 ms momentary RMS dBFS)."""
    x = np.asarray(x, dtype=np.float64)
    peak = 20 * math.log10(np.max(np.abs(x)) + 1e-12)
    rms = 20 * math.log10(math.sqrt(np.mean(x ** 2)) + 1e-12)
    w = max(1, n_of(0.1))
    c = np.cumsum(np.concatenate([[0.0], x ** 2]))
    mom = (c[w:] - c[:-w]) / w if len(x) > w else np.array([np.mean(x ** 2)])
    return peak, rms, 10 * math.log10(np.max(mom) + 1e-12)


def read(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        raw = w.readframes(w.getnframes())
        ch = w.getnchannels()
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767
    return x.reshape(-1, ch).mean(axis=1) if ch > 1 else x


def render_all(sounds: dict, out_dir: Path, rng: np.random.Generator, prefix: str = "") -> None:
    """``sounds``: name -> fn(rng) -> raw wave. Finishes and writes each file."""
    for name, fn in sounds.items():
        x = finish(fn(rng))
        write(out_dir / f"{prefix}{name}.wav", x)
        p, r, m = loudness(x)
        print(f"wrote {prefix}{name}.wav  {len(x) / SR:5.2f}s  peak {p:5.1f}  rms {r:6.1f}  mom {m:6.1f} dBFS")

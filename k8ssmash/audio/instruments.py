"""Sample-style instruments for the soundtrack. Everything is synthesized offline with numpy/scipy:
oversampled oscillators (no aliasing), detuned ensembles, FM and additive voices, filtered noise."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

SR = 44100


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, min(fc, SR * 0.45) / (SR / 2), "low", output="sos"), x)


def hp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, fc / (SR / 2), "high", output="sos"), x)


def bp(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, [lo / (SR / 2), min(hi, SR * 0.45) / (SR / 2)], "band", output="sos"), x)


def noise(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-1, 1, n)


def adsr(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    env = np.full(n, s, dtype=float)
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    ai = min(ai, n)
    if ai:
        env[:ai] = np.linspace(0, 1, ai) ** 1.2
    di = min(di, max(0, n - ai))
    if di:
        env[ai:ai + di] = np.linspace(1, s, di)
    ri = min(ri, n)
    if ri:
        env[n - ri:] *= np.linspace(1, 0, ri) ** 1.5
    return env


def osc(kind: str, freq: float | np.ndarray, n: int, phase0: float = 0.0) -> np.ndarray:
    """Band-limited-ish oscillator: generated at 2x and decimated with a proper anti-alias filter."""
    f = np.broadcast_to(freq, (n,)) if np.ndim(freq) == 0 else freq
    f2 = np.repeat(f, 2)
    ph = (np.cumsum(f2) / (SR * 2) + phase0) % 1.0
    if kind == "saw":
        w = 2 * ph - 1
    elif kind == "square":
        w = np.where(ph < 0.5, 1.0, -1.0)
    elif kind == "pulse25":
        w = np.where(ph < 0.25, 1.0, -1.0)
    elif kind == "tri":
        w = 4 * np.abs(ph - 0.5) - 1
    else:
        w = np.sin(2 * np.pi * ph)
    return resample_poly(w, 1, 2)[:n]


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))


def _len(dur: float, tail: float) -> int:
    return max(64, int((dur + tail) * SR))


# --- pitched instruments ----------------------------------------------------------------------
def strings(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.35)
    t = np.arange(n) / SR
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.1 * t) * np.minimum(1, t / 0.5)
    sig = sum(osc("saw", f * vib * 2 ** (c / 1200), n, ph) for c, ph in
              ((-14, .0), (-8, .17), (-3, .3), (3, .6), (8, .75), (14, .9))) / 6
    sig = lp(sig, min(3000, f * 4 + 700))
    return sig * adsr(n, 0.13, 0.2, 0.82, 0.32)


def brass(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.12)
    sig = osc("saw", f * 0.998, n) * 0.5 + osc("saw", f * 1.004, n) * 0.4 + osc("sine", f, n) * 0.35
    bright = adsr(n, 0.05, 0.25, 0.55, 0.1)
    out = lp(sig, 800) * (1 - bright) + lp(sig, min(3400, f * 6)) * bright
    return out * adsr(n, 0.025, 0.1, 0.85, 0.1)


def flute(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.12)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.6 * t) * np.minimum(1, np.maximum(0, t - 0.15) / 0.3)
    ph = np.cumsum(f * vib) / SR
    sig = np.sin(2 * np.pi * ph) + 0.22 * np.sin(4 * np.pi * ph) + 0.07 * np.sin(6 * np.pi * ph)
    sig += 0.05 * bp(noise(n, 3), f * 1.5, f * 4) * 4
    return sig * adsr(n, 0.05, 0.1, 0.8, 0.12) * 0.7


def marimba(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 0.7), 0.25)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.4 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 18)
           + 0.15 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 40))
    sig += 0.12 * hp(noise(n, 5), 2500) * np.exp(-t * 90)
    return sig * 0.9


def bell(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(max(dur, 0.8), 1.2)
    t = np.arange(n) / SR
    parts = ((1.0, 1.0, 1.8), (2.76, 0.55, 2.6), (5.40, 0.32, 3.8), (8.93, 0.18, 5.5))
    sig = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in parts)
    return sig * 0.55


def epiano(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 1.4), 0.3)
    t = np.arange(n) / SR
    idx = 2.4 * np.exp(-t * 5.0) + 0.35
    sig = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    sig += 0.18 * np.sin(2 * np.pi * f * 14 * t + 0.6 * np.sin(2 * np.pi * f * 14 * t)) * np.exp(-t * 38)
    return sig * np.exp(-t * 1.6) * adsr(n, 0.004, 0.05, 1.0, 0.2) * 0.8


def harp(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 1.6), 0.2)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 14):
        if f * k > 9000:
            break
        sig += (1.0 / k ** 1.1) * np.sin(2 * np.pi * f * k * (1 + 0.0004 * k * k) * t) * np.exp(-t * (1.8 + 1.4 * k))
    return sig * adsr(n, 0.002, 0.03, 1.0, 0.12) * 0.9


def pad(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.7)
    sig = (osc("tri", f * 0.997, n) + osc("saw", f * 1.004, n, 0.4) * 0.5 + osc("tri", f * 2.002, n) * 0.25)
    sig = lp(sig, min(2200, f * 4 + 500))
    return sig * adsr(n, 0.45, 0.3, 0.85, 0.6) * 0.8


def choir(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.5)
    t = np.arange(n) / SR
    vib = 1 + 0.005 * np.sin(2 * np.pi * 5.3 * t) * np.minimum(1, np.maximum(0, t - 0.2) / 0.5)
    ph = np.cumsum(f * vib) / SR
    sig = np.zeros(n)
    formants = ((620, 90, 1.0), (1180, 110, 0.55), (2500, 160, 0.25))  # an "ah" vowel
    for k in range(1, 28):
        fk = f * k
        if fk > 5000:
            break
        amp = sum(a * np.exp(-0.5 * ((fk - fc) / bw) ** 2) for fc, bw, a in formants) + 0.03 / k
        sig += amp * np.sin(2 * np.pi * ph * k)
    sig += 0.05 * bp(noise(n, 9), 800, 3000)
    return sig * adsr(n, 0.35, 0.2, 0.85, 0.5) * 0.45


def bass_fretless(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.12)
    t = np.arange(n) / SR
    vib = 1 + 0.002 * np.sin(2 * np.pi * 5 * t) * np.minimum(1, t / 0.3)
    ph = np.cumsum(f * vib) / SR
    sig = np.sin(2 * np.pi * ph) + 0.45 * np.sin(4 * np.pi * ph) + 0.22 * np.sin(6 * np.pi * ph) * np.exp(-t * 4)
    sig = lp(sig, 900)
    return sig * adsr(n, 0.01, 0.12, 0.8, 0.1) * 0.9


def bass_synth(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.08)
    t = np.arange(n) / SR
    saw = osc("saw", f, n)
    cutoff = 380 + 2600 * np.exp(-t * 14)
    out = np.zeros(n)
    for lo, hi in ((0, n // 3), (n // 3, 2 * n // 3), (2 * n // 3, n)):  # block-wise sweeping filter
        out[lo:hi] = lp(saw, float(np.mean(cutoff[lo:hi])))[lo:hi]
    return (out * 0.8 + np.sin(2 * np.pi * f * t) * 0.6) * adsr(n, 0.004, 0.08, 0.8, 0.06)


def bass_slap(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 0.5), 0.1)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.6 * np.sin(4 * np.pi * f * t) * np.exp(-t * 12) + 0.3 * np.sin(6 * np.pi * f * t) * np.exp(-t * 20)
    sig += 0.25 * hp(noise(n, 2), 1800) * np.exp(-t * 120)
    return lp(sig, 2200) * np.exp(-t * 4.5) * 1.1


def lead_synth(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.1)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.8 * t) * np.minimum(1, np.maximum(0, t - 0.12) / 0.25)
    sig = (osc("saw", f * vib * 0.997, n) * 0.4 + osc("saw", f * vib * 1.004, n) * 0.4
           + osc("sine", f * vib, n) * 0.5 + osc("tri", f * vib * 2, n) * 0.18)
    bright = adsr(n, 0.02, 0.2, 0.35, 0.1)  # the filter opens on the attack and settles: a played note, not a buzz
    sig = lp(sig, 1500) * (1 - bright) + lp(sig, min(4200, f * 7)) * bright
    return sig * adsr(n, 0.012, 0.12, 0.8, 0.14) * 0.8


def steel(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 0.8), 0.3)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t * 4)
           + 0.35 * np.sin(2 * np.pi * f * 3.02 * t) * np.exp(-t * 7))
    sig *= 1 + 0.25 * np.sin(2 * np.pi * 9 * t)  # the shimmer of a steel pan
    return sig * np.exp(-t * 3.2) * 0.8


INSTRUMENTS = {
    "strings": strings, "brass": brass, "flute": flute, "marimba": marimba, "bell": bell, "epiano": epiano,
    "harp": harp, "pad": pad, "choir": choir, "bass_fretless": bass_fretless, "bass_synth": bass_synth,
    "bass_slap": bass_slap, "lead_synth": lead_synth, "steel": steel,
}


# --- percussion ------------------------------------------------------------------------------
def _sweep(f0: float, f1: float, dur: float, decay: float) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t * decay)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def kick(punch: float = 1.0) -> np.ndarray:
    t = np.arange(int(0.32 * SR)) / SR
    body = _sweep(170, 46, 0.32, 26) * np.exp(-t * 9)
    click = hp(noise(len(t), 4), 1500) * np.exp(-t * 220) * 0.5 * punch
    return lp(body * 1.25 + click, 4500)


def snare(tone: float = 1.0) -> np.ndarray:
    t = np.arange(int(0.28 * SR)) / SR
    n = bp(noise(len(t), 6), 1400, 8000) * np.exp(-t * 17)
    body = (np.sin(2 * np.pi * 190 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t * 28) * 0.55 * tone
    return n * 0.9 + body


def hat(open_: bool = False) -> np.ndarray:
    t = np.arange(int((0.28 if open_ else 0.06) * SR)) / SR
    return hp(noise(len(t), 7), 7000) * np.exp(-t * (11 if open_ else 80)) * 0.5


def shaker() -> np.ndarray:
    t = np.arange(int(0.09 * SR)) / SR
    return bp(noise(len(t), 8), 4500, 10000) * np.sin(np.minimum(1, t / 0.09) * np.pi) ** 1.3 * 0.45


def clap() -> np.ndarray:
    t = np.arange(int(0.25 * SR)) / SR
    out = np.zeros(len(t))
    for i, off in enumerate((0, 0.011, 0.023)):
        j = int(off * SR)
        out[j:] += bp(noise(len(t) - j, 10 + i), 900, 4500) * np.exp(-np.arange(len(t) - j) / SR * 60)
    out += bp(noise(len(t), 14), 900, 3500) * np.exp(-t * 14) * 0.6
    return out * 0.7


def tom(f0: float = 160, f1: float = 90) -> np.ndarray:
    t = np.arange(int(0.45 * SR)) / SR
    return _sweep(f0, f1, 0.45, 12) * np.exp(-t * 7) * 0.9


def conga(high: bool = True) -> np.ndarray:
    f0, f1 = (330, 250) if high else (220, 170)
    t = np.arange(int(0.3 * SR)) / SR
    return (_sweep(f0, f1, 0.3, 30) * np.exp(-t * 14) + 0.2 * hp(noise(len(t), 3), 1500) * np.exp(-t * 150)) * 0.9


def timpani() -> np.ndarray:
    t = np.arange(int(1.1 * SR)) / SR
    return (_sweep(115, 80, 1.1, 5) * np.exp(-t * 3.2) + 0.5 * np.sin(2 * np.pi * 170 * t) * np.exp(-t * 6)
            + 0.15 * lp(noise(len(t), 12), 600) * np.exp(-t * 30))


def crash() -> np.ndarray:
    t = np.arange(int(2.2 * SR)) / SR
    return hp(noise(len(t), 15), 3200) * np.exp(-t * 2.4) * 0.55


DRUMS = {
    "kick": kick, "snare": snare, "hat": hat, "ohat": lambda: hat(True), "shaker": shaker, "clap": clap,
    "tom_hi": lambda: tom(210, 120), "tom_mid": lambda: tom(160, 90), "tom_lo": lambda: tom(115, 65),
    "conga_hi": lambda: conga(True), "conga_lo": lambda: conga(False), "timpani": timpani, "crash": crash,
}


# --- space ------------------------------------------------------------------------------------
def make_ir(seconds: float = 2.2, seed: int = 1, bright: float = 0.6, predelay: float = 0.018) -> np.ndarray:
    """A synthetic stereo hall impulse response: early reflections, then a diffuse tail that darkens."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for ch in range(2):
        tail = rng.standard_normal(n)
        lo = lp(tail, 1800) * np.exp(-t * (6.9 / seconds))
        hi = hp(tail, 2500) * np.exp(-t * (6.9 / seconds) * 2.6) * bright
        ir[:, ch] = lo + hi
        for tap in rng.uniform(0.012, 0.09, 8):
            ir[int(tap * SR), ch] += rng.uniform(0.3, 0.8) * (1 if rng.random() < 0.5 else -1)
    pre = int(predelay * SR)
    ir = np.vstack([np.zeros((pre, 2)), ir])
    return ir / np.sqrt((ir ** 2).sum(axis=0).max())


def chorus(x: np.ndarray, depth: float = 0.0035, rate: float = 0.6, mix: float = 0.5) -> np.ndarray:
    """Ensemble chorus: three slowly modulated delay taps spread across the stereo field. Takes mono or stereo,
    returns stereo. This is what turns thin synth voices into a section."""
    stereo = x if x.ndim == 2 else np.stack([x, x], axis=1)
    n = len(stereo)
    t = np.arange(n) / SR
    out = stereo.astype(np.float64).copy() * (1 - mix * 0.5)
    for k, (ph, ch_gain) in enumerate(((0.0, (1.0, 0.35)), (2.1, (0.65, 0.65)), (4.2, (0.35, 1.0)))):
        delay = (0.012 + 0.004 * k + depth * np.sin(2 * np.pi * rate * (1 + 0.13 * k) * t + ph)) * SR
        idx = np.clip(np.arange(n) - delay, 0, n - 1)
        lo = idx.astype(int)
        frac = idx - lo
        hi = np.minimum(lo + 1, n - 1)
        for c in (0, 1):
            tap = stereo[lo, c] * (1 - frac) + stereo[hi, c] * frac
            out[:, c] += tap * mix * 0.5 * ch_gain[c]
    return out.astype(np.float32)


def echo(stereo: np.ndarray, delay_s: float, feedback: float = 0.42, tone: float = 3200.0, taps: int = 6) -> np.ndarray:
    """The classic 16-bit console echo: a ping-ponging repeat that darkens with every pass."""
    d = int(delay_s * SR)
    out = np.zeros_like(stereo, dtype=np.float64)
    cur = stereo.astype(np.float64)
    for k in range(1, taps + 1):
        cur = lp(cur.T, tone, 1).T * feedback
        cur = cur[:, ::-1]  # swap channels each pass: the repeats bounce left and right
        shift = d * k
        if shift >= len(out):
            break
        out[shift:] += cur[: len(out) - shift]
    return out.astype(np.float32)


def reverb(stereo: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Convolve a stereo signal with an IR. The result is longer than the input (the tail)."""
    return np.stack([fftconvolve(stereo[:, c], ir[:, c]) for c in (0, 1)], axis=1)


# --- quirky / sample-flavoured voices (EarthBound-style oddballs) -----------------------------
def honky(m: float, dur: float) -> np.ndarray:
    """A slightly out-of-tune upright piano: two detuned FM/pluck strings per note."""
    f, n = hz(m), _len(min(dur, 1.0), 0.2)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (1.0, 1.0075):  # the second string is flat-ish: that saloon wobble
        out += np.sin(2 * np.pi * f * det * t + 1.4 * np.exp(-t * 9) * np.sin(2 * np.pi * f * det * t))
        out += 0.3 * np.sin(2 * np.pi * f * 2 * det * t) * np.exp(-t * 6)
    out += 0.2 * hp(noise(n, 21), 3000) * np.exp(-t * 80)
    return out * np.exp(-t * 3.2) * 0.5


def toy_piano(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 0.5), 0.15)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.7 * np.sin(2 * np.pi * f * 4.1 * t) * np.exp(-t * 14)
           + 0.45 * np.sin(2 * np.pi * f * 6.7 * t) * np.exp(-t * 22))
    return sig * np.exp(-t * 9) * 0.85


def kazoo(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.08)
    t = np.arange(n) / SR
    vib = 1 + 0.012 * np.sin(2 * np.pi * 6.2 * t) * np.minimum(1, t / 0.2)
    buzz = osc("pulse25", f * vib, n) + 0.5 * osc("square", f * vib * 1.01, n)
    nasal = bp(buzz, 900, 2800) * 2.2 + lp(buzz, 600) * 0.5
    return np.tanh(nasal * 1.4) * adsr(n, 0.02, 0.1, 0.8, 0.07) * 0.7


def accordion(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.12)
    t = np.arange(n) / SR
    bellows = 1 + 0.12 * np.sin(2 * np.pi * 4.2 * t)
    reeds = osc("saw", f * 0.998, n) + osc("square", f * 1.003, n, 0.3) * 0.7 + osc("saw", f * 2.004, n) * 0.25
    return lp(reeds, 3000) * bellows * adsr(n, 0.05, 0.1, 0.85, 0.1) * 0.6


def tuba(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 0.45), 0.08)
    sig = osc("square", f, n) * 0.6 + osc("saw", f * 0.998, n) * 0.5
    return lp(sig, 620) * adsr(n, 0.018, 0.12, 0.7, 0.07) * 1.1


def fuzz_guitar(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.1)
    t = np.arange(n) / SR
    raw = osc("saw", f, n) + 0.6 * osc("square", f * 2.003, n)
    wah = 500 + 1800 * (0.5 + 0.5 * np.sin(2 * np.pi * 2.2 * t))  # a lazy wah-pedal rock
    out = np.zeros(n)
    blocks = 8
    for i in range(blocks):
        lo, hi = i * n // blocks, (i + 1) * n // blocks
        out[lo:hi] = bp(raw, max(120, float(wah[lo:hi].mean()) * 0.6), float(wah[lo:hi].mean()) * 1.8)[lo:hi]
    return np.tanh(out * 3.2) * adsr(n, 0.005, 0.08, 0.8, 0.08) * 0.55


def vibes(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 1.2), 0.3)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 9)
    return sig * (1 + 0.35 * np.sin(2 * np.pi * 5.5 * t)) * np.exp(-t * 2.4) * 0.8


def whistle(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.1)
    t = np.arange(n) / SR
    vib = 1 + 0.01 * np.sin(2 * np.pi * 5.8 * t) * np.minimum(1, np.maximum(0, t - 0.1) / 0.2)
    ph = np.cumsum(f * vib) / SR
    sig = np.sin(2 * np.pi * ph) + 0.05 * hp(noise(n, 31), 3000)
    return sig * adsr(n, 0.05, 0.05, 0.9, 0.1) * 0.65


def rubber_bass(m: float, dur: float) -> np.ndarray:
    """A bouncy bass whose pitch squirts down onto the note."""
    f, n = hz(m), _len(min(dur, 0.45), 0.08)
    t = np.arange(n) / SR
    fi = f * (1 + 0.5 * np.exp(-t * 38))
    sig = np.sin(2 * np.pi * np.cumsum(fi) / SR) + 0.35 * np.sin(4 * np.pi * np.cumsum(fi) / SR) * np.exp(-t * 8)
    return sig * np.exp(-t * 3.5) * 1.1


def organ(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.06)
    t = np.arange(n) / SR
    sig = sum(a * np.sin(2 * np.pi * f * r * t) for r, a in ((0.5, .5), (1, 1), (2, .8), (3, .4), (4, .3), (6, .15)))
    sig *= 1 + 0.06 * np.sin(2 * np.pi * 6.6 * t)
    return sig * adsr(n, 0.012, 0.05, 0.9, 0.05) * 0.35


INSTRUMENTS.update({
    "honky": honky, "toy_piano": toy_piano, "kazoo": kazoo, "accordion": accordion, "tuba": tuba,
    "fuzz": fuzz_guitar, "vibes": vibes, "whistle": whistle, "rubber_bass": rubber_bass, "organ": organ,
})


def cowbell() -> np.ndarray:
    t = np.arange(int(0.22 * SR)) / SR
    sig = np.sign(np.sin(2 * np.pi * 560 * t)) + np.sign(np.sin(2 * np.pi * 845 * t))
    return bp(sig, 500, 3000) * np.exp(-t * 17) * 0.45


def woodblock() -> np.ndarray:
    t = np.arange(int(0.12 * SR)) / SR
    return (np.sin(2 * np.pi * 880 * t) + 0.5 * np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 55) * 0.7


def triangle() -> np.ndarray:
    t = np.arange(int(1.0 * SR)) / SR
    return (np.sin(2 * np.pi * 2800 * t) + 0.4 * np.sin(2 * np.pi * 5600 * t)) * np.exp(-t * 5) * 0.3


def boing() -> np.ndarray:
    t = np.arange(int(0.45 * SR)) / SR
    f = 180 + 260 * np.sin(2 * np.pi * 7 * t) * np.exp(-t * 6) + 70 * np.exp(-t * 3)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.7


def rim() -> np.ndarray:
    t = np.arange(int(0.08 * SR)) / SR
    return (np.sin(2 * np.pi * 1700 * t) * 0.6 + hp(noise(len(t), 41), 2500) * 0.5) * np.exp(-t * 80)


DRUMS.update({"cowbell": cowbell, "wood": woodblock, "triangle": triangle, "boing": boing, "rim": rim})

from k8ssmash.audio import orchestra  # noqa: E402,F401  (registers the lifelike voices)

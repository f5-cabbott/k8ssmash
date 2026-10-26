"""More lifelike voices for the soundtrack: piano, plucked strings (physical model), horn, woodwinds, sax, bowed
strings with bow noise, glockenspiel and orchestra stabs. Registered into instruments.INSTRUMENTS on import."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, lfilter, resample_poly, sosfilt

from k8ssmash.audio import instruments as I
from k8ssmash.audio.instruments import SR, _len, adsr, bp, hp, hz, lp, noise, osc


def _vibrato(n: int, rate: float, depth: float, delay: float, ramp: float, seed: int = 0) -> np.ndarray:
    t = np.arange(n) / SR
    onset = np.clip((t - delay) / ramp, 0, 1)
    wobble = 1 + 0.12 * np.sin(2 * np.pi * 0.37 * t + seed)  # a human vibrato never holds one rate or depth
    return 1 + depth * onset * np.sin(2 * np.pi * rate * wobble * t + seed)


def _formants(x: np.ndarray, peaks: tuple[tuple[float, float, float], ...], dry: float = 0.25) -> np.ndarray:
    out = x * dry
    for fc, width, gain in peaks:
        out = out + gain * bp(x, max(60.0, fc - width), fc + width, 2)
    return out


# --- struck and plucked -----------------------------------------------------------------------
def piano(m: float, dur: float) -> np.ndarray:
    """Three slightly detuned, slightly stretched strings per note, a hammer thump and pitch-dependent decay."""
    f, n = hz(m), _len(min(dur, 3.0), 0.5)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    stretch = 0.00012 * (m / 40.0) ** 2
    base_decay = 1.1 + (m - 40) * 0.035
    for detune in (-1.6, 0.0, 1.9):  # cents: the unison strings beat against each other
        fs = f * 2 ** (detune / 1200)
        for k in range(1, 22):
            fk = fs * k * np.sqrt(1 + stretch * k * k)
            if fk > 11000:
                break
            amp = (1.0 / k ** 0.95) * (1.0 if k < 9 else 0.6) * (0.55 + 0.45 * np.cos(np.pi * k * 0.12) ** 2)
            sig += amp * np.sin(2 * np.pi * fk * t) * np.exp(-t * (base_decay + 0.55 * k * (1 + (m - 40) / 60)))
    thump = lp(noise(n, int(m)), 900) * np.exp(-t * 90) * 0.5 + hp(noise(n, 7), 3000) * np.exp(-t * 220) * 0.12
    sig = (sig / 3.2 + thump) * adsr(n, 0.001, 0.02, 1.0, 0.18)
    return lp(sig, min(9000, 2400 + f * 8)) * 1.1


def _karplus(f: float, n: int, damping: float, bright: float, seed: int) -> np.ndarray:
    """Karplus-Strong at 4x rate (fine tuning), then decimated back down."""
    up = 4
    period = SR * up / f
    ni = int(period - 0.5)
    frac = period - 0.5 - ni
    a = np.zeros(ni + 2)
    a[0] = 1.0
    a[ni] = -damping * 0.5 * (1 - frac)
    a[ni + 1] = -damping * 0.5
    burst = noise(int(period) + 2, seed)
    burst = sosfilt(butter(1, bright * 0.18 / up * 2.0, "low", output="sos"), burst)  # softer burst = duller pluck
    x = np.zeros(n * up)
    x[: len(burst)] = burst
    y = lfilter([1.0], a, x)
    return resample_poly(y, 1, up)[:n]


def pizz(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 0.7), 0.15)
    t = np.arange(n) / SR
    sig = _karplus(f, n, 0.985, 0.8, int(m) + 1)
    sig = sig / (np.abs(sig).max() or 1)
    sig += 0.08 * hp(noise(n, 3), 2000) * np.exp(-t * 160)  # the snap of the string on the fingerboard
    return lp(sig, 4200) * np.exp(-t * 5.5) * 0.9


def nylon(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 1.6), 0.2)
    t = np.arange(n) / SR
    sig = _karplus(f, n, 0.9965, 0.55, int(m) + 17)
    sig = sig / (np.abs(sig).max() or 1)
    body = _formants(sig, ((110, 40, 0.5), (210, 60, 0.35), (2400, 700, 0.12)), dry=0.8)  # the hollow wooden body
    return body * adsr(n, 0.001, 0.05, 1.0, 0.08) * np.exp(-t * 1.1) * 0.9


def bass_pluck(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 1.0), 0.1)
    t = np.arange(n) / SR
    sig = _karplus(f, n, 0.9985, 0.35, int(m) + 31)
    sig = sig / (np.abs(sig).max() or 1)
    sig = lp(sig, 1400) + 0.4 * np.sin(2 * np.pi * f * t) * np.exp(-t * 3)
    return sig * adsr(n, 0.002, 0.05, 1.0, 0.07) * np.exp(-t * 1.8) * 0.9


def glock(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(max(dur, 0.5), 0.9)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.5) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
           + 0.3 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 11))
    sig += 0.1 * hp(noise(n, 5), 4000) * np.exp(-t * 200)
    return sig * 0.6


# --- bowed and blown --------------------------------------------------------------------------
def strings(m: float, dur: float) -> np.ndarray:
    """A string section: eight players, each with their own vibrato, entrance and bow noise."""
    f, n = hz(m), _len(dur, 0.4)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    rng = np.random.default_rng(int(m) * 7 + 1)
    for v in range(8):
        cents = rng.uniform(-11, 11)
        vib = _vibrato(n, rng.uniform(4.7, 5.8), rng.uniform(0.0025, 0.0045), rng.uniform(0.15, 0.4), 0.5, rng.uniform(0, 6))
        late = int(rng.uniform(0, 0.03) * SR)  # players do not all start on the same sample
        voice = osc("saw", f * 2 ** (cents / 1200) * vib, n, rng.uniform(0, 1))
        sig += np.roll(voice, late) * (1.0 if v < 6 else 0.6)
    sig /= 6.0
    bow = lp(sig, min(5200, f * 7 + 900))  # the sound brightens as the bow digs in, then settles
    soft = lp(sig, min(2200, f * 3 + 500))
    open_ = adsr(n, 0.25, 0.4, 0.55, 0.3)
    sig = soft * (1 - open_) + bow * open_
    sig += 0.045 * bp(noise(n, 11), 2500, 6500) * np.exp(-t * 6)  # rosin
    return sig * adsr(n, 0.11, 0.2, 0.84, 0.3)


def horn(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.2)
    sig = osc("saw", f * _vibrato(n, 5.0, 0.002, 0.3, 0.4), n) * 0.7 + osc("sine", f, n) * 0.5
    swell = adsr(n, 0.12, 0.3, 0.6, 0.1)
    sig = lp(sig, 520 + 0.0 * f) * (1 - swell) + lp(sig, min(2600, f * 5 + 500)) * swell
    sig = _formants(sig, ((480, 160, 0.5), (1200, 300, 0.2)), dry=0.8)
    return sig * adsr(n, 0.05, 0.12, 0.85, 0.16) * 0.8


def clarinet(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.1)
    t = np.arange(n) / SR
    ph = np.cumsum(f * _vibrato(n, 5.2, 0.003, 0.25, 0.4)) / SR
    sig = sum((1.0 / k ** 1.05) * np.sin(2 * np.pi * ph * k) for k in range(1, 16, 2) if f * k < 9000)
    sig += 0.03 * bp(noise(n, 5), 1000, 4000) * np.minimum(1, t * 30)
    sig = lp(sig, 2600)
    return sig * adsr(n, 0.035, 0.08, 0.85, 0.09) * 0.8


def oboe(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.1)
    ph = np.cumsum(f * _vibrato(n, 5.6, 0.0035, 0.2, 0.4)) / SR
    sig = np.zeros(n)
    for k in range(1, 22):
        fk = f * k
        if fk > 8000:
            break
        sig += (np.exp(-0.5 * ((fk - 1250) / 650) ** 2) + 0.35 / k) * np.sin(2 * np.pi * ph * k)
    sig += 0.04 * bp(noise(n, 8), 1500, 5000)
    return lp(sig, 3600) * adsr(n, 0.04, 0.1, 0.85, 0.1) * 0.45


def sax(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.12)
    t = np.arange(n) / SR
    sig = osc("saw", f * _vibrato(n, 5.4, 0.004, 0.25, 0.5), n) * 0.8
    sig = _formants(sig, ((900, 250, 0.7), (1800, 400, 0.35)), dry=0.45)
    breath = 0.07 * bp(noise(n, 13), 900, 4500) * (0.5 + 0.5 * np.exp(-t * 9))
    return lp(sig + breath, 4200) * adsr(n, 0.03, 0.1, 0.82, 0.12) * 0.55


def synth_brass(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(dur, 0.1)
    sig = osc("saw", f * 0.996, n) + osc("saw", f * 1.005, n) + osc("saw", f * 2.0, n) * 0.25
    sweep = adsr(n, 0.06, 0.25, 0.3, 0.1)
    sig = lp(sig, 700) * (1 - sweep) + lp(sig, min(5000, f * 9)) * sweep
    return sig * adsr(n, 0.015, 0.1, 0.85, 0.1) * 0.5


def orch_hit(m: float, dur: float) -> np.ndarray:
    """The classic 16-bit orchestra stab: stacked octaves and fifths, a quick bloom and a hard cutoff."""
    f, n = hz(m), _len(0.55, 0.3)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for ratio, g in ((1, 1.0), (1.5, 0.7), (2, 0.8), (3, 0.5), (4, 0.35)):
        sig += osc("saw", f * ratio * 0.998, n) * g + osc("saw", f * ratio * 1.003, n) * g
    sig = lp(sig, min(6000, f * 10 + 800)) * np.exp(-t * 5)
    return sig * adsr(n, 0.004, 0.05, 0.6, 0.12) * 0.28


# --- AWE64 / EMU8000-flavoured voices: the lush, chorused General MIDI sound of late-90s sound cards ------------
def _cho(x: np.ndarray, depth: float = 0.003, rate: float = 0.5, mix: float = 0.6) -> np.ndarray:
    """Thicken a mono voice with the card's built-in chorus (mono in, mono out)."""
    return I.chorus(x, depth=depth, rate=rate, mix=mix).mean(axis=1)


def emu_pad(m: float, dur: float) -> np.ndarray:
    """A 'halo' pad: detuned saws and a triangle, a filter that slowly opens, then a deep chorus."""
    f, n = hz(m), _len(dur, 0.9)
    sig = sum(osc("saw", f * 2 ** (c / 1200), n, ph) for c, ph in ((-9, 0.0), (-3, 0.3), (4, 0.6), (10, 0.85))) / 4
    sig += osc("tri", f * 2.0, n) * 0.18 + osc("sine", f * 0.5, n) * 0.2
    open_ = adsr(n, 0.9, 0.5, 0.7, 0.4)
    sig = lp(sig, min(1500, f * 3)) * (1 - open_) + lp(sig, min(3800, f * 6 + 800)) * open_
    return _cho(sig * adsr(n, 0.5, 0.4, 0.85, 0.8), 0.004, 0.35, 0.8) * 0.7


def emu_strings(m: float, dur: float) -> np.ndarray:
    """String-machine strings: a smooth, slow-bowed saw ensemble, very wide."""
    f, n = hz(m), _len(dur, 0.5)
    sig = sum(osc("saw", f * _vibrato(n, 5.0 + 0.3 * k, 0.002, 0.3, 0.6, k) * 2 ** (c / 1200), n, k * 0.17)
              for k, c in enumerate((-12, -5, 0, 6, 13))) / 5
    sig = lp(sig, min(3400, f * 5 + 700))
    return _cho(sig * adsr(n, 0.28, 0.3, 0.85, 0.45), 0.0035, 0.45, 0.7) * 0.85


def emu_epiano(m: float, dur: float) -> np.ndarray:
    return _cho(I.epiano(m, dur), 0.0025, 0.7, 0.65) * 0.9


def emu_choir(m: float, dur: float) -> np.ndarray:
    return _cho(I.choir(m, dur), 0.003, 0.4, 0.7) * 0.9


def emu_bass(m: float, dur: float) -> np.ndarray:
    f, n = hz(m), _len(min(dur, 1.2), 0.08)
    t = np.arange(n) / SR
    sig = lp(osc("saw", f, n), 300 + 1400 * np.exp(-t * 9)) * 0.8 + osc("sine", f, n) * 0.6
    return sig * adsr(n, 0.004, 0.1, 0.8, 0.08) * 0.8


I.INSTRUMENTS.update({
    "emu_pad": emu_pad, "emu_strings": emu_strings, "emu_epiano": emu_epiano, "emu_choir": emu_choir,
    "emu_bass": emu_bass,
    "piano": piano, "pizz": pizz, "nylon": nylon, "bass_pluck": bass_pluck, "glock": glock, "strings": strings,
    "horn": horn, "clarinet": clarinet, "oboe": oboe, "sax": sax, "synth_brass": synth_brass, "orch_hit": orch_hit,
})

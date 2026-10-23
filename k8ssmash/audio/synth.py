"""Tiny numpy chiptune synthesizer: oscillators, envelopes, drums, echo. Used offline by build.py."""
from __future__ import annotations

import numpy as np

SR = 44100


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def square(freq: np.ndarray | float, t: np.ndarray, duty: float = 0.5) -> np.ndarray:
    phase = np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    return np.where((phase % 1.0) < duty, 1.0, -1.0)


def triangle(freq: np.ndarray | float, t: np.ndarray) -> np.ndarray:
    phase = np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    return 2 * np.abs(2 * (phase % 1.0) - 1) - 1


def saw(freq: np.ndarray | float, t: np.ndarray) -> np.ndarray:
    phase = np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    return 2 * (phase % 1.0) - 1


def noise(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-1, 1, n)


def adsr(n: int, a: float = 0.005, d: float = 0.05, s: float = 0.7, r: float = 0.05) -> np.ndarray:
    env = np.ones(n)
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    ai, ri = min(ai, n), min(ri, n)
    if ai:
        env[:ai] = np.linspace(0, 1, ai)
    di = min(di, max(0, n - ai))
    if di:
        env[ai:ai + di] = np.linspace(1, s, di)
    env[ai + di:] = s
    if ri:
        env[n - ri:] *= np.linspace(1, 0, ri)
    return env


def lowpass(x: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return x
    return np.convolve(x, np.ones(width) / width, mode="same")


def highpass(x: np.ndarray, width: int) -> np.ndarray:
    return x - lowpass(x, width)


def echo(stereo: np.ndarray, delay_s: float, feedback: float, mix: float) -> np.ndarray:
    d = int(delay_s * SR)
    out = stereo.copy()
    tap = stereo
    for i in range(1, 5):
        shifted = np.zeros_like(stereo)
        shifted[d * i:] = tap[:-d * i] * (feedback ** i)
        # ping-pong the repeats between channels
        out += mix * (shifted[:, ::-1] if i % 2 else shifted)
    return out


def to_int16(stereo: np.ndarray, peak: float = 0.89) -> np.ndarray:
    m = np.max(np.abs(stereo)) or 1.0
    return (stereo / m * peak * 32767).astype(np.int16)


# --- drum voices ------------------------------------------------------------------------------
def kick() -> np.ndarray:
    t = t_axis(0.22)
    f = 150 * np.exp(-t * 28) + 42
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)


def snare(seed: int = 1) -> np.ndarray:
    t = t_axis(0.2)
    return (highpass(noise(len(t), seed), 6) * np.exp(-t * 22) * 0.9
            + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.5)


def hat(open_: bool = False, seed: int = 2) -> np.ndarray:
    t = t_axis(0.18 if open_ else 0.05)
    return highpass(noise(len(t), seed), 4) * np.exp(-t * (14 if open_ else 70)) * 0.5


# --- sequencing ------------------------------------------------------------------------------
class Mix:
    """Stereo mix bus. Notes are placed in beats at a given tempo."""

    def __init__(self, bpm: float, beats: float, tail: float = 1.0):
        self.bpm = bpm
        self.spb = 60.0 / bpm
        self.loop_len = int(beats * self.spb * SR)
        self.buf = np.zeros((self.loop_len + int(tail * SR), 2))

    def add(self, start_beat: float, wave: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
        i = int(start_beat * self.spb * SR)
        n = min(len(wave), len(self.buf) - i)
        if n <= 0:
            return
        l, r = gain * (1 - max(0.0, pan)), gain * (1 + min(0.0, pan))
        self.buf[i:i + n, 0] += wave[:n] * l
        self.buf[i:i + n, 1] += wave[:n] * r

    def note(self, kind: str, start_beat: float, dur_beats: float, midi: float, gain: float = 0.3,
             pan: float = 0.0, duty: float = 0.5, vibrato: float = 0.0) -> None:
        dur = dur_beats * self.spb
        t = t_axis(dur + 0.06)
        f = midi_hz(midi) * (1 + vibrato * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t * 4))
        osc = {"square": lambda: square(f, t, duty), "tri": lambda: triangle(f, t),
               "saw": lambda: saw(f, t) * 0.8}[kind]()
        env = adsr(len(t), a=0.004, d=0.06, s=0.65, r=0.05)
        self.add(start_beat, osc * env, gain, pan)

    def finish(self, echo_delay_beats: float = 0.75, feedback: float = 0.38, mix: float = 0.35) -> np.ndarray:
        out = echo(self.buf, echo_delay_beats * self.spb, feedback, mix)
        # fold the tail back onto the start so the loop is seamless
        loop = out[:self.loop_len].copy()
        tail = out[self.loop_len:]
        loop[:len(tail)] += tail[:self.loop_len]
        return loop

"""Generate every sound effect and music loop: python -m k8ssmash.audio.build"""
from __future__ import annotations

import random
import subprocess
import wave
from pathlib import Path

import numpy as np

from k8ssmash.audio import synth as S

OUT = Path(__file__).resolve().parents[2] / "assets" / "audio"
SR = S.SR


def write_wav(path: Path, data: np.ndarray) -> None:
    mono = data.ndim == 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1 if mono else 2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def sweep(f0: float, f1: float, dur: float, kind: str = "square", duty: float = 0.5, decay: float = 4.0) -> np.ndarray:
    t = S.t_axis(dur)
    f = np.linspace(f0, f1, len(t))
    wave_ = S.square(f, t, duty) if kind == "square" else S.triangle(f, t)
    return wave_ * np.exp(-t * decay)


def finish_sfx(data: np.ndarray, target_rms: float = 0.16, max_peak: float = 0.8) -> np.ndarray:
    """Fade the edges (no clicks) and level-match so squarey beeps aren't louder than thumps."""
    data = data.astype(float).copy()
    n = min(len(data) // 4, int(0.006 * SR))
    if n:
        data[:n] *= np.linspace(0, 1, n)
        data[-n:] *= np.linspace(1, 0, n)
    data /= np.max(np.abs(data)) or 1.0
    rms = np.sqrt(np.mean(data ** 2)) or 1.0
    return (data * min(max_peak, target_rms / rms) * 32767).astype(np.int16)


def sfx() -> dict[str, np.ndarray]:
    t = S.t_axis
    out: dict[str, np.ndarray] = {}
    out["jump"] = sweep(300, 760, 0.13, duty=0.25, decay=6) * 0.5
    out["djump"] = np.concatenate([sweep(420, 900, 0.08, duty=0.25), sweep(700, 1300, 0.1, duty=0.25)]) * 0.5
    n = int(0.07 * SR)
    out["hit_light"] = (S.highpass(S.noise(n, 3), 5) * np.exp(-t(0.07) * 45) * 0.8
                        + np.sin(2 * np.pi * 220 * t(0.07)) * np.exp(-t(0.07) * 40)) * 0.8
    d = t(0.22)
    out["hit_heavy"] = (S.lowpass(S.noise(len(d), 4), 3) * np.exp(-d * 18) * 0.9
                        + np.sin(2 * np.pi * np.cumsum(120 * np.exp(-d * 12) + 45) / SR) * np.exp(-d * 10) * 1.1)
    d = t(0.25)
    out["shield"] = sum(np.sin(2 * np.pi * f * d) * np.exp(-d * k) for f, k in ((880, 12), (1320, 16), (1760, 20))) * 0.35
    d = t(0.5)
    out["shield_break"] = (S.highpass(S.noise(len(d), 5), 3) * np.exp(-d * 7) * 0.6
                           + sweep(1400, 120, 0.5, decay=5) * 0.5)
    d = t(0.8)
    out["ko"] = (sweep(900, 50, 0.8, duty=0.5, decay=2.2) * 0.6
                 + S.lowpass(S.noise(len(d), 6), 6) * np.exp(-d * 5) * 0.9)
    d = t(0.3)
    whoosh = S.lowpass(S.noise(len(d), 7), 8) * np.sin(np.linspace(0, np.pi, len(d))) ** 1.5
    out["special"] = whoosh * 0.9 + sweep(250, 600, 0.3, "tri", decay=3) * 0.25
    out["pickup"] = np.concatenate([sweep(f, f, 0.07, duty=0.25, decay=3) for f in (523, 659, 784, 1047)]) * 0.5
    out["countdown"] = sweep(660, 660, 0.14, duty=0.5, decay=4) * 0.5
    out["go"] = (sweep(660, 660, 0.4, duty=0.5, decay=3) + sweep(990, 990, 0.4, duty=0.5, decay=3)
                 + sweep(1320, 1320, 0.4, duty=0.25, decay=3)) * 0.3
    out["menu_move"] = sweep(880, 880, 0.04, duty=0.25, decay=8) * 0.45
    out["menu_select"] = np.concatenate([sweep(660, 660, 0.05, duty=0.5), sweep(990, 990, 0.09, duty=0.5)]) * 0.5
    out["join"] = np.concatenate([sweep(f, f, 0.06, "tri", decay=3) for f in (392, 494, 587)]) * 0.7
    d = t(0.35)
    out["counter"] = sum(np.sin(2 * np.pi * f * d) * np.exp(-d * k)
                         for f, k in ((660, 9), (1010, 11), (1580, 14), (2210, 18))) * 0.3
    d = t(0.6)
    out["explosion"] = (S.lowpass(S.noise(len(d), 8), 10) * np.exp(-d * 6) * 1.0
                        + np.sin(2 * np.pi * np.cumsum(90 * np.exp(-d * 9) + 35) / SR) * np.exp(-d * 6))
    return out


# --- music ------------------------------------------------------------------------------------
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]


def scale_note(root: int, mode: list[int], degree: int) -> int:
    return root + mode[degree % 7] + 12 * (degree // 7)


def track(name: str, bpm: int, root: int, mode: list[int], prog: list[int], style: str, seed: int) -> np.ndarray:
    rng = random.Random(seed)
    bars = len(prog)
    m = S.Mix(bpm, bars * 4)
    kick, snare, hat, ohat = S.kick(), S.snare(), S.hat(), S.hat(True)
    motif = [rng.choice([0, 1, 2, 4]) for _ in range(4)]
    for bar, chord_deg in enumerate(prog):
        b0 = bar * 4
        triad = [scale_note(root, mode, chord_deg + k) for k in (0, 2, 4)]
        # bass: driving eighths on the root (octave pattern for energetic styles)
        for i in range(8):
            octave = 12 if (i % 4 == 3 and style != "calm") else 0
            m.note("tri", b0 + i * 0.5, 0.45, triad[0] - 24 + octave, gain=0.36, pan=-0.1)
        # arpeggio / pad
        if style == "calm":
            for k, n in enumerate(triad):
                m.note("tri", b0, 4, n - 12, gain=0.12, pan=0.2 * (k - 1))
        else:
            for i in range(16):
                m.note("square", b0 + i * 0.25, 0.22, triad[i % 3] + 12, gain=0.07, pan=0.35 if i % 2 else -0.35,
                       duty=0.125)
        # lead melody: a 4-note motif transposed by chord, with a varied ending every 4th bar
        for i in range(8):
            if rng.random() < 0.18 and i % 4:
                continue
            deg = chord_deg + motif[i % 4] + (2 if bar % 4 == 3 and i > 4 else 0) + (7 if style == "heroic" and i % 8 > 5 else 0)
            m.note("square", b0 + i * 0.5, 0.45 if i % 2 else 0.7, scale_note(root, mode, deg) + 12,
                   gain=0.2, pan=0.15, duty=0.25 if bar % 2 else 0.5, vibrato=0.004)
        # drums
        for beat in range(4):
            if style == "calm":
                if beat % 2 == 0:
                    m.add(b0 + beat, kick, 0.5)
                if beat % 2 == 1:
                    m.add(b0 + beat, snare, 0.35)
            else:
                if style == "drive" or beat % 2 == 0:
                    m.add(b0 + beat, kick, 0.6)
                if beat % 2 == 1:
                    m.add(b0 + beat, snare, 0.45)
                m.add(b0 + beat + 0.5, ohat if beat == 3 else hat, 0.3)
                if style == "drive":
                    m.add(b0 + beat, hat, 0.18)
    return S.to_int16(m.finish(0.75, 0.36, 0.3), 0.85)


def results_jingle() -> np.ndarray:
    m = S.Mix(132, 12, tail=1.6)
    seq = [(0, .5, 67), (.5, .5, 72), (1, .5, 76), (1.5, 1.5, 79), (3.5, .5, 76), (4, .5, 79), (4.5, 2.5, 84)]
    for st, du, n in seq:
        m.note("square", st, du, n, gain=0.28, duty=0.25, vibrato=0.004)
        m.note("tri", st, du, n - 12, gain=0.25)
    for st, notes in ((1.5, (60, 64, 67)), (4.5, (60, 64, 67, 72))):
        for n in notes:
            m.note("tri", st, 3, n - 12, gain=0.2)
    m.add(0, S.kick(), 0.6)
    m.add(1.5, S.kick(), 0.6)
    m.add(4.5, S.kick(), 0.7)
    m.add(4.5, S.snare(), 0.5)
    out = m.buf
    return S.to_int16(S.echo(out, 0.3, 0.35, 0.3), 0.85)


TRACKS = {
    # name: (bpm, root midi, mode, chord degrees per bar, style, seed)
    "title": (96, 57, MINOR, [0, 5, 3, 4] * 2, "calm", 1),
    "datacenter": (148, 52, MINOR, [0, 0, 5, 4, 0, 0, 5, 6, 3, 3, 5, 4, 0, 5, 6, 4], "drive", 2),
    "controlplane": (136, 55, MAJOR, [0, 4, 5, 3, 0, 4, 5, 3, 1, 4, 0, 5, 3, 4, 0, 4], "heroic", 3),
    "nodepool": (124, 50, MINOR, [0, 5, 2, 6, 0, 5, 3, 4, 0, 5, 2, 6, 3, 4, 0, 0], "drive", 4),
}


def encode_ogg(wav: Path) -> None:
    ogg = wav.with_suffix(".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "4", str(ogg)],
                   check=True)
    wav.unlink()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in sfx().items():
        write_wav(OUT / f"{name}.wav", finish_sfx(np.asarray(data)))
    for name, (bpm, root, mode, prog, style, seed) in TRACKS.items():
        write_wav(OUT / f"{name}.wav", track(name, bpm, root, mode, prog, style, seed))
        encode_ogg(OUT / f"{name}.wav")
    write_wav(OUT / "results.wav", results_jingle())
    encode_ogg(OUT / "results.wav")
    print("audio built:", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()

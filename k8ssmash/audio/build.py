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
    ph = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * ph) * 0.55 + S.triangle(f, t) * 0.3  # rounded: sine + triangle...
    if kind == "square":
        body += S.lowpass(S.square(f, t, duty), 2) * 0.22  # ...with a dusting of edge, not a raw square
    return body * np.exp(-t * decay) * np.minimum(1.0, t / 0.004)


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


def generic_sfx() -> dict[str, np.ndarray]:
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


# --- music, fighter sounds, orchestration ---------------------------------------------------
def encode_ogg(wav: Path) -> None:
    ogg = wav.with_suffix(".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "8", str(ogg)],
                   check=True)
    wav.unlink()


HOT_SONGS = ("datacenter", "controlplane", "nodepool")


def main() -> None:
    from k8ssmash.audio import arranger, songs, sfx

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()  # regenerate cleanly: no stale files from earlier versions
    generic = generic_sfx()
    # fighting-game style fallbacks: swings, meaty impacts and a battle-cry whoosh (a fighter's own sounds replace these)
    generic["attack_light"] = sfx.whoosh(0.14, True, 0.4, 7)
    generic["attack_heavy"] = sfx.mixin(sfx.whoosh(0.26, True, 0.9, 8), sfx.thump(90, 0.2, 12), 0.1, 0.6)
    generic["special"] = sfx.mixin(sfx.whoosh(0.4, True, 1.0, 9), sfx.voice(220, 380, 0.4, "eh", "ah", 0.3), 0.04, 0.8)
    generic["hit_light"] = sfx.punch(0.35)
    generic["hit_heavy"] = sfx.punch(0.92)
    for name, data in generic.items():
        write_wav(OUT / f"{name}.wav", finish_sfx(np.asarray(data), target_rms=0.19))
    for fighter in sfx.VOICES:
        slug = fighter.lower().replace(" ", "_")
        for event in sfx.EVENTS:
            write_wav(OUT / f"{slug}__{event}.wav", finish_sfx(sfx.fighter_sound(fighter, event), target_rms=0.2))
    for name, make in songs.SONGS.items():
        song = make()
        audio = arranger.master(arranger.render(song))
        write_wav(OUT / f"{name}.wav", (audio * 32767).astype(np.int16))
        encode_ogg(OUT / f"{name}.wav")
        print(f"  {name}: {len(audio) / SR:.0f}s")
        if name in HOT_SONGS:  # the final-stock version: a little faster and a step higher, so the tension lifts
            import dataclasses

            hot = dataclasses.replace(song, bpm=song.bpm * 1.1, tonic=song.tonic + 2)
            audio = arranger.master(arranger.render(hot))
            write_wav(OUT / f"{name}_hot.wav", (audio * 32767).astype(np.int16))
            encode_ogg(OUT / f"{name}_hot.wav")
            print(f"  {name}_hot: {len(audio) / SR:.0f}s")
    print("audio built:", len(list(OUT.iterdir())), "files")


if __name__ == "__main__":
    main()

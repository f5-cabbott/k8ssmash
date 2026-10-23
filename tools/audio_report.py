"""Measure rendered music against the reference profile (length, loudness, spectrum, stereo, key fit)."""
import sys
import time

import numpy as np

from k8ssmash.audio import arranger as A
from k8ssmash.audio import songs as S
from k8ssmash.audio import theory as T

SR = 44100


def bands(mono: np.ndarray) -> list[float]:
    N, hop = 4096, 4096
    frames = np.array([mono[i:i + N] * np.hanning(N) for i in range(0, len(mono) - N, hop * 2)])
    spec = np.abs(np.fft.rfft(frames, axis=1))
    f = np.fft.rfftfreq(N, 1 / SR)
    edges = [(0, 100), (100, 300), (300, 1000), (1000, 3000), (3000, 6000), (6000, 22050)]
    tot = spec.sum()
    return [100 * spec[:, (f >= lo) & (f < hi)].sum() / tot for lo, hi in edges] + [float(((spec * f).sum(1) / spec.sum(1)).mean())]


def key_fit(song, events) -> float:
    """Share of lead notes that belong to the song's scale in each section's key (chromatic slips excluded)."""
    scale = set((song.tonic + s) % 12 for s in T.SCALES[song.scale])
    notes = events["lead"]
    if not notes:
        return 1.0
    # allow transposed sections: judge against any of the tonics used
    tonics = {(song.tonic + sec.transpose) % 12 for sec in song.sections}
    ok = 0
    for _, midi, _ in notes:
        for t in tonics:
            sc = {(t + s) % 12 for s in T.SCALES[song.scale]}
            if midi % 12 in sc:
                ok += 1
                break
    return ok / len(notes)


if __name__ == "__main__":
    names = sys.argv[1:] or list(S.SONGS)
    print(f"{'song':13s} {'len':>5s} {'rms':>6s} {'crest':>6s} {'<300Hz':>7s} {'3-6k':>6s} {'6k+':>5s} {'cent':>5s} {'side/mid':>8s} {'keyfit':>6s}")
    print(f"{'(DKC2 ref)':13s} {'108s':>5s} {'0.174':>6s} {'15dB':>6s} {'37.7%':>7s} {'21%':>6s} {'9.8%':>5s} {'2163':>5s} {'0.11':>8s}")
    for n in names:
        song = S.SONGS[n]()
        t0 = time.perf_counter()
        out, ev = A.render(song, return_events=True)
        m = A.master(out)
        mono = m.mean(1)
        b = bands(mono)
        mid, side = m.mean(1), (m[:, 0] - m[:, 1]) / 2
        crest = 20 * np.log10(np.abs(m).max() / np.sqrt((mono ** 2).mean()))
        print(f"{n:13s} {len(m) / SR:4.0f}s {np.sqrt((mono ** 2).mean()):6.3f} {crest:5.1f}d {b[0] + b[1]:6.1f}% {b[4]:5.1f}% {b[5]:4.1f}% {b[6]:5.0f} "
              f"{np.sqrt((side ** 2).mean()) / np.sqrt((mid ** 2).mean()):8.2f} {key_fit(song, ev):6.2f}  ({time.perf_counter() - t0:.0f}s)")

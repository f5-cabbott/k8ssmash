"""The ring announcer: a handful of short, clear lines ("Ready", "Fight!", "Game!", "Pod wins!"...) for the match flow.

The lines are spoken by espeak-ng (build time only, via the optional `espeakng-loader` package, which bundles the
library) and then dressed like an arena PA: a lower voice, gentle compression, a touch of presence and a short slap-back.
If the package is missing the build keeps whatever announcer clips already exist, so the game never depends on it."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve, resample_poly

from k8ssmash.audio import instruments as I

SR = I.SR
NAME_SPEECH = {"Pod": "Pod", "StatefulSet": "Stateful set", "Kubectl": "Kube control", "CronJob": "Cron job",
               "Sidecar": "Sidecar", "Ingress": "Ingress", "Operator": "Operator", "OOMKiller": "O. O. M. Killer"}
LINES = {
    "ann_ready": "Ready?",
    "ann_fight": "Fight!",
    "ann_game": "Game!",
    "ann_final_stock": "Final stock!",
    "ann_p1_wins": "Player one wins!",
    "ann_p2_wins": "Player two wins!",
    "ann_draw": "It's a draw!",
}


def available() -> bool:
    try:
        import espeakng_loader  # noqa: F401
        return True
    except ImportError:
        return False


class _Speaker:
    def __init__(self) -> None:
        import espeakng_loader

        self.lib = ctypes.CDLL(espeakng_loader.get_library_path())
        data = os.path.dirname(espeakng_loader.get_data_path())
        self.lib.espeak_Initialize.restype = ctypes.c_int
        self.rate = self.lib.espeak_Initialize(2, 0, data.encode(), 0)  # synchronous retrieval
        if self.rate <= 0:
            raise RuntimeError("espeak-ng failed to initialise")
        self.chunks: list[np.ndarray] = []
        cb_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

        def on_audio(wav, n, _events):
            if wav and n > 0:
                self.chunks.append(np.ctypeslib.as_array(wav, shape=(n,)).astype(np.float32).copy())
            return 0
        self._cb = cb_type(on_audio)  # keep a reference alive
        self.lib.espeak_SetSynthCallback(self._cb)
        self.lib.espeak_SetVoiceByName(b"en-us")

    def say(self, text: str, rate: int = 135, pitch: int = 30, pitch_range: int = 62) -> np.ndarray:
        self.chunks.clear()
        for param, value in ((1, rate), (2, 100), (3, pitch), (4, pitch_range)):  # rate, volume, pitch, range
            self.lib.espeak_SetParameter(param, value, 0)
        raw = text.encode()
        self.lib.espeak_Synth(raw, len(raw) + 1, 0, 0, 0, 1, None, None)
        self.lib.espeak_Synchronize()
        wave = np.concatenate(self.chunks) / 32768.0 if self.chunks else np.zeros(1)
        return resample_poly(wave, SR, self.rate)


def dress(voice: np.ndarray) -> np.ndarray:
    """Arena-PA treatment: trim, body and presence EQ, compression, then a short slap-back and room."""
    voice = voice - voice.mean()
    keep = np.where(np.abs(voice) > 0.01 * np.abs(voice).max())[0]
    if len(keep):
        voice = voice[max(0, keep[0] - 200): keep[-1] + 1500]
    voice = I.hp(voice, 110) + 0.35 * I.lp(I.hp(voice, 140), 420) + 0.28 * I.bp(voice, 2200, 4600)
    voice = np.tanh(voice * 2.4 / (np.abs(voice).max() or 1.0))  # compression: even loudness from word to word
    echo = np.zeros(len(voice) + int(0.4 * SR))
    echo[: len(voice)] += voice
    d = int(0.085 * SR)
    echo[d: d + len(voice)] += 0.22 * I.lp(voice, 3200)
    ir = I.make_ir(0.7, seed=5, bright=0.35)[:, 0]
    wet = fftconvolve(echo, ir)[: len(echo)]
    out = echo + 0.16 * wet
    fade = int(0.012 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def build(out: Path, write_wav, finish) -> int:
    """Write every announcer clip into `out` using the build's writer; returns how many were made."""
    sp = _Speaker()
    lines = dict(LINES)
    for name, speech in NAME_SPEECH.items():
        lines[f"ann_win_{name.lower()}"] = f"{speech} wins!"
    for key, text in lines.items():
        write_wav(out / f"{key}.wav", finish(dress(sp.say(text)), target_rms=0.2))
    return len(lines)

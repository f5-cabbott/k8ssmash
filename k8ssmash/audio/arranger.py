"""Turns a Song description (sections of chords, layers, meters, instruments) into stereo audio."""
from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field

import numpy as np

from k8ssmash.audio import instruments as I
from k8ssmash.audio import theory as T

SR = I.SR
Chord = T.Chord


@dataclass
class Sec:
    bars: int
    prog: list[Chord]
    meter: str = "4/4"
    layers: tuple[str, ...] = ()
    mel: str = "A"  # same id = same hook, so repeated sections really repeat
    transpose: int = 0
    swing: float = 0.0
    drums: str = ""
    bass: str = ""
    comp: str = ""
    arp: str = ""
    inst: dict = field(default_factory=dict)
    gain: float = 1.0
    busy: float = 0.5
    crash: bool = True


@dataclass
class Song:
    name: str
    bpm: float
    tonic: int  # MIDI note of the tonic in a low octave (bass lives here)
    scale: str
    inst: dict
    sections: list[Sec]
    seed: int = 1
    reverb: float = 2.0
    wet: float = 0.28
    lead_center: int = 69
    mix: dict = field(default_factory=dict)
    loop: bool = True


# (gain, pan, reverb send)
DEFAULT_MIX = {"lead": (1.0, 0.0, 0.32), "counter": (0.55, 0.3, 0.36), "pad": (0.5, 0.0, 0.5),
               "comp": (0.6, -0.25, 0.3), "arp": (0.5, 0.3, 0.42), "bass": (1.25, 0.0, 0.05),
               "drums": (0.85, 0.0, 0.16)}

# --- patterns ---------------------------------------------------------------------------------
BASS = {  # meter -> name -> [(step, kind, dur)]
    "4/4": {
        "pedal": [(0, "r", 14)], "rootfifth": [(0, "r", 8), (8, "5", 8)],
        "drive8": [(i * 2, "8" if i % 4 == 3 else "r", 2) for i in range(8)],
        "funk": [(0, "r", 3), (3, "r", 2), (6, "5", 2), (8, "r", 2), (10, "8", 2), (12, "5", 2), (14, "3", 2)],
        "walk": [(0, "r", 4), (4, "3", 4), (8, "5", 4), (12, "6", 4)],
        "oompah": [(0, "r", 3), (8, "5", 3)], "bounce": [(0, "r", 2), (4, "8", 2), (6, "r", 2), (10, "5", 2), (12, "r", 2)],
    },
    "3/4": {"waltz": [(0, "r", 3)], "oompah": [(0, "r", 3)]},
    "6/8": {"six8": [(0, "r", 5), (6, "5", 5)], "oompah": [(0, "r", 4), (6, "5", 4)]},
    "7/8": {"seven8": [(0, "r", 3), (4, "r", 2), (6, "5", 2), (8, "r", 3), (12, "8", 2)]},
    "5/4": {"five4": [(0, "r", 5), (6, "5", 4), (12, "r", 3), (16, "b7", 3)]},
}
COMP = {
    "4/4": {"off": [(2, 2), (6, 2), (10, 2), (14, 2)], "charleston": [(0, 6), (6, 2)], "hold": [(0, 15)],
            "funk16": [(0, 1), (3, 1), (6, 1), (10, 1), (12, 2)], "oompah": [(4, 3), (12, 3)],
            "stabs": [(0, 2), (6, 2), (10, 2)], "sparse": [(0, 4), (8, 4)]},
    "3/4": {"waltz": [(4, 3), (8, 3)], "oompah": [(4, 3), (8, 3)]},
    "6/8": {"six8": [(3, 2), (9, 2)], "oompah": [(3, 2), (9, 2)]},
    "7/8": {"seven8": [(4, 2), (8, 2), (10, 2)]},
    "5/4": {"five4": [(6, 2), (12, 2), (16, 2)]},
}
DRUMPAT = {
    "calm": {"meter": "4/4", "kick": [0, 10], "snare": [8], "rim": [4, 12], "shaker": list(range(0, 16, 2))},
    "funk": {"meter": "4/4", "kick": [0, 6, 10], "snare": [4, 12], "hat": list(range(0, 16, 2)), "conga_hi": [3, 11],
             "cowbell": [14], "shaker": [1, 5, 9, 13]},
    "drive": {"meter": "4/4", "kick": [0, 4, 8, 12], "snare": [4, 12], "clap": [4, 12], "hat": [2, 6, 10, 14],
              "ohat": [14]},
    "half": {"meter": "4/4", "kick": [0, 11], "snare": [8], "hat": [0, 4, 8, 12], "rim": [14]},
    "heroic": {"meter": "4/4", "kick": [0, 8], "timpani": [0, 8, 14], "snare": [4, 12], "hat": [2, 6, 10, 14]},
    "swing": {"meter": "4/4", "kick": [0, 10], "hat": [0, 4, 6, 8, 12, 14], "rim": [4, 12]},
    "march": {"meter": "4/4", "kick": [0, 8], "snare": [4, 12], "wood": [2, 6, 10, 14], "triangle": [0]},
    "waltz": {"meter": "3/4", "kick": [0], "snare": [4, 8], "hat": [0, 2, 4, 6, 8, 10]},
    "six8": {"meter": "6/8", "kick": [0], "snare": [6], "wood": [0, 3, 6, 9], "hat": [0, 3, 6, 9]},
    "odd78": {"meter": "7/8", "kick": [0, 8], "snare": [4, 10], "wood": [2, 6, 12], "hat": [0, 2, 4, 6, 8, 10, 12]},
    "odd54": {"meter": "5/4", "kick": [0, 12], "snare": [6, 16], "hat": [0, 4, 8, 12, 16], "cowbell": [10]},
    "tag": {"meter": "4/4", "kick": [0], "snare": [0], "crash": [0]},
}
DRUM_PAN = {"hat": 0.35, "ohat": 0.35, "shaker": 0.4, "conga_hi": -0.3, "conga_lo": -0.4, "tom_hi": -0.3,
            "tom_mid": 0.0, "tom_lo": 0.3, "cowbell": 0.25, "wood": -0.35, "rim": -0.2, "triangle": 0.4, "crash": 0.2}
DRUM_VEL = {"hat": 0.55, "ohat": 0.5, "shaker": 0.5, "rim": 0.7, "cowbell": 0.5, "wood": 0.6, "triangle": 0.5,
            "conga_hi": 0.7, "timpani": 0.9, "kick": 1.0, "snare": 0.9, "clap": 0.7, "crash": 0.6}

_inst_gain: dict[str, float] = {}
_note_cache: dict[tuple, np.ndarray] = {}
_drum_cache: dict[str, np.ndarray] = {}


def _gain(inst: str) -> float:
    if inst not in _inst_gain:
        ref = I.INSTRUMENTS[inst](60, 1.0)
        _inst_gain[inst] = 0.2 / max(1e-4, float(np.sqrt((ref ** 2).mean())))
    return _inst_gain[inst]


def _voice(inst: str, midi: int, dur: float) -> np.ndarray:
    key = (inst, midi, round(dur, 2))
    if key not in _note_cache:
        _note_cache[key] = I.INSTRUMENTS[inst](midi, max(0.05, dur)) * _gain(inst)
    return _note_cache[key]


def _drum(name: str) -> np.ndarray:
    if name not in _drum_cache:
        _drum_cache[name] = I.DRUMS[name]()
    return _drum_cache[name]


class Bus:
    def __init__(self, n: int, stereo: bool = False):
        self.buf = np.zeros((n, 2) if stereo else n, dtype=np.float32)

    def add(self, start: int, wave: np.ndarray, gain: float, pan: float = 0.0) -> None:
        if start >= len(self.buf):
            return
        n = min(len(wave), len(self.buf) - start)
        if n <= 0:
            return
        if self.buf.ndim == 1:
            self.buf[start:start + n] += wave[:n] * gain
        else:
            a = (pan + 1) * np.pi / 4
            self.buf[start:start + n, 0] += wave[:n] * gain * np.cos(a)
            self.buf[start:start + n, 1] += wave[:n] * gain * np.sin(a)


def _bass_midi(tonic: int, chord: Chord, kind: str) -> int:
    root = tonic + chord[0]
    off = {"r": 0, "5": 7, "8": 12, "3": 3 if chord[1].startswith("m") or chord[1] == "dim" else 4, "b7": 10, "6": 9}[kind]
    m = root + off
    while m > tonic + 14:
        m -= 12
    return m


def render(song: Song, return_events: bool = False):
    rng_master = random.Random(song.seed)
    scale = T.SCALES[song.scale]
    spstep = 60.0 / song.bpm / 4
    total_steps = sum(sec.bars * T.steps_per_bar(sec.meter) for sec in song.sections)
    n_loop = int(total_steps * spstep * SR)
    tail = int(3.0 * SR)
    buses = {name: Bus(n_loop + tail) for name in ("lead", "counter", "pad", "comp", "arp", "bass")}
    drums = Bus(n_loop + tail, stereo=True)
    mix = {**DEFAULT_MIX, **song.mix}
    melodies: dict[str, list[T.Note]] = {}
    events: dict[str, list] = {k: [] for k in ("lead", "counter", "pad", "comp", "arp", "bass")}

    def at(step: float, swing: float) -> int:
        shifted = step + (swing * 0.66 if int(step) % 4 == 2 else 0.0)
        return int(shifted * spstep * SR)

    cursor = 0
    for si, sec in enumerate(song.sections):
        spb = T.steps_per_bar(sec.meter)
        tonic = song.tonic + sec.transpose
        inst = {**song.inst, **sec.inst}
        bars = [(sec.meter, sec.prog[b % len(sec.prog)]) for b in range(sec.bars)]
        g = sec.gain
        for b, (meter, chord) in enumerate(bars):
            bar0 = cursor + b * spb
            chord_notes = T.chord_midi(tonic, chord, 60)
            # pad: the whole bar
            if "pad" in sec.layers:
                for m in T.chord_midi(tonic, chord, 52):
                    d = spb * spstep
                    buses["pad"].add(at(bar0, 0), _voice(inst["pad"], m, d), mix["pad"][0] * g * 0.55)
                    events["pad"].append((bar0, m))
            # comp
            if "comp" in sec.layers:
                pats = COMP[meter]
                pat = pats.get(sec.comp) or next(iter(pats.values()))
                for s, ln in pat:
                    if s >= spb:
                        continue
                    for m in T.chord_midi(tonic, chord, 55):
                        buses["comp"].add(at(bar0 + s, sec.swing), _voice(inst["comp"], m, ln * spstep),
                                          mix["comp"][0] * g * 0.5, mix["comp"][1])
                    events["comp"].append((bar0 + s, chord))
            # arp
            if "arp" in sec.layers:
                tones = T.chord_midi(tonic, chord, 64)
                tones = tones + [tones[0] + 12]
                pattern = sec.arp or "up"
                spacing = 2 if pattern in ("up", "broken") else 1
                order = {"up": [0, 1, 2, 3], "broken": [0, 2, 1, 3], "updown": [0, 1, 2, 3, 2, 1]}[pattern]
                for k, s in enumerate(range(0, spb, spacing)):
                    m = tones[order[k % len(order)] % len(tones)]
                    buses["arp"].add(at(bar0 + s, sec.swing), _voice(inst["arp"], m, spacing * spstep * 1.5),
                                     mix["arp"][0] * g * (0.9 if k % 2 == 0 else 0.65), mix["arp"][1] * (1 if k % 2 else -1))
            # bass
            if "bass" in sec.layers:
                pats = BASS[meter]
                pat = pats.get(sec.bass) or next(iter(pats.values()))
                for s, kind, ln in pat:
                    if s >= spb:
                        continue
                    m = _bass_midi(tonic, chord, kind) - 12
                    buses["bass"].add(at(bar0 + s, sec.swing), _voice(inst["bass"], m, ln * spstep * 0.95),
                                      mix["bass"][0] * g * 0.8)
                    events["bass"].append((bar0 + s, m))
            # drums
            if "drums" in sec.layers:
                dp = DRUMPAT.get(sec.drums or "calm")
                if dp and dp["meter"] == meter:
                    for dname, steps in dp.items():
                        if dname == "meter":
                            continue
                        for s in steps:
                            if s >= spb or (dname == "crash" and not (b == 0 and sec.crash)):
                                continue
                            vel = DRUM_VEL.get(dname, 0.8) * (1.0 if s % 4 == 0 else 0.8) * g
                            drums.add(at(bar0 + s, sec.swing), _drum(dname), mix["drums"][0] * vel, DRUM_PAN.get(dname, 0.0))
                    if sec.crash and b == 0 and si > 0 and "crash" not in dp:
                        drums.add(at(bar0, 0), _drum("crash"), mix["drums"][0] * 0.45, 0.2)
                    if b == sec.bars - 1 and meter == "4/4" and sec.drums not in ("tag",):  # a little fill into the next section
                        for k, name in enumerate(("tom_hi", "tom_mid", "tom_lo", "snare")):
                            drums.add(at(bar0 + 12 + k, 0), _drum(name), mix["drums"][0] * 0.7, DRUM_PAN.get(name, 0.0))
        # lead + counter-melody share one generated line so repeats are exact
        if "lead" in sec.layers or "counter" in sec.layers:
            key = f"{si if sec.mel == '' else sec.mel}|{sec.transpose}|{sec.bars}|{sec.meter}"
            if key not in melodies:
                rng = random.Random(zlib.crc32(f"{song.seed}:{key}".encode()))
                melodies[key] = T.melody(rng, tonic, scale, bars, song.lead_center + sec.transpose, busy=sec.busy)
            for note in melodies[key]:
                start = at(cursor + note.step, sec.swing)
                if "lead" in sec.layers:
                    buses["lead"].add(start, _voice(inst["lead"], note.midi, note.dur * spstep),
                                      mix["lead"][0] * g * note.vel, mix["lead"][1])
                    events["lead"].append((cursor + note.step, note.midi, note.dur))
                if "counter" in sec.layers and note.dur >= 2:
                    idx = T.nearest_index(tonic, scale, note.midi)
                    low = T.scale_note(tonic, scale, idx - 2)
                    buses["counter"].add(start, _voice(inst["counter"], low, note.dur * spstep),
                                         mix["counter"][0] * g * note.vel * 0.8, mix["counter"][1])
                    events["counter"].append((cursor + note.step, low, note.dur))
        cursor += sec.bars * spb

    # --- mix: dry + convolution reverb, then master ------------------------------------------
    ir = I.make_ir(song.reverb, seed=song.seed)
    dry = np.zeros((n_loop + tail, 2), dtype=np.float32)
    send = np.zeros_like(dry)
    for name, bus in buses.items():
        gain, pan, rv = mix[name]
        a = (pan + 1) * np.pi / 4
        dry[:, 0] += bus.buf * np.cos(a)
        dry[:, 1] += bus.buf * np.sin(a)
        send[:, 0] += bus.buf * rv * np.cos(a)
        send[:, 1] += bus.buf * rv * np.sin(a)
    dry += drums.buf
    send += drums.buf * mix["drums"][2]
    wet = I.reverb(send, ir)[: n_loop + tail]
    out = dry + wet * song.wet * 2.2
    out = out[: n_loop + tail].copy()
    if song.loop:
        out[:tail] += out[n_loop:n_loop + tail]  # fold the reverb tail back onto the start so it loops
        out = out[:n_loop]
    out = I.lp(out.T, 15500).T
    # master EQ: weightier low end and a bright presence band, like a commercial 16-bit-era master
    out = out + 0.62 * I.lp(out.T, 170).T + 0.85 * I.bp(out.T, 2800, 6800).T + 0.35 * I.hp(out.T, 7000).T
    # keep the image mostly centred (the space comes from the reverb), narrowing the sides
    mid, side = (out[:, 0] + out[:, 1]) / 2, (out[:, 0] - out[:, 1]) / 2
    out = np.stack([mid + side * 0.5, mid - side * 0.5], axis=1)
    out = np.tanh(out * 1.1) / 1.1
    return (out, events) if return_events else out


def master(stereo: np.ndarray, target_rms: float = 0.10, peak: float = 0.85) -> np.ndarray:
    mono = stereo.mean(axis=1)
    rms = float(np.sqrt((mono ** 2).mean())) or 1.0
    out = stereo * (target_rms / rms)
    m = float(np.abs(out).max())
    if m > peak:  # soft-limit rather than clip
        out = np.tanh(out / peak) * peak
    return out

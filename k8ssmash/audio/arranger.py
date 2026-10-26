"""Turns a Song description (sections of chords, layers, meters, instruments) into stereo audio."""
from __future__ import annotations

import itertools
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
    double: str = ""  # an instrument doubling the lead an octave down, for weight
    harm: str = ""  # an instrument shadowing the lead in parallel thirds below
    line: tuple = ()  # an explicit lead line [(step, length in steps, midi)] used instead of a generated melody
    orn: float = 0.14  # chance a longer lead note gets a grace note (and long ones a trill)


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
    emu: float = 0.0  # 0..1: how much of the lush, chorused AWE64 / EMU8000 sound-card sheen to add


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
    """A mono or stereo accumulation buffer; stereo buses place every note at its own pan position."""

    def __init__(self, n: int, stereo: bool = False):
        self.buf = np.zeros((n, 2) if stereo else n, dtype=np.float32)

    def add(self, start: int, wave: np.ndarray, gain: float, pan: float = 0.0) -> None:
        if start >= len(self.buf):
            return
        start = max(0, start)
        n = min(len(wave), len(self.buf) - start)
        if n <= 0:
            return
        if self.buf.ndim == 1:
            self.buf[start:start + n] += wave[:n] * gain
        else:
            a = (max(-1.0, min(1.0, pan)) + 1) * np.pi / 4
            self.buf[start:start + n, 0] += wave[:n] * gain * np.cos(a)
            self.buf[start:start + n, 1] += wave[:n] * gain * np.sin(a)


def voice_lead(tonic: int, chord: Chord, prev: list[int] | None, lo: int, hi: int) -> list[int]:
    """Four chord tones placed as close as possible to the previous chord's notes, so chords glide instead of jumping."""
    pcs = [(tonic + chord[0] + i) % 12 for i in T.CHORDS[chord[1]]][:4]
    while len(pcs) < 4:
        pcs.append(pcs[len(pcs) - 2] if len(pcs) > 2 else pcs[0])
    if prev is None:
        base = T.chord_midi(tonic, chord, lo + 5)
        while len(base) < 4:
            base.append(base[0] + 12)
        return sorted(base[:4])
    best, best_cost = None, 1e9
    for perm in itertools.permutations(pcs):
        notes, cost = [], 0
        for pc, old in zip(perm, prev):
            options = [m for m in range(lo, hi + 1) if m % 12 == pc]
            m = min(options, key=lambda x: abs(x - old))
            notes.append(m)
            cost += abs(m - old)
        if len(set(notes)) == 4 and cost < best_cost:
            best, best_cost = notes, cost
    return sorted(best or prev)


def _bass_midi(tonic: int, chord: Chord, kind: str) -> int:
    root = tonic + chord[0]
    off = {"r": 0, "5": 7, "8": 12, "3": 3 if chord[1].startswith("m") or chord[1] == "dim" else 4, "b7": 10, "6": 9}[kind]
    m = root + off
    while m > tonic + 14:
        m -= 12
    return m


_APPROACH_PATTERNS = ("bounce", "funk", "walk", "drive8", "rootfifth", "oompah")
_GHOST_DRUMS = ("funk", "half", "drive", "swing")


def render(song: Song, return_events: bool = False):
    rng_master = random.Random(song.seed)
    human = random.Random(song.seed * 31 + 7)  # the same "performance" every build
    scale = T.SCALES[song.scale]
    spstep = 60.0 / song.bpm / 4
    total_steps = sum(sec.bars * T.steps_per_bar(sec.meter) for sec in song.sections)
    n_loop = int(total_steps * spstep * SR)
    tail = int(3.0 * SR)
    layer_names = ("lead", "counter", "pad", "comp", "arp", "bass", "double", "harm")
    buses = {name: Bus(n_loop + tail, stereo=True) for name in layer_names}
    drums = Bus(n_loop + tail, stereo=True)
    mix = {**DEFAULT_MIX, **song.mix}
    mix.setdefault("double", (0.5, -0.15, 0.3))
    mix.setdefault("harm", (0.5, 0.2, 0.34))
    melodies: dict[str, list[T.Note]] = {}
    events: dict[str, list] = {k: [] for k in ("lead", "counter", "pad", "comp", "arp", "bass")}

    def at(step: float, swing: float, loose: float = 0.0045) -> int:
        """Sample position of a step: swing applied, then a few milliseconds of human looseness."""
        shifted = step + (swing * 0.66 if int(step) % 4 == 2 else 0.0)
        jitter = max(-0.012, min(0.012, human.gauss(0, loose))) if loose else 0.0
        return max(0, int(shifted * spstep * SR + jitter * SR))

    def vel(base: float, spread: float = 0.08) -> float:
        return base * (1 + human.uniform(-spread, spread))

    comp_prev: list[int] | None = None
    pad_prev: list[int] | None = None
    cursor = 0
    for si, sec in enumerate(song.sections):
        spb = T.steps_per_bar(sec.meter)
        tonic = song.tonic + sec.transpose
        inst = {**song.inst, **sec.inst}
        bars = [(sec.meter, sec.prog[b % len(sec.prog)]) for b in range(sec.bars)]
        g = sec.gain
        nxt_first = (song.sections[si + 1] if si + 1 < len(song.sections) else song.sections[0]).prog[0]
        for b, (meter, chord) in enumerate(bars):
            bar0 = cursor + b * spb
            swell = 1.0 + 0.12 * (b / max(1, sec.bars - 1) - 0.5)  # a gentle crescendo through each section
            # pad: open voicing, spread across the stereo field, gliding from chord to chord
            if "pad" in sec.layers:
                pad_prev = voice_lead(tonic, chord, pad_prev, 47, 68)
                d = spb * spstep
                for k, m in enumerate(pad_prev):
                    buses["pad"].add(at(bar0, 0, 0.0), _voice(inst["pad"], m, d), mix["pad"][0] * g * 0.5 * swell,
                                     mix["pad"][1] + (-0.45, -0.15, 0.15, 0.45)[k])
                    events["pad"].append((bar0, m))
            # comp: voice-led chords, a touch of strum between the notes
            if "comp" in sec.layers:
                pats = COMP[meter]
                pat = pats.get(sec.comp) or next(iter(pats.values()))
                comp_prev = voice_lead(tonic, chord, comp_prev, 52, 76)
                for s_, ln in pat:
                    if s_ >= spb:
                        continue
                    hit = vel(1.0 if s_ % 4 == 0 else 0.82, 0.1)
                    for k, m in enumerate(comp_prev):
                        buses["comp"].add(at(bar0 + s_, sec.swing) + int(k * 0.004 * SR), _voice(inst["comp"], m, ln * spstep),
                                          mix["comp"][0] * g * 0.5 * hit * swell, mix["comp"][1] + (k - 1.5) * 0.12)
                    events["comp"].append((bar0 + s_, chord))
            # arp
            if "arp" in sec.layers:
                tones = T.chord_midi(tonic, chord, 64)
                tones = tones + [tones[0] + 12]
                pattern = sec.arp or "up"
                spacing = 2 if pattern in ("up", "broken") else 1
                order = {"up": [0, 1, 2, 3], "broken": [0, 2, 1, 3], "updown": [0, 1, 2, 3, 2, 1]}[pattern]
                for k, s_ in enumerate(range(0, spb, spacing)):
                    m = tones[order[k % len(order)] % len(tones)]
                    buses["arp"].add(at(bar0 + s_, sec.swing), _voice(inst["arp"], m, spacing * spstep * 1.5),
                                     mix["arp"][0] * g * vel(0.9 if k % 2 == 0 else 0.65, 0.12), mix["arp"][1] * (1 if k % 2 else -1))
            # bass: the pattern, with the last note of the bar often walking up or down into the next chord
            if "bass" in sec.layers:
                pats = BASS[meter]
                pat = pats.get(sec.bass) or next(iter(pats.values()))
                nxt = bars[b + 1][1] if b + 1 < len(bars) else nxt_first
                for ni, (s_, kind, ln) in enumerate(pat):
                    if s_ >= spb:
                        continue
                    m = _bass_midi(tonic, chord, kind) - 12
                    if (sec.bass in _APPROACH_PATTERNS and ni == len(pat) - 1 and spb - s_ <= 5 and human.random() < 0.6):
                        target = _bass_midi(tonic, nxt, "r") - 12
                        m = target + human.choice([-1, -1, 1, -2])
                    buses["bass"].add(at(bar0 + s_, sec.swing, 0.003), _voice(inst["bass"], m, ln * spstep * 0.95),
                                      mix["bass"][0] * g * 0.8 * vel(1.0 if s_ % 4 == 0 else 0.88, 0.07))
                    events["bass"].append((bar0 + s_, m))
            # drums: accented hats, ghost snares and a small fill every fourth bar
            if "drums" in sec.layers:
                dp = DRUMPAT.get(sec.drums or "calm")
                if dp and dp["meter"] == meter:
                    fill = meter == "4/4" and b % 4 == 3 and b != sec.bars - 1 and sec.drums != "tag"
                    for dname, steps in dp.items():
                        if dname == "meter":
                            continue
                        for s_ in steps:
                            if s_ >= spb or (dname == "crash" and not (b == 0 and sec.crash)):
                                continue
                            if fill and s_ >= 12 and dname in ("hat", "ohat", "shaker", "kick"):
                                continue  # make room for the fill
                            accent = 1.0 if s_ % 4 == 0 else 0.82 if s_ % 2 == 0 else 0.55
                            if dname in ("kick", "snare", "clap", "timpani", "crash"):
                                accent = 1.0 if s_ % 4 == 0 else 0.85
                            v = DRUM_VEL.get(dname, 0.8) * accent * g * vel(1.0, 0.08)
                            drums.add(at(bar0 + s_, sec.swing, 0.002), _drum(dname), mix["drums"][0] * v, DRUM_PAN.get(dname, 0.0))
                    if sec.drums in _GHOST_DRUMS and meter == "4/4":
                        for gs in (7, 15, 3):
                            if human.random() < 0.38 and not (fill and gs >= 12):
                                drums.add(at(bar0 + gs, sec.swing, 0.002), _drum("snare"), mix["drums"][0] * 0.2 * g,
                                          DRUM_PAN.get("snare", 0.0))
                    if sec.crash and b == 0 and si > 0 and "crash" not in dp:
                        drums.add(at(bar0, 0, 0.0), _drum("crash"), mix["drums"][0] * 0.45, 0.2)
                    if fill:  # a quick snare run
                        for k, vv in zip((12, 13, 14, 15), (0.3, 0.45, 0.6, 0.85)):
                            drums.add(at(bar0 + k, 0, 0.002), _drum("snare"), mix["drums"][0] * vv * g, 0.0)
                    if b == sec.bars - 1 and meter == "4/4" and sec.drums not in ("tag",):  # a bigger fill into the next section
                        for k, name in enumerate(("tom_hi", "tom_mid", "tom_lo", "snare")):
                            drums.add(at(bar0 + 12 + k, 0, 0.002), _drum(name), mix["drums"][0] * 0.7, DRUM_PAN.get(name, 0.0))
        # lead + counter-melody share one generated line so repeats are exact
        if {"lead", "counter"} & set(sec.layers):
            key = f"{si if sec.mel == '' else sec.mel}|{sec.transpose}|{sec.bars}|{sec.meter}"
            if sec.line:
                key = f"line{si}"
                melodies[key] = [T.Note(st, ln * 0.96, midi, 1.0 if st % 4 == 0 else 0.88) for st, ln, midi in sec.line]
            elif key not in melodies:
                rng = random.Random(zlib.crc32(f"{song.seed}:{key}".encode()))
                melodies[key] = T.melody(rng, tonic, scale, bars, song.lead_center + sec.transpose, busy=sec.busy)
            notes = melodies[key]
            for ni, note in enumerate(notes):
                start = at(cursor + note.step, sec.swing)
                bar_i = min(sec.bars - 1, int(note.step // spb))
                swell = 1.0 + 0.12 * (bar_i / max(1, sec.bars - 1) - 0.5)
                orn = random.Random(zlib.crc32(f"{song.seed}:{key}:{note.step}".encode()))
                idx = T.nearest_index(tonic, scale, note.midi)
                dur_steps = note.dur
                trill = note.dur >= 8 and orn.random() < sec.orn * 1.5
                if "lead" in sec.layers:
                    if trill:
                        dur_steps = note.dur * 0.45
                    buses["lead"].add(start, _voice(inst["lead"], note.midi, dur_steps * spstep),
                                      mix["lead"][0] * g * note.vel * swell * vel(1.0, 0.06), mix["lead"][1])
                    events["lead"].append((cursor + note.step, note.midi, note.dur))
                    if trill:  # alternate with the note above for the rest of the held note
                        upper = T.scale_note(tonic, scale, idx + 1)
                        k = int(note.dur * 0.45)
                        while k < int(note.dur) - 1:
                            m = upper if (k - int(note.dur * 0.45)) % 2 == 0 else note.midi
                            buses["lead"].add(at(cursor + note.step + k, sec.swing), _voice(inst["lead"], m, spstep * 1.1),
                                              mix["lead"][0] * g * 0.7 * swell, mix["lead"][1])
                            k += 1
                    elif note.dur >= 3 and note.step % 4 == 0 and orn.random() < sec.orn:  # a grace note leaning in
                        grace = T.scale_note(tonic, scale, idx + 1)
                        buses["lead"].add(max(0, start - int(0.55 * spstep * SR)), _voice(inst["lead"], grace, 0.6 * spstep),
                                          mix["lead"][0] * g * 0.5 * swell, mix["lead"][1])
                    if sec.double:
                        buses["double"].add(start, _voice(sec.double, note.midi - 12, note.dur * spstep),
                                            mix["double"][0] * g * note.vel * 0.7, mix["double"][1])
                    if sec.harm and note.dur >= 1.5:
                        low = T.scale_note(tonic, scale, idx - 2)
                        buses["harm"].add(start + int(0.006 * SR), _voice(sec.harm, low, note.dur * spstep),
                                          mix["harm"][0] * g * note.vel * 0.8, mix["harm"][1])
                if "counter" in sec.layers:
                    if note.dur >= 2:
                        low = T.scale_note(tonic, scale, idx - 5)
                        buses["counter"].add(start + int(0.004 * SR), _voice(inst["counter"], low, note.dur * spstep),
                                             mix["counter"][0] * g * note.vel * 0.8 * swell, mix["counter"][1])
                        events["counter"].append((cursor + note.step, low, note.dur))
                    if note.dur >= 8:  # the counter-voice answers while the lead holds
                        direction = 1 if orn.random() < 0.5 else -1
                        base = idx - 3
                        for k in range(3):
                            m = T.scale_note(tonic, scale, base + direction * k)
                            s_ = note.dur - 4 + k * 1.3
                            buses["counter"].add(at(cursor + note.step + s_, sec.swing),
                                                 _voice(inst["counter"], m, 1.4 * spstep),
                                                 mix["counter"][0] * g * 0.7 * swell, mix["counter"][1])
        cursor += sec.bars * spb

    # --- mix: dry + convolution reverb, then master ------------------------------------------
    ir = I.make_ir(song.reverb, seed=song.seed)
    size = n_loop + tail
    dry = np.zeros((size, 2), dtype=np.float32)
    send = np.zeros_like(dry)
    for name, bus in buses.items():
        rv = mix[name][2]
        dry += bus.buf
        send += bus.buf * rv
    dry += drums.buf
    send += drums.buf * mix["drums"][2]
    wet = I.reverb(send, ir)[:size]
    # the console-style ping-pong echo on the melodic voices, timed to a dotted eighth note
    echo_in = np.zeros_like(dry)
    for name in ("lead", "counter", "arp", "harm"):
        echo_in += buses[name].buf
    echo = I.echo(echo_in, spstep * 3, feedback=0.45, tone=2800.0)
    out = dry + wet * song.wet * 2.2 * (1 + 0.6 * song.emu) + echo * 0.5
    out = out[:size].copy()
    if song.loop:
        out[:tail] += out[n_loop:n_loop + tail]  # fold the reverb tail back onto the start so it loops
        out = out[:n_loop]
    out = I.chorus(out, mix=0.35 + 0.4 * song.emu)  # ensemble shimmer across the whole mix (deeper on sound-card songs)
    out = I.lp(out.T, 12500).T
    # warm master: a full low end, a gentle low-mid body, and presence kept soft so nothing sounds buzzy or "chippy"
    out = out + 0.5 * I.lp(out.T, 150).T + 0.22 * I.bp(out.T, 250, 900).T + 0.2 * I.bp(out.T, 3000, 6500).T
    mid, side = (out[:, 0] + out[:, 1]) / 2, (out[:, 0] - out[:, 1]) / 2
    out = np.stack([mid + side * 1.0, mid - side * 1.0], axis=1)  # full stereo width
    out = np.tanh(out * 1.25) / 1.25  # soft saturation glues the mix like tape
    return (out, events) if return_events else out


def master(stereo: np.ndarray, target_rms: float = 0.10, peak: float = 0.85) -> np.ndarray:
    mono = stereo.mean(axis=1)
    rms = float(np.sqrt((mono ** 2).mean())) or 1.0
    out = stereo * (target_rms / rms)
    m = float(np.abs(out).max())
    if m > peak:  # soft-limit rather than clip
        out = np.tanh(out / peak) * peak
    return out

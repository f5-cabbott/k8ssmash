"""Small music-theory toolkit: scales, chords, meters and a phrase-aware melody generator."""
from __future__ import annotations

import random
from dataclasses import dataclass

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11],
}
CHORDS = {
    "maj": [0, 4, 7], "min": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11],
    "dim": [0, 3, 6], "sus": [0, 5, 7], "6": [0, 4, 7, 9], "9": [0, 4, 7, 10, 14], "m9": [0, 3, 7, 10, 14],
    "m6": [0, 3, 7, 9], "aug": [0, 4, 8], "5": [0, 7],
}
Chord = tuple[int, str]  # (semitones above the tonic, quality)

# Where the beats group inside a bar, in sixteenth-note steps. Odd meters are what make it quirky.
METERS: dict[str, list[int]] = {
    "4/4": [4, 4, 4, 4], "3/4": [4, 4, 4], "6/8": [6, 6], "7/8": [4, 4, 6], "5/4": [12, 8], "2/4": [4, 4],
    "5/8": [6, 4],
}


def steps_per_bar(meter: str) -> int:
    return sum(METERS[meter])


def groups(meter: str) -> list[int]:
    return METERS[meter]


def chord_midi(tonic: int, chord: Chord, octave_base: int = 60, spread: int = 0) -> list[int]:
    """Chord tones as MIDI notes, closed voicing starting at octave_base."""
    off, quality = chord
    notes = [tonic + off + i for i in CHORDS[quality]]
    notes = [octave_base + ((n - octave_base) % 12) + 12 * (1 if i >= 3 and spread else 0)
             for i, n in enumerate(notes)]
    return sorted(notes)


def chord_pcs(tonic: int, chord: Chord) -> set[int]:
    return {(tonic + chord[0] + i) % 12 for i in CHORDS[chord[1]]}


def scale_note(tonic: int, scale: list[int], idx: int) -> int:
    octave, deg = divmod(idx, len(scale))
    return tonic + 12 * octave + scale[deg]


def nearest_index(tonic: int, scale: list[int], midi: float) -> int:
    best = min(range(-14, 28), key=lambda i: abs(scale_note(tonic, scale, i) - midi))
    return best


@dataclass
class Note:
    step: float  # start, in sixteenth steps from the start of the section
    dur: float  # in sixteenth steps
    midi: int
    vel: float = 1.0


_GROUP_PATTERNS = {
    2: [[(0, 2)], [(0, 1), (1, 1)]],
    4: [[(0, 4)], [(0, 2), (2, 2)], [(0, 3), (3, 1)], [(0, 1), (1, 1), (2, 2)], [(0, 2), (2, 1), (3, 1)],
        [(1, 3)], [(0, 1), (2, 2)]],
    6: [[(0, 6)], [(0, 3), (3, 3)], [(0, 2), (2, 2), (4, 2)], [(0, 4), (4, 2)], [(0, 3), (3, 1), (4, 2)]],
    8: [[(0, 8)], [(0, 4), (4, 4)], [(0, 6), (6, 2)], [(0, 3), (3, 3), (6, 2)], [(0, 2), (2, 2), (4, 4)]],
    12: [[(0, 12)], [(0, 6), (6, 6)], [(0, 4), (4, 4), (8, 4)], [(0, 6), (6, 3), (9, 3)]],
}


def _bar_rhythm(rng: random.Random, meter: str, busy: float) -> list[tuple[int, int]]:
    """Onsets (step, length) for one bar, group by group; `busy` biases toward shorter notes."""
    out: list[tuple[int, int]] = []
    pos = 0
    for g in groups(meter):
        pats = _GROUP_PATTERNS.get(g, [[(0, g)]])
        weights = [1.0 + busy * len(p) * 1.4 - (0.0 if len(p) > 1 else (busy * 1.5)) for p in pats]
        pat = rng.choices(pats, weights=[max(0.1, w) for w in weights])[0]
        out += [(pos + s, ln) for s, ln in pat]
        pos += g
    return out


def _motif_steps(rng: random.Random, n: int = 9) -> list[int]:
    """A hook's pitch contour as scale-step moves. Leaps are answered by a step back the other way, and a repeated note
    now and then gives it the 'da-da-da-DAA' shape that makes a tune stick."""
    out: list[int] = []
    for _ in range(n):
        if out and out[-1] >= 3:
            out.append(rng.choice([-1, -2, -1]))
        elif out and out[-1] <= -3:
            out.append(rng.choice([1, 2, 1]))
        else:
            out.append(rng.choice([-2, -1, -1, 0, 0, 1, 1, 2, 3, -3, 4]))
    return out


def melody(rng: random.Random, tonic: int, scale: list[int], bars: list[tuple[str, Chord]], center: int,
           busy: float = 0.5, chromatic: float = 0.12, rest_prob: float = 0.08) -> list[Note]:
    """Four-bar phrases built like a real tune: bar 1 states a hook, bar 2 answers it as a sequence a step or two away,
    bar 3 reaches higher with a varied ending and bar 4 falls home to a chord tone. Chord tones land on strong beats."""
    notes: list[Note] = []
    cursor = 0
    idx = nearest_index(tonic, scale, center)
    rhythms: list[list[tuple[int, int]]] = []
    steps: list[int] = []
    bar0 = idx
    for bi, (meter, chord) in enumerate(bars):
        spb = steps_per_bar(meter)
        pp = bi % 4
        if pp == 0 or not rhythms:
            rhythms = [_bar_rhythm(rng, meter, busy), _bar_rhythm(rng, meter, busy)]
            steps = _motif_steps(rng)
            idx = max(idx - rng.choice([0, 0, 1]), nearest_index(tonic, scale, center) - 3)  # start near the middle
            bar0 = idx
        if pp in (0, 2):
            rhythm = rhythms[0]
        elif pp == 1:
            rhythm = rhythms[1]
        else:  # the cadence bar: a quick figure, then a held note on the last group
            rhythm = rhythms[0][: max(1, len(rhythms[0]) // 2)]
            last = spb - groups(meter)[-1]
            rhythm = [r for r in rhythm if r[0] < last] + [(last, groups(meter)[-1])]
        if pp == 1:
            idx = bar0 + rng.choice([-1, 1, 1, 2])  # the answer: the same shape, shifted
        elif pp == 2:
            idx = bar0 + rng.choice([2, 3, 3, 4])  # the reach
        elif pp == 3:
            idx = max(bar0 + 1, idx - 1)
        contour = steps if pp < 3 else [-1, -1, -2, -1, 0, -1, -2, -1, -1]
        if pp == 2:  # a varied ending: the last moves of the hook flip direction
            contour = steps[:-3] + [-s if s else 1 for s in steps[-3:]]
        pcs = chord_pcs(tonic, chord)
        for ni, (s, ln) in enumerate(rhythm):
            strong = s in _strong_steps(meter)
            last_note = pp == 3 and ni == len(rhythm) - 1
            if ni > 0 and rng.random() < rest_prob and not last_note:
                continue
            cand = idx + (contour[(ni - 1) % len(contour)] if ni > 0 else 0)
            if last_note:  # land the cadence on the chord root or fifth
                cand = _nearest_chord_tone(tonic, scale, cand, {(tonic + chord[0]) % 12, (tonic + chord[0] + 7) % 12})
            elif strong:
                cand = _nearest_chord_tone(tonic, scale, cand, pcs)
            cand = max(-5, min(15, cand))
            midi = scale_note(tonic, scale, cand)
            idx = cand
            if not strong and ni > 0 and rng.random() < chromatic and ln <= 2:
                midi -= 1  # a chromatic slip that resolves up on the next note
            notes.append(Note(cursor + s, ln * 0.92, midi, 1.0 if strong else 0.82))
        cursor += spb
    return notes


def _strong_steps(meter: str) -> set[int]:
    out, pos = set(), 0
    for g in groups(meter):
        out.add(pos)
        pos += g
    return out


def _nearest_chord_tone(tonic: int, scale: list[int], idx: int, pcs: set[int]) -> int:
    for d in (0, 1, -1, 2, -2, 3, -3):
        if scale_note(tonic, scale, idx + d) % 12 in pcs:
            return idx + d
    return idx

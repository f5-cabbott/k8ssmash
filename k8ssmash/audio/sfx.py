"""Per-fighter sound effects. Every fighter has its own timbre, so you can tell who just jumped,
cast or got hit with your eyes closed: bubbles, foghorns, bleeps, squeaks, servos, portals, phone tones, growls."""
from __future__ import annotations

import numpy as np

from k8ssmash.audio import instruments as I

SR = I.SR
EVENTS = ("jump", "djump", "attack_light", "attack_heavy", "special", "hit_light", "hit_heavy", "ko")

VOICES = {  # fighter -> (timbre, base frequency)
    "Pod": ("bubble", 520), "StatefulSet": ("horn", 130), "Kubectl": ("digital", 880), "Chaos Monkey": ("squeak", 900),
    "Sidecar": ("servo", 300), "Ingress": ("portal", 440), "Operator": ("dtmf", 697), "OOMKiller": ("growl", 62),
}


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def glide(kind: str, f0: float, f1: float, dur: float, curve: float = 1.0, vib: float = 0.0) -> np.ndarray:
    t = _t(dur)
    f = f0 + (f1 - f0) * (t / dur) ** curve
    if vib:
        f = f * (1 + vib * np.sin(2 * np.pi * 9 * t))
    return I.osc(kind, f, len(t))


def decay(x: np.ndarray, k: float) -> np.ndarray:
    return x * np.exp(-np.arange(len(x)) / SR * k)


def cat(*parts: np.ndarray) -> np.ndarray:
    return np.concatenate(parts)


def mixin(base: np.ndarray, extra: np.ndarray, at: float = 0.0, gain: float = 1.0) -> np.ndarray:
    i = int(at * SR)
    out = np.zeros(max(len(base), i + len(extra)))
    out[:len(base)] += base
    out[i:i + len(extra)] += extra * gain
    return out


def thump(f0: float, dur: float, k: float = 12) -> np.ndarray:
    t = _t(dur)
    return np.sin(2 * np.pi * np.cumsum(f0 * (0.35 + 0.65 * np.exp(-t * 30))) / SR) * np.exp(-t * k)


def crunch(dur: float, lo: float = 400, hi: float = 5000, k: float = 25, seed: int = 0) -> np.ndarray:
    n = int(dur * SR)
    return I.bp(I.noise(n, seed), lo, hi) * np.exp(-_t(dur) * k)


def distort(x: np.ndarray, drive: float = 4.0) -> np.ndarray:
    return np.tanh(x * drive) / np.tanh(drive)


def bitcrush(x: np.ndarray, factor: int = 6) -> np.ndarray:
    return np.repeat(x[::factor], factor)[:len(x)]


# --- timbres ----------------------------------------------------------------------------------
def bubble(b: float, ev: str) -> np.ndarray:
    blup = lambda f0, f1, d: decay(glide("sine", f0, f1, d, 0.6), 7)
    if ev == "jump":
        return cat(blup(b * 0.8, b * 1.7, 0.11), blup(b * 1.1, b * 2.0, 0.07))
    if ev == "djump":
        return cat(blup(b, b * 1.9, 0.08), blup(b * 1.3, b * 2.4, 0.08), blup(b * 1.7, b * 3, 0.07))
    if ev == "special":
        return cat(*[blup(b * m, b * m * 1.5, 0.07) for m in (1, 1.25, 1.5, 2, 2.5)])
    if ev == "hit":
        return mixin(blup(b * 1.4, b * 0.4, 0.12), crunch(0.03, 1500, 7000, 60), 0.0, 0.5)
    if ev == "hit_heavy":
        return mixin(thump(110, 0.25, 9), blup(b * 1.6, b * 0.3, 0.2), 0.0, 0.8)
    return cat(*[blup(b * 2.2 - k * 90, b * 1.4 - k * 90, 0.09) for k in range(7)])  # ko: a falling cascade of bubbles


def horn(b: float, ev: str) -> np.ndarray:
    def blast(f0: float, f1: float, d: float, k: float = 5) -> np.ndarray:
        return I.lp(decay(glide("saw", f0, f1, d, 0.5), k) + decay(glide("square", f0 * 1.005, f1, d, 0.5), k) * 0.5, 1800)
    if ev == "jump":
        return blast(b * 2, b * 3, 0.14, 8)
    if ev == "djump":
        return cat(blast(b * 2, b * 2.5, 0.09, 9), blast(b * 3, b * 4, 0.11, 8))
    if ev == "special":
        return mixin(blast(b * 1.5, b * 1.5, 0.6, 3), crunch(0.4, 200, 1200, 7), 0.0, 0.3)
    if ev == "hit":
        return mixin(thump(150, 0.15, 14), blast(b * 4, b * 3, 0.08, 20), 0.0, 0.6)
    if ev == "hit_heavy":
        return mixin(thump(95, 0.3, 8), blast(b * 3, b * 2, 0.22, 10), 0.0, 0.8)
    return blast(b * 3, b * 0.7, 1.0, 2.2)


def digital(b: float, ev: str) -> np.ndarray:
    beep = lambda f, d: decay(I.osc("square", f, int(d * SR)), 14) * 0.7
    if ev == "jump":
        return cat(beep(b, 0.04), beep(b * 1.26, 0.04), beep(b * 1.5, 0.05))
    if ev == "djump":
        return cat(*[beep(b * m, 0.035) for m in (1, 1.26, 1.5, 2)])
    if ev == "special":
        rng = np.random.default_rng(5)
        return cat(*[beep(float(rng.choice([b * 1.5, b * 2, b * 2.5, b * 3, b * 4])), 0.03) for _ in range(9)])
    if ev == "hit":
        return bitcrush(crunch(0.07, 300, 8000, 40, 4) + thump(180, 0.07, 30) * 0.8, 5)
    if ev == "hit_heavy":
        return bitcrush(crunch(0.22, 200, 6000, 14, 6) * 0.8 + thump(110, 0.22, 11), 9)
    return bitcrush(glide("square", b * 2, 70, 0.7, 0.4) * np.exp(-_t(0.7) * 2.5), 12)


def squeak(b: float, ev: str) -> np.ndarray:
    if ev == "jump":
        return decay(glide("sine", b, b * 1.8, 0.12, 0.8, 0.02), 5)
    if ev == "djump":
        return cat(decay(glide("sine", b, b * 1.7, 0.08, 0.8), 6), decay(glide("sine", b * 1.3, b * 2.2, 0.1, 0.8), 6))
    if ev == "special":
        t = _t(0.35)
        return I.lp(I.osc("saw", 110 + 30 * np.sin(2 * np.pi * 25 * t), len(t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 38 * t)), 1500) * np.exp(-t * 3)
    if ev == "hit":
        return decay(glide("sine", b * 1.6, b * 0.9, 0.1, 0.7), 9)
    if ev == "hit_heavy":
        return mixin(decay(glide("sine", b * 2, b * 0.5, 0.25, 0.7, 0.03), 5), thump(120, 0.18, 14), 0.02, 0.6)
    return mixin(glide("sine", b * 2.2, 130, 0.9, 0.5) * np.exp(-_t(0.9) * 2), thump(150, 0.2, 10), 0.85, 0.9)  # slide-whistle fall, then bonk


def servo(b: float, ev: str) -> np.ndarray:
    def whirr(f0: float, f1: float, d: float) -> np.ndarray:
        t = _t(d)
        f = f0 + (f1 - f0) * t / d
        return I.lp(I.osc("saw", f * (1 + 0.04 * np.sin(2 * np.pi * 38 * t)), len(t)), 2400) * np.sin(np.pi * np.minimum(1, t / d)) ** 0.5
    clank = lambda d, k: sum(decay(np.sin(2 * np.pi * f * _t(d)), k) for f in (310, 523, 947, 1430)) * 0.35
    if ev == "jump":
        return whirr(b * 0.6, b * 1.6, 0.14)
    if ev == "djump":
        return cat(whirr(b * 0.7, b * 1.6, 0.08), whirr(b, b * 2.2, 0.1))
    if ev == "special":
        return mixin(whirr(b * 0.5, b * 2.5, 0.32), clank(0.08, 40), 0.3, 0.8)
    if ev == "hit":
        return clank(0.14, 22)
    if ev == "hit_heavy":
        return mixin(clank(0.3, 12), thump(100, 0.22, 10), 0, 0.9)
    return cat(whirr(b * 2, b * 0.3, 0.5), clank(0.3, 14))


def portal(b: float, ev: str) -> np.ndarray:
    def fm(f: float, d: float, k: float, idx: float = 3.0) -> np.ndarray:
        t = _t(d)
        return np.sin(2 * np.pi * f * t + idx * np.exp(-t * 6) * np.sin(2 * np.pi * f * 1.41 * t)) * np.exp(-t * k)
    if ev == "jump":
        return mixin(fm(b * 1.5, 0.25, 9), fm(b * 2.25, 0.2, 11), 0.03, 0.6)
    if ev == "djump":
        return mixin(fm(b * 2, 0.25, 8), mixin(fm(b * 3, 0.22, 8), fm(b * 2.5, 0.2, 9), 0.05, 0.7), 0.0, 0.8)
    if ev == "special":
        t = _t(0.4)
        swirl = I.bp(I.noise(len(t), 3), 400, 4000) * np.sin(np.pi * t / 0.4)
        return mixin(swirl * 0.7, fm(b * 2, 0.35, 5), 0.08, 0.7)
    if ev == "hit":
        return fm(b * 3.2, 0.14, 22, 4)
    if ev == "hit_heavy":
        return mixin(fm(b * 2.4, 0.3, 11, 5), thump(100, 0.2, 10), 0, 0.8)
    t = _t(0.7)
    return mixin(np.sin(2 * np.pi * np.cumsum(b * 0.5 + b * 4 * (t / 0.7) ** 2) / SR) * np.sin(np.pi * t / 0.7) ** 0.4,
                 crunch(0.2, 300, 6000, 10), 0.5, 0.7)


def dtmf(b: float, ev: str) -> np.ndarray:
    def dual(f1: float, f2: float, d: float, k: float = 10) -> np.ndarray:
        t = _t(d)
        return (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t)) * 0.5 * np.exp(-t * k)
    digits = [(697, 1209), (770, 1336), (852, 1477), (941, 1336), (697, 1477), (770, 1209)]
    if ev == "jump":
        return dual(*digits[0], 0.09, 12)
    if ev == "djump":
        return cat(dual(*digits[0], 0.05, 14), dual(*digits[4], 0.07, 12))
    if ev == "special":
        return cat(*[dual(*d, 0.045, 11) for d in digits[:5]])
    if ev == "hit":  # a busy signal's buzz
        return mixin(dual(480, 620, 0.12, 14), crunch(0.05, 1000, 5000, 60), 0.0, 0.3)
    if ev == "hit_heavy":
        return mixin(dual(480, 620, 0.28, 7), thump(110, 0.2, 10), 0, 0.8)
    return cat(*[decay(np.sin(2 * np.pi * f * _t(0.22)), 4) * 0.6 for f in (913, 1371, 1777)])  # the "number disconnected" tri-tone


def growl(b: float, ev: str) -> np.ndarray:
    def rumble(f0: float, f1: float, d: float, k: float) -> np.ndarray:
        t = _t(d)
        sig = I.osc("saw", (f0 + (f1 - f0) * t / d) * (1 + 0.03 * np.sin(2 * np.pi * 31 * t)), len(t))
        return distort(I.lp(sig, 900), 4) * np.exp(-t * k)
    if ev == "jump":
        return rumble(b * 2, b * 4, 0.15, 8)
    if ev == "djump":
        return cat(rumble(b * 2.5, b * 4, 0.09, 10), rumble(b * 3, b * 6, 0.12, 8))
    if ev == "special":
        t = _t(0.45)
        return mixin(I.lp(I.noise(len(t), 2), 2200) * np.sin(np.pi * t / 0.45) ** 1.5 * 0.8, rumble(b * 2, b * 1, 0.45, 5), 0, 0.8)
    if ev == "hit":
        return mixin(thump(90, 0.14, 16), crunch(0.08, 500, 6000, 38) * 0.7, 0, 0.9)
    if ev == "hit_heavy":
        return mixin(thump(60, 0.45, 6), distort(crunch(0.3, 200, 5000, 9) * 1.4, 3), 0, 0.9)
    return mixin(rumble(b * 4, b * 0.7, 1.0, 2.2), crunch(0.9, 150, 3000, 3), 0, 0.5)


# --- fighting-game building blocks ---------------------------------------------------------------
VOWELS = {  # formant frequencies (F1, F2, F3) in Hz
    "ah": (800, 1200, 2800), "eh": (530, 1840, 2480), "oh": (570, 840, 2410), "ee": (270, 2290, 3010),
    "uh": (520, 1190, 2390),
}
# fighter -> (pitch Hz, light vowel, shout vowel, grit 0..1, ring-mod Hz for robot voices, breathiness)
VOX = {
    "Pod": (300, "eh", "ee", 0.1, 0, 0.5), "StatefulSet": (118, "uh", "ah", 0.5, 0, 0.6),
    "Kubectl": (190, "eh", "ah", 0.2, 72, 0.2), "Chaos Monkey": (430, "ee", "oh", 0.1, 0, 0.7),
    "Sidecar": (235, "eh", "ah", 0.25, 0, 0.5), "Ingress": (160, "oh", "ah", 0.3, 0, 0.4),
    "Operator": (335, "eh", "ee", 0.1, 0, 0.5), "OOMKiller": (84, "uh", "oh", 0.9, 0, 0.8),
}


def whoosh(dur: float, rising: bool = True, power: float = 0.6, seed: int = 4) -> np.ndarray:
    """A swing through the air: noise whose brightness sweeps across three bands."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise_ = I.noise(n, seed)
    out = np.zeros(n)
    for lo, hi, peak in ((250, 900, 0.2), (900, 2600, 0.5), (2600, 7000, 0.8)):
        centre = peak if rising else 1 - peak
        weight = np.exp(-((t - centre) / 0.3) ** 2)
        out += I.bp(noise_, lo, hi) * weight * (1.0 if hi < 3000 else 0.6)
    env = np.sin(np.pi * np.clip(t, 0, 1)) ** 1.4
    return out * env * (0.5 + power)


def punch(power: float, seed: int = 1) -> np.ndarray:
    """A layered impact: a sharp crack, a slap, a thump and (for heavy hits) a low boom, like arcade fighters."""
    dur = 0.14 + 0.3 * power
    n = int(dur * SR)
    t = np.arange(n) / SR
    crack = I.hp(I.noise(n, seed), 3000) * np.exp(-t * 700) * 1.0
    slap = I.bp(I.noise(n, seed + 1), 500, 3200) * np.exp(-t * (55 - 25 * power)) * 0.9
    thump = np.sin(2 * np.pi * np.cumsum(60 + 110 * np.exp(-t * 45) + 40 * (1 - power)) / SR) * np.exp(-t * (24 - 12 * power)) * (0.8 + power)
    out = crack * (0.7 + 0.3 * power) + slap + thump
    if power > 0.5:
        boom = np.sin(2 * np.pi * np.cumsum(46 + 40 * np.exp(-t * 20)) / SR) * np.exp(-t * 7) * 1.3
        tail = I.lp(I.noise(n, seed + 2), 900) * np.exp(-t * 10) * 0.7
        out = out + boom * (power - 0.4) + tail * (power - 0.3)
    return out


def voice(pitch: float, end_pitch: float, dur: float, vowel_a: str, vowel_b: str, grit: float = 0.2,
          ring: float = 0.0, breath: float = 0.5, hit: bool = True) -> np.ndarray:
    """A shouted syllable: a glottal buzz gliding in pitch through two vowels' formants, with breath, grit and
    an optional ring-modulator for robot voices."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    f = pitch + (end_pitch - pitch) * t ** 0.8
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 7 * np.arange(n) / SR))
    source = I.osc("saw", f, n) * 0.8 + I.osc("pulse25", f * 1.003, n) * 0.4

    def vowel(name: str) -> np.ndarray:
        out = np.zeros(n)
        for freq, gain in zip(VOWELS[name], (1.0, 0.7, 0.35)):
            out += I.bp(source, freq * 0.88, freq * 1.12, 2) * gain
        return out

    mix = t
    body = I.lp(source, 420) * 0.55  # the chest: a voice keeps its fundamental alongside the formants
    sig = vowel(vowel_a) * (1 - mix) + vowel(vowel_b) * mix + body
    secs = np.arange(n) / SR
    env = np.minimum(1.0, secs / 0.008) * np.exp(-np.maximum(0, secs - dur * 0.45) * (3.5 / dur))
    sig = sig * env
    if hit:  # the "h" of a "HAH!": a burst of breath before the vowel
        puff = I.bp(I.noise(n, 11), 1200, 5200) * np.exp(-secs * 38) * breath * 1.6
        sig = sig + puff
    sig = sig + I.bp(I.noise(n, 12), 900, 4500) * env * breath * 0.25
    if ring:
        sig = sig * (0.45 + 0.55 * np.sin(2 * np.pi * ring * secs))
    if grit:
        sig = np.tanh(sig * (1 + grit * 5)) / np.tanh(1 + grit * 5)
    return sig


def _norm(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    return x / (np.max(np.abs(x)) or 1.0) * peak


def fighter_attack(fighter: str, event: str) -> np.ndarray:
    """A swing plus a battle cry. Both layers are levelled first so the voice leads and the whoosh supports it."""
    pitch, va, vb, grit, ring, breath = VOX[fighter]
    if event == "attack_light":  # a quick "hup!"
        shout = voice(pitch * 1.15, pitch * 0.95, 0.12, va, va, grit, ring, breath)
        return mixin(_norm(whoosh(0.13, True, 0.35, 7), 0.35), _norm(shout, 0.95), 0.0)
    if event == "attack_heavy":  # a committed "HAH!"
        shout = voice(pitch * 1.25, pitch * 0.78, 0.26, va, vb, grit, ring, breath)
        return mixin(_norm(whoosh(0.24, True, 0.8, 8), 0.4), _norm(shout, 1.0), 0.02)
    # special: the big rising shout, with a trace of the fighter's own timbre underneath
    shout = voice(pitch * 0.9, pitch * 1.7, 0.42, va, vb, min(1.0, grit + 0.15), ring, breath)
    cast = mixin(_norm(whoosh(0.38, True, 1.0, 9), 0.45), _norm(shout, 1.0), 0.03)
    return mixin(cast, _norm(fighter_flavor(fighter, "special"), 0.3), 0.0)


def fighter_flavor(fighter: str, event: str) -> np.ndarray:
    timbre, base = VOICES[fighter]
    return TIMBRES[timbre](float(base), event)


TIMBRES = {"bubble": bubble, "horn": horn, "digital": digital, "squeak": squeak, "servo": servo, "portal": portal,
           "dtmf": dtmf, "growl": growl}


def fighter_sound(fighter: str, event: str) -> np.ndarray:
    pitch, va, vb, grit, ring, breath = VOX[fighter]
    if event in ("attack_light", "attack_heavy", "special"):
        return fighter_attack(fighter, event)
    if event in ("hit_light", "hit_heavy"):  # a meaty impact with a hint of the attacker's own character
        power = 0.35 if event == "hit_light" else 0.92
        return mixin(punch(power, seed=len(fighter)), fighter_flavor(fighter, "hit" if event == "hit_light" else event), 0.0, 0.35)
    if event == "ko":  # the timbre's fall plus a long falling scream
        scream = voice(pitch * 2.1, pitch * 0.55, 0.9, vb, va, min(1.0, grit + 0.2), ring, breath * 0.5, hit=False)
        return mixin(_norm(fighter_flavor(fighter, "ko"), 0.6), _norm(scream, 1.0), 0.0)
    return fighter_flavor(fighter, event)

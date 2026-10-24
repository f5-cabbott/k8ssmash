"""The soundtrack. Original compositions in the spirit of quirky 16-bit RPG/platformer scores:
unusual instruments, jazzy chords, odd-meter detours and the occasional hard left turn."""
from __future__ import annotations

from k8ssmash.audio.arranger import Sec, Song

FULL = ("lead", "counter", "pad", "comp", "arp", "bass", "drums")


def splash() -> Song:
    """The title-screen theme: fast, bouncy and cheerful, with a 5/4 detour and a key lift for the last chorus."""
    inst = dict(lead="kazoo", counter="whistle", pad="strings", comp="honky", arp="toy_piano", bass="tuba")
    a = [(0, "maj"), (5, "maj"), (0, "maj"), (7, "7"), (0, "maj"), (9, "min"), (5, "maj"), (7, "7")]
    b = [(5, "maj"), (2, "m7"), (7, "7"), (0, "maj")] * 2
    sw = dict(swing=0.1)
    bounce = dict(comp="oompah", bass="bounce", drums="march")
    secs = [
        Sec(2, [(0, "maj"), (7, "7")], layers=("arp", "drums", "bass"), arp="updown", drums="march", bass="bounce", crash=False, **sw),
        Sec(8, a, layers=("lead", "counter", "comp", "arp", "bass", "drums"), mel="A", arp="broken", **bounce, **sw),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "marimba", "counter": "kazoo", "arp": "steel"}, arp="updown",
            comp="oompah", bass="bounce", drums="funk", gain=1.05, **sw),
        Sec(4, [(0, "maj"), (3, "maj"), (8, "maj"), (7, "7")], meter="5/4", layers=("lead", "comp", "bass", "drums"),
            mel="Z", inst={"lead": "whistle", "comp": "accordion"}, comp="five4", bass="five4", drums="odd54", busy=0.8),
        Sec(8, a, layers=FULL, mel="A", arp="broken", inst={"counter": "steel"}, **bounce, **sw),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "marimba", "counter": "kazoo", "arp": "steel"}, arp="updown",
            comp="oompah", bass="bounce", drums="funk", gain=1.05, **sw),
        Sec(8, a, layers=FULL, mel="A", transpose=2, arp="updown", inst={"lead": "brass", "counter": "kazoo"}, gain=1.1,
            **bounce, **sw),
        Sec(2, [(5, "maj"), (0, "maj")], layers=("arp", "bass", "drums"), arp="up", bass="pedal", drums="tag"),
    ]
    return Song("splash", 150, 55, "major", inst, secs, seed=97, reverb=1.7, wet=0.2, lead_center=76)


def select() -> Song:
    inst = dict(lead="kazoo", counter="honky", pad="organ", comp="fuzz", arp="vibes", bass="bass_slap")
    a = [(0, "9"), (5, "9"), (0, "9"), (10, "maj"), (0, "9"), (5, "9"), (2, "m7"), (7, "7")]
    b = [(5, "maj7"), (4, "m7"), (2, "m7"), (7, "7")] * 2
    groove = dict(comp="funk16", bass="funk", drums="funk", swing=0.12)
    secs = [
        Sec(4, [(0, "9"), (0, "9"), (5, "9"), (0, "9")], layers=("comp", "bass", "drums"), gain=0.9, crash=False, **groove),
        Sec(8, a, layers=("lead", "pad", "comp", "bass", "drums"), mel="A", **groove),
        Sec(8, b, layers=("lead", "counter", "pad", "comp", "bass", "drums"), mel="B",
            inst={"lead": "epiano", "counter": "kazoo", "comp": "organ"}, comp="stabs", bass="bounce", drums="funk", swing=0.12),
        Sec(4, [(0, "7"), (10, "maj"), (0, "7"), (5, "7")], meter="7/8", layers=("lead", "comp", "bass", "drums"),
            mel="Z", comp="seven8", bass="seven8", drums="odd78", busy=0.8, inst={"lead": "whistle"}),
        Sec(8, a, layers=("lead", "counter", "pad", "comp", "bass", "drums"), mel="A", inst={"counter": "epiano"}, **groove),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "epiano", "counter": "kazoo", "comp": "organ"}, comp="stabs",
            bass="bounce", drums="funk", swing=0.12),
        Sec(4, [(0, "9"), (5, "9"), (10, "maj"), (0, "9")], layers=("comp", "bass", "drums", "pad"), crash=False,
            gain=0.95, **groove),
    ]
    return Song("select", 112, 55, "mixolydian", inst, secs, seed=23, reverb=1.5, wet=0.2, lead_center=72)


def datacenter() -> Song:
    inst = dict(lead="lead_synth", counter="strings", pad="pad", comp="fuzz", arp="vibes", bass="bass_synth")
    verse = [(0, "min"), (8, "maj"), (10, "maj"), (7, "7")] * 2
    chorus = [(5, "maj"), (8, "maj"), (0, "min"), (7, "7")] * 2
    drive = dict(bass="drive8", drums="drive", comp="stabs")
    secs = [
        Sec(4, [(0, "min"), (0, "min"), (8, "maj"), (10, "maj")], layers=("comp", "bass", "drums"), gain=0.9, crash=False, **drive),
        Sec(8, verse, layers=("lead", "pad", "arp", "comp", "bass", "drums"), mel="V", arp="broken", **drive),
        Sec(8, chorus, layers=FULL, mel="C", inst={"lead": "brass", "arp": "marimba"}, arp="updown", gain=1.05, **drive),
        Sec(4, [(0, "min"), (3, "maj"), (8, "maj"), (7, "7")], meter="5/4", layers=("lead", "comp", "bass", "drums"),
            mel="Z", inst={"lead": "vibes"}, comp="five4", bass="five4", drums="odd54", busy=0.7),
        Sec(8, [(2, "m7"), (7, "9"), (0, "m7"), (5, "maj7")] * 2, layers=("lead", "pad", "comp", "bass", "drums"),
            mel="S", inst={"lead": "vibes", "comp": "epiano", "bass": "rubber_bass", "pad": "strings"}, swing=0.2,
            drums="half", comp="sparse", bass="bounce"),
        Sec(8, verse, layers=("lead", "counter", "pad", "arp", "comp", "bass", "drums"), mel="V", arp="broken", **drive),
        Sec(8, chorus, layers=FULL, mel="C", inst={"lead": "brass", "arp": "marimba"}, arp="updown", gain=1.08, **drive),
        Sec(4, [(0, "min"), (0, "min"), (7, "7"), (0, "min")], layers=("pad", "bass", "comp"), bass="pedal", comp="hold",
            crash=False, gain=0.8),
    ]
    return Song("datacenter", 138, 45, "minor", inst, secs, seed=37, reverb=1.8, wet=0.22, lead_center=69)


def controlplane() -> Song:
    inst = dict(lead="brass", counter="strings", pad="choir", comp="harp", arp="harp", bass="bass_fretless")
    a = [(0, "maj"), (7, "maj"), (9, "min"), (4, "min"), (5, "maj"), (0, "maj"), (5, "maj"), (7, "7")]
    secs = [
        Sec(4, [(0, "maj"), (5, "maj"), (7, "maj"), (0, "maj")], layers=("pad", "drums"), drums="heroic", gain=0.8, crash=False),
        Sec(8, a, layers=("lead", "counter", "pad", "arp", "bass", "drums"), mel="A", arp="updown", bass="rootfifth", drums="heroic"),
        Sec(8, [(9, "min"), (5, "maj"), (0, "maj"), (7, "maj")] * 2, layers=("lead", "counter", "pad", "arp", "bass", "drums"),
            mel="B", inst={"lead": "flute", "pad": "strings"}, arp="up", bass="rootfifth", drums="heroic"),
        Sec(4, [(0, "maj"), (5, "maj"), (7, "7"), (0, "maj")], meter="6/8", layers=("lead", "comp", "bass", "drums"),
            mel="M", inst={"lead": "kazoo", "comp": "accordion", "bass": "tuba"}, comp="six8", bass="six8", drums="six8"),
        Sec(8, [(5, "maj"), (0, "maj"), (7, "maj"), (9, "min")] * 2, layers=FULL, mel="C", transpose=2,
            inst={"counter": "choir", "pad": "strings", "arp": "harp"}, arp="updown", bass="rootfifth", drums="heroic", gain=1.08),
        Sec(8, a, layers=FULL, mel="A", arp="updown", bass="rootfifth", drums="heroic", gain=1.05),
        Sec(4, [(0, "maj"), (5, "maj"), (7, "sus"), (0, "maj")], layers=("pad", "arp"), arp="up", crash=False, gain=0.85),
    ]
    return Song("controlplane", 124, 50, "major", inst, secs, seed=41, reverb=3.0, wet=0.34, lead_center=74)


def nodepool() -> Song:
    inst = dict(lead="marimba", counter="whistle", pad="strings", comp="accordion", arp="steel", bass="tuba")
    a = [(0, "maj"), (0, "6"), (5, "maj"), (7, "7"), (0, "maj"), (9, "m7"), (2, "m7"), (7, "7")]
    sw = dict(swing=0.14)
    secs = [
        Sec(2, [(0, "maj"), (7, "7")], layers=("arp",), arp="up", crash=False, **sw),
        Sec(8, a, layers=("lead", "counter", "comp", "bass", "drums"), mel="A", comp="oompah", bass="oompah", drums="march", **sw),
        Sec(8, [(5, "maj"), (9, "m7"), (2, "m7"), (7, "7")] * 2, layers=("lead", "counter", "pad", "arp", "comp", "bass", "drums"),
            mel="B", inst={"lead": "steel", "counter": "marimba"}, comp="oompah", bass="oompah", drums="march", arp="broken", **sw),
        Sec(6, [(0, "maj"), (5, "maj"), (0, "maj"), (7, "7"), (0, "maj"), (7, "7")], meter="3/4",
            layers=("lead", "comp", "bass", "drums"), mel="W", inst={"lead": "accordion", "comp": "honky", "bass": "tuba"},
            comp="waltz", bass="waltz", drums="waltz"),
        Sec(8, a, layers=FULL, mel="A", comp="oompah", bass="oompah", drums="march", arp="broken", **sw),
        Sec(8, [(5, "maj"), (9, "m7"), (2, "m7"), (7, "7")] * 2, layers=FULL, mel="B", inst={"lead": "steel", "counter": "marimba"},
            comp="oompah", bass="oompah", drums="march", arp="broken", gain=1.05, **sw),
        Sec(2, [(5, "maj"), (0, "maj")], layers=("arp", "bass"), arp="up", bass="pedal", crash=False),
    ]
    return Song("nodepool", 118, 48, "major", inst, secs, seed=53, reverb=1.7, wet=0.22, lead_center=72)


def training() -> Song:
    inst = dict(lead="vibes", counter="flute", pad="organ", comp="epiano", arp="vibes", bass="bass_fretless")
    sw = dict(swing=0.22)
    a = [(0, "m9"), (5, "9"), (0, "m9"), (5, "9"), (3, "maj7"), (10, "9"), (0, "m9"), (7, "m7")]
    secs = [
        Sec(2, [(0, "m9"), (5, "9")], layers=("comp", "bass"), comp="sparse", bass="walk", crash=False, **sw),
        Sec(8, a, layers=("lead", "pad", "comp", "bass", "drums"), mel="A", comp="sparse", bass="walk", drums="swing", **sw),
        Sec(8, [(5, "maj7"), (4, "m7"), (2, "m7"), (7, "7")] * 2, layers=("lead", "counter", "pad", "comp", "bass", "drums"),
            mel="B", inst={"lead": "flute", "counter": "vibes", "comp": "organ"}, comp="charleston", bass="walk", drums="swing", **sw),
        Sec(8, a, layers=("lead", "counter", "pad", "comp", "bass", "drums"), mel="A", comp="sparse", bass="walk", drums="swing",
            inst={"counter": "epiano"}, **sw),
        Sec(8, [(5, "maj7"), (4, "m7"), (2, "m7"), (7, "7")] * 2, layers=FULL, mel="B", arp="updown",
            inst={"lead": "flute", "counter": "vibes", "comp": "organ"}, comp="charleston", bass="walk", drums="swing", **sw),
        Sec(2, [(0, "m9"), (7, "7")], layers=("comp", "bass"), comp="sparse", bass="walk", crash=False, **sw),
    ]
    return Song("training", 100, 50, "dorian", inst, secs, seed=67, reverb=1.6, wet=0.22, lead_center=69)


def leaderboard() -> Song:
    inst = dict(lead="brass", counter="strings", pad="strings", comp="toy_piano", arp="toy_piano", bass="bass_synth")
    a = [(0, "maj"), (5, "maj"), (7, "maj"), (0, "maj"), (0, "maj"), (9, "min"), (5, "maj"), (7, "7")]
    secs = [
        Sec(2, [(0, "maj"), (5, "maj")], layers=("pad", "drums"), drums="heroic", crash=False, gain=0.9),
        Sec(8, a, layers=("lead", "counter", "pad", "arp", "bass", "drums"), mel="A", arp="up", bass="rootfifth", drums="march"),
        Sec(8, [(5, "maj"), (10, "maj"), (0, "maj"), (7, "7")] * 2, layers=FULL, mel="B",
            inst={"lead": "kazoo", "counter": "brass", "comp": "honky"}, comp="oompah", arp="broken", bass="oompah", drums="march"),
        Sec(8, a, layers=FULL, mel="A", arp="updown", bass="rootfifth", drums="heroic", gain=1.06),
        Sec(8, [(5, "maj"), (10, "maj"), (0, "maj"), (7, "7")] * 2, layers=FULL, mel="B", transpose=2,
            inst={"lead": "brass", "counter": "kazoo", "comp": "honky"}, comp="oompah", arp="updown", bass="oompah",
            drums="heroic", gain=1.08),
        Sec(2, [(5, "maj7"), (0, "maj7")], layers=("pad", "arp"), arp="up", crash=False, gain=0.85),
    ]
    return Song("leaderboard", 108, 46, "major", inst, secs, seed=71, reverb=2.2, wet=0.28, lead_center=70)


def results() -> Song:
    """A short victory sting (plays once)."""
    inst = dict(lead="brass", counter="kazoo", pad="strings", comp="toy_piano", arp="toy_piano", bass="tuba")
    secs = [Sec(4, [(0, "maj"), (5, "maj"), (7, "7"), (0, "maj")], layers=("lead", "counter", "pad", "bass", "drums"),
                mel="V", drums="tag", bass="rootfifth", busy=0.65, gain=1.0)]
    return Song("results", 120, 51, "major", inst, secs, seed=83, reverb=2.4, wet=0.3, lead_center=72, loop=False)


SONGS = {"splash": splash, "select": select, "datacenter": datacenter, "controlplane": controlplane,
         "nodepool": nodepool, "training": training, "leaderboard": leaderboard, "results": results}

"""The soundtrack. Original compositions in the spirit of quirky 16-bit RPG/platformer scores:
unusual instruments, jazzy chords, odd-meter detours and the occasional hard left turn."""
from __future__ import annotations

from k8ssmash.audio.arranger import Sec, Song

FULL = ("lead", "counter", "pad", "comp", "arp", "bass", "drums")


def splash() -> Song:
    """The title-screen theme: fast, bouncy and cheerful, with a 5/4 detour and a key lift for the last chorus."""
    inst = dict(lead="oboe", counter="clarinet", pad="emu_strings", comp="piano", arp="pizz", bass="tuba")
    a = [(0, "maj"), (5, "maj"), (0, "maj"), (7, "7"), (0, "maj"), (9, "min"), (5, "maj"), (7, "7")]
    b = [(5, "maj"), (2, "m7"), (7, "7"), (0, "maj")] * 2
    sw = dict(swing=0.1)
    bounce = dict(comp="oompah", bass="bounce", drums="march")
    secs = [
        Sec(2, [(0, "maj"), (7, "7")], layers=("arp", "drums", "bass"), arp="updown", drums="march", bass="bounce", crash=False, **sw),
        Sec(8, a, layers=("lead", "counter", "comp", "arp", "bass", "drums"), mel="A", arp="broken", **bounce, **sw),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "marimba", "counter": "clarinet", "arp": "steel"}, arp="updown",
            comp="oompah", bass="bounce", drums="funk", gain=1.05, **sw),
        Sec(4, [(0, "maj"), (3, "maj"), (8, "maj"), (7, "7")], meter="5/4", layers=("lead", "comp", "bass", "drums"),
            mel="Z", inst={"lead": "whistle", "comp": "accordion"}, comp="five4", bass="five4", drums="odd54", busy=0.8),
        Sec(8, a, layers=FULL, mel="A", arp="broken", inst={"counter": "steel"}, **bounce, **sw),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "marimba", "counter": "clarinet", "arp": "steel"}, arp="updown",
            comp="oompah", bass="bounce", drums="funk", gain=1.05, **sw),
        Sec(8, a, layers=FULL, mel="A", transpose=2, arp="updown", inst={"lead": "brass", "counter": "horn"}, double="strings", harm="clarinet", gain=1.1,
            **bounce, **sw),
        Sec(2, [(5, "maj"), (0, "maj")], layers=("arp", "bass", "drums"), arp="up", bass="pedal", drums="tag"),
    ]
    return Song("splash", 150, 55, "major", inst, secs, seed=97, reverb=1.7, wet=0.2, lead_center=76, emu=0.3)


def select() -> Song:
    inst = dict(lead="sax", counter="emu_epiano", pad="emu_pad", comp="fuzz", arp="vibes", bass="bass_slap")
    a = [(0, "9"), (5, "9"), (0, "9"), (10, "maj"), (0, "9"), (5, "9"), (2, "m7"), (7, "7")]
    b = [(5, "maj7"), (4, "m7"), (2, "m7"), (7, "7")] * 2
    groove = dict(comp="funk16", bass="funk", drums="funk", swing=0.12)
    secs = [
        Sec(4, [(0, "9"), (0, "9"), (5, "9"), (0, "9")], layers=("comp", "bass", "drums"), gain=0.9, crash=False, **groove),
        Sec(8, a, layers=("lead", "pad", "comp", "bass", "drums"), mel="A", **groove),
        Sec(8, b, layers=("lead", "counter", "pad", "comp", "bass", "drums"), mel="B",
            inst={"lead": "epiano", "counter": "clarinet", "comp": "organ"}, comp="stabs", bass="bounce", drums="funk", swing=0.12),
        Sec(4, [(0, "7"), (10, "maj"), (0, "7"), (5, "7")], meter="7/8", layers=("lead", "comp", "bass", "drums"),
            mel="Z", comp="seven8", bass="seven8", drums="odd78", busy=0.8, inst={"lead": "whistle"}),
        Sec(8, a, layers=("lead", "counter", "pad", "comp", "bass", "drums"), mel="A", inst={"counter": "epiano"}, **groove),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "epiano", "counter": "clarinet", "comp": "organ"}, comp="stabs",
            bass="bounce", drums="funk", swing=0.12),
        Sec(4, [(0, "9"), (5, "9"), (10, "maj"), (0, "9")], layers=("comp", "bass", "drums", "pad"), crash=False,
            gain=0.95, **groove),
    ]
    return Song("select", 112, 55, "mixolydian", inst, secs, seed=23, reverb=1.5, wet=0.2, lead_center=72, emu=0.6)


def datacenter() -> Song:
    inst = dict(lead="lead_synth", counter="strings", pad="emu_pad", comp="fuzz", arp="vibes", bass="bass_synth")
    verse = [(0, "min"), (8, "maj"), (10, "maj"), (7, "7")] * 2
    chorus = [(5, "maj"), (8, "maj"), (0, "min"), (7, "7")] * 2
    drive = dict(bass="drive8", drums="drive", comp="stabs")
    secs = [
        Sec(4, [(0, "min"), (0, "min"), (8, "maj"), (10, "maj")], layers=("comp", "bass", "drums"), gain=0.9, crash=False, **drive),
        Sec(8, verse, layers=("lead", "pad", "arp", "comp", "bass", "drums"), mel="V", arp="broken", **drive),
        Sec(8, chorus, layers=FULL, mel="C", inst={"lead": "brass", "arp": "marimba"}, double="horn", harm="strings", arp="updown", gain=1.05, **drive),
        Sec(4, [(0, "min"), (3, "maj"), (8, "maj"), (7, "7")], meter="5/4", layers=("lead", "comp", "bass", "drums"),
            mel="Z", inst={"lead": "vibes"}, comp="five4", bass="five4", drums="odd54", busy=0.7),
        Sec(8, [(2, "m7"), (7, "9"), (0, "m7"), (5, "maj7")] * 2, layers=("lead", "pad", "comp", "bass", "drums"),
            mel="S", inst={"lead": "vibes", "comp": "epiano", "bass": "rubber_bass", "pad": "strings"}, swing=0.2,
            drums="half", comp="sparse", bass="bounce"),
        Sec(8, verse, layers=("lead", "counter", "pad", "arp", "comp", "bass", "drums"), mel="V", arp="broken", **drive),
        Sec(8, chorus, layers=FULL, mel="C", inst={"lead": "brass", "arp": "marimba"}, double="horn", harm="strings", arp="updown", gain=1.08, **drive),
        Sec(4, [(0, "min"), (0, "min"), (7, "7"), (0, "min")], layers=("pad", "bass", "comp"), bass="pedal", comp="hold",
            crash=False, gain=0.8),
    ]
    return Song("datacenter", 138, 45, "minor", inst, secs, seed=37, reverb=1.8, wet=0.22, lead_center=69, emu=0.3)


def etcd() -> Song:
    """Etcd Vault: slow and mysterious, bells over a choir pad, with a 5/4 detour and a big strings-and-horn finish."""
    inst = dict(lead="glock", counter="oboe", pad="emu_pad", comp="harp", arp="harp", bass="bass_fretless")
    a = [(0, "m7"), (5, "maj"), (10, "maj"), (7, "m7")] * 2
    b = [(3, "maj7"), (10, "maj"), (5, "maj7"), (7, "7")] * 2
    secs = [
        Sec(4, [(0, "m7"), (7, "m7")], layers=("pad", "arp"), arp="updown", crash=False, gain=0.85),
        Sec(8, a, layers=("lead", "pad", "arp", "bass", "drums"), mel="A", arp="broken", bass="rootfifth", drums="calm"),
        Sec(8, b, layers=("lead", "counter", "pad", "comp", "arp", "bass", "drums"), mel="B", inst={"lead": "oboe", "counter": "horn"},
            harm="clarinet", comp="sparse", bass="walk", drums="half", gain=1.05),
        Sec(4, [(0, "m7"), (5, "maj"), (10, "maj"), (7, "7")], meter="5/4", layers=("lead", "comp", "bass", "drums"), mel="Z",
            inst={"lead": "vibes", "comp": "epiano"}, comp="five4", bass="five4", drums="odd54", busy=0.7),
        Sec(8, a, layers=FULL, mel="A", inst={"lead": "horn", "counter": "choir"}, double="strings", arp="updown", bass="rootfifth",
            drums="heroic", gain=1.08),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "brass", "counter": "choir"}, double="horn", harm="oboe", comp="sparse", bass="walk",
            drums="heroic", gain=1.1),
        Sec(4, [(0, "m7"), (5, "maj"), (7, "m7"), (0, "m7")], layers=("pad", "arp", "bass"), arp="up", bass="pedal", crash=False, gain=0.8),
    ]
    return Song("etcd", 96, 50, "dorian", inst, secs, seed=59, reverb=2.8, wet=0.3, lead_center=74, emu=0.4)


def mesh() -> Song:
    """Service Mesh: a driving night-drive synth track with sax, vibes and a swung middle."""
    inst = dict(lead="lead_synth", counter="sax", pad="emu_pad", comp="emu_epiano", arp="marimba", bass="bass_synth")
    verse = [(0, "min"), (8, "maj"), (10, "maj"), (5, "min")] * 2
    chorus = [(8, "maj"), (10, "maj"), (0, "min"), (7, "min")] * 2
    drive = dict(bass="drive8", drums="drive", comp="stabs")
    secs = [
        Sec(4, [(0, "min"), (0, "min"), (8, "maj"), (10, "maj")], layers=("comp", "bass", "drums"), gain=0.9, crash=False, **drive),
        Sec(8, verse, layers=("lead", "pad", "arp", "comp", "bass", "drums"), mel="V", arp="broken", **drive),
        Sec(8, chorus, layers=FULL, mel="C", inst={"lead": "synth_brass", "arp": "vibes"}, double="strings", harm="sax", arp="updown",
            gain=1.06, **drive),
        Sec(8, [(0, "m7"), (5, "m7"), (8, "maj7"), (7, "7")] * 2, layers=("lead", "pad", "comp", "bass", "drums"), mel="S",
            inst={"lead": "sax", "comp": "epiano", "bass": "rubber_bass"}, swing=0.18, drums="half", comp="sparse", bass="bounce"),
        Sec(8, verse, layers=("lead", "counter", "pad", "arp", "comp", "bass", "drums"), mel="V", arp="broken", **drive),
        Sec(8, chorus, layers=FULL, mel="C", inst={"lead": "synth_brass", "arp": "vibes"}, double="strings", harm="sax", arp="updown",
            gain=1.1, **drive),
        Sec(4, [(0, "min"), (0, "min"), (7, "7"), (0, "min")], layers=("pad", "bass", "comp"), bass="pedal", comp="hold", crash=False, gain=0.8),
    ]
    return Song("mesh", 126, 52, "minor", inst, secs, seed=61, reverb=2.0, wet=0.24, lead_center=71, emu=0.5)


def cloud() -> Song:
    """Cloud Native: sunny, bouncy and a little dreamy (lydian), with flutes and glockenspiel over a skipping groove."""
    inst = dict(lead="flute", counter="glock", pad="strings", comp="piano", arp="marimba", bass="bass_pluck")
    a = [(0, "maj"), (2, "maj"), (0, "maj7"), (7, "maj")] * 2
    b = [(4, "m7"), (9, "m7"), (2, "maj"), (7, "maj")] * 2
    sw = dict(swing=0.12)
    skip = dict(comp="charleston", bass="bounce", drums="swing")
    secs = [
        Sec(4, [(0, "maj"), (7, "maj")], layers=("arp", "pad", "bass"), arp="updown", bass="pedal", crash=False, gain=0.85),
        Sec(8, a, layers=("lead", "pad", "arp", "comp", "bass", "drums"), mel="A", arp="broken", **skip, **sw),
        Sec(8, b, layers=("lead", "counter", "pad", "arp", "comp", "bass", "drums"), mel="B", inst={"lead": "oboe", "counter": "flute"},
            arp="updown", **skip, **sw),
        Sec(6, [(0, "maj"), (5, "maj"), (0, "maj"), (7, "7"), (0, "maj"), (7, "7")], meter="3/4", layers=("lead", "comp", "bass", "drums"),
            mel="W", inst={"lead": "clarinet", "comp": "harp"}, comp="waltz", bass="waltz", drums="waltz"),
        Sec(8, a, layers=FULL, mel="A", inst={"lead": "horn", "counter": "glock"}, double="strings", harm="flute", arp="updown", gain=1.06,
            **skip, **sw),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "brass", "counter": "flute", "arp": "vibes"}, double="horn", harm="oboe", arp="broken",
            gain=1.1, **skip, **sw),
        Sec(4, [(0, "maj"), (5, "maj"), (0, "maj7"), (0, "maj")], layers=("pad", "arp", "bass"), arp="up", bass="pedal", crash=False, gain=0.8),
    ]
    return Song("cloud", 116, 53, "lydian", inst, secs, seed=73, reverb=2.2, wet=0.26, lead_center=76, emu=0.35)


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
            inst={"counter": "choir", "pad": "strings", "arp": "harp"}, double="horn", harm="oboe", arp="updown", bass="rootfifth", drums="heroic", gain=1.08),
        Sec(8, a, layers=FULL, mel="A", arp="updown", bass="rootfifth", drums="heroic", gain=1.05),
        Sec(4, [(0, "maj"), (5, "maj"), (7, "sus"), (0, "maj")], layers=("pad", "arp"), arp="up", crash=False, gain=0.85),
    ]
    return Song("controlplane", 124, 50, "major", inst, secs, seed=41, reverb=3.0, wet=0.34, lead_center=74)


def nodepool() -> Song:
    inst = dict(lead="marimba", counter="clarinet", pad="emu_strings", comp="accordion", arp="steel", bass="tuba")
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
    inst = dict(lead="sax", counter="flute", pad="emu_pad", comp="emu_epiano", arp="vibes", bass="bass_fretless")
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
    return Song("training", 100, 50, "dorian", inst, secs, seed=67, reverb=1.6, wet=0.22, lead_center=69, emu=0.6)


def leaderboard() -> Song:
    """Hall of Fame: a bouncy game-show romp with a polka detour and two key lifts to a big finish."""
    inst = dict(lead="clarinet", counter="brass", pad="emu_pad", comp="honky", arp="vibes", bass="rubber_bass")
    a = [(0, "maj"), (0, "6"), (5, "maj"), (5, "min"), (0, "maj"), (9, "m7"), (2, "m7"), (7, "7")]
    b = [(10, "maj"), (0, "maj"), (10, "maj"), (7, "7")] * 2
    sw = dict(swing=0.14)
    funk = dict(bass="funk", drums="funk", comp="stabs")
    secs = [
        Sec(2, [(0, "maj"), (7, "7")], layers=("lead", "pad", "bass", "drums"), mel="F", inst={"lead": "brass"},
            drums="tag", bass="rootfifth", crash=False),
        Sec(8, a, layers=("lead", "counter", "comp", "arp", "bass", "drums"), mel="A", comp="charleston", arp="broken",
            bass="bounce", drums="funk", **sw),
        Sec(8, b, layers=FULL, mel="B", inst={"lead": "vibes", "counter": "horn", "comp": "organ", "arp": "marimba"},
            arp="updown", gain=1.05, **funk, **sw),
        Sec(4, [(0, "maj"), (5, "maj"), (7, "7"), (0, "maj")], meter="6/8", layers=("lead", "comp", "bass", "drums"),
            mel="P", inst={"lead": "whistle", "comp": "accordion", "bass": "tuba"}, comp="six8", bass="six8", drums="six8"),
        Sec(8, a, layers=FULL, mel="A", transpose=2, inst={"lead": "brass", "counter": "horn"}, double="strings", comp="charleston",
            arp="updown", bass="bounce", drums="funk", gain=1.08, **sw),
        Sec(8, b, layers=FULL, mel="B", transpose=2, inst={"lead": "brass", "counter": "horn", "comp": "organ", "arp": "marimba"},
            arp="updown", gain=1.1, **funk, **sw),
        Sec(8, a, layers=FULL, mel="A", transpose=5, inst={"lead": "brass", "counter": "horn", "arp": "steel"}, double="strings", harm="clarinet",
            comp="charleston", arp="updown", bass="bounce", drums="heroic", gain=1.14, **sw),
        Sec(2, [(5, "maj"), (0, "maj")], layers=("lead", "pad", "bass", "drums"), mel="F", transpose=5, inst={"lead": "brass"},
            drums="tag", bass="pedal", crash=True),
    ]
    return Song("leaderboard", 128, 53, "major", inst, secs, seed=71, reverb=1.9, wet=0.24, lead_center=72, emu=0.45)


def results() -> Song:
    """The victory theme (plays once): a brass fanfare, a soaring answer and a big final chord, in the spirit of a
    boss-defeated jingle, with a lush sound-card string bed under it."""
    inst = dict(lead="brass", counter="horn", pad="emu_strings", comp="orch_hit", arp="harp", bass="tuba")
    prog = [(0, "maj"), (0, "maj"), (5, "maj"), (7, "maj"), (0, "maj"), (9, "min"), (5, "maj"), (7, "7"),
            (0, "maj"), (5, "maj"), (7, "maj"), (0, "maj")]
    line = (  # (step, length, midi); a bar is 16 steps
        (0, 2, 67), (2, 2, 67), (4, 2, 67), (6, 10, 72),                          # G G G  C-----
        (16, 2, 76), (18, 2, 74), (20, 2, 72), (22, 2, 74), (24, 8, 76),          # E D C D E--
        (32, 2, 77), (34, 2, 76), (36, 2, 77), (38, 2, 79), (40, 8, 81),          # F E F G A--
        (48, 2, 79), (50, 2, 77), (52, 2, 76), (54, 2, 74), (56, 8, 71),          # G F E D B-- (leaning on the dominant)
        (64, 4, 72), (68, 2, 76), (70, 2, 79), (72, 8, 84),                       # the theme: C E G C^
        (80, 4, 81), (84, 2, 79), (86, 2, 76), (88, 8, 81),                       # A G E A
        (96, 4, 77), (100, 2, 81), (102, 2, 84), (104, 4, 86), (108, 4, 84),      # F A C D C
        (112, 2, 83), (114, 2, 81), (116, 2, 79), (118, 2, 77), (120, 8, 74),     # B A G F D--
        (128, 2, 72), (130, 2, 76), (132, 2, 79), (134, 2, 84), (136, 8, 88),     # rising arpeggio to the top
        (144, 4, 81), (148, 4, 84), (152, 8, 89),
        (160, 2, 86), (162, 2, 83), (164, 2, 79), (166, 2, 83), (168, 8, 86),
        (176, 16, 84),                                                           # the final C
    )
    secs = [Sec(12, prog, layers=("lead", "counter", "pad", "comp", "arp", "bass", "drums"), line=line, double="horn",
                harm="strings", comp="sparse", arp="updown", bass="rootfifth", drums="heroic", gain=1.05, orn=0.0,
                inst={"counter": "emu_choir"})]
    return Song("results", 138, 48, "major", inst, secs, seed=83, reverb=2.6, wet=0.32, lead_center=72, loop=False, emu=0.5)


SONGS = {"splash": splash, "select": select, "datacenter": datacenter, "controlplane": controlplane,
         "nodepool": nodepool, "etcd": etcd, "mesh": mesh, "cloud": cloud, "training": training, "leaderboard": leaderboard, "results": results}

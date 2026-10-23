"""Round-robin CPU-vs-CPU balance check.  python tools/balance.py [rounds] [seed]

Plays every fighter pair from both sides `rounds` times and prints win rates, match length and how
many matches ended on the clock. The CPU is simple, so treat this as a smoke alarm for outliers
(someone winning ~90% or ~10%), not as a substitute for people playing.
"""
import itertools
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import MATCH_SECONDS, READY_FRAMES, Battle
from k8ssmash.stage import STAGES

rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
app = App(Config())
app.input.poll = lambda: None
fighters = roster()
names = [f.name for f in fighters]
wins = {n: 0 for n in names}
games = {n: 0 for n in names}
head2head = {(a, b): 0 for a in names for b in names}
lengths, timeouts, draws = [], 0, 0

n = 0
for r in range(rounds):
    for i, j in itertools.permutations(range(len(fighters)), 2):
        n += 1
        stage = STAGES[(i + j + r) % len(STAGES)]()
        b = Battle(app, [fighters[i], fighters[j]], stage=stage, human=[False, False], items=True, demo=True)
        for slot, ai in b.ais.items():
            ai.rng = random.Random(seed * 100003 + n * 10 + slot)
        b.spawner.rng = random.Random(seed + n)
        for _ in range((MATCH_SECONDS + 5) * 60 + READY_FRAMES):
            b.update()
            if b.winner is not None:
                break
        games[names[i]] += 1
        games[names[j]] += 1
        lengths.append((READY_FRAMES + MATCH_SECONDS * 60 - b.time_left) / 60 if b.time_left > 0 else MATCH_SECONDS)
        if b.time_left <= 0:
            timeouts += 1
        if b.winner in (0, 1):
            w, l = (names[i], names[j]) if b.winner == 0 else (names[j], names[i])
            wins[w] += 1
            head2head[(w, l)] += 1
        else:
            draws += 1

print(f"{n} matches, avg length {sum(lengths) / len(lengths):.0f}s, {timeouts} ended on the clock, {draws} draws\n")
print(f"{'fighter':14s} win%   (wins/games)")
for name in sorted(names, key=lambda k: -wins[k] / games[k]):
    rate = 100 * wins[name] / games[name]
    flag = "  <-- check" if rate > 75 or rate < 25 else ""
    print(f"{name:14s} {rate:4.0f}%   ({wins[name]}/{games[name]}){flag}")

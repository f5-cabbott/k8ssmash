"""Frame-time benchmark for the Pi smoke test: a CPU-vs-CPU match with items on a real display.

    .venv/bin/python tools/benchmark.py [seconds]      (exit code 1 if the average frame misses 60 fps)
"""
import statistics
import sys
import time

import pygame

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.stage import STAGES

seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
app = App(Config.load())
print(f"driver={pygame.display.get_driver()} gpu_scaled={app.display.gpu} output={app.display.output_size}")
r = roster()
times: list[float] = []
for i, make in enumerate(STAGES):
    battle = Battle(app, [r[i % 8], r[(i + 3) % 8]], stage=make(), human=[False, False], items=True)
    app.set_scene(battle)
    battle.frame = READY_FRAMES
    end = time.perf_counter() + seconds / len(STAGES)
    while time.perf_counter() < end:
        t0 = time.perf_counter()
        pygame.event.pump()
        app.step()
        battle.draw(app.display.canvas)
        app.display.present()
        times.append(time.perf_counter() - t0)
avg = statistics.mean(times) * 1000
p99 = sorted(times)[int(len(times) * 0.99)] * 1000
print(f"{len(times)} frames: avg {avg:.2f} ms  p99 {p99:.2f} ms  worst {max(times) * 1000:.2f} ms")
ok = avg < 16.0 and p99 < 20.0
print("PASS: holds 60 fps" if ok else "FAIL: too slow for 60 fps")
sys.exit(0 if ok else 1)

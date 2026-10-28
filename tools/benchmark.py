"""Frame-pacing benchmark: drives the real game loop (App.run's fixed-step accumulator, draw_scene, present, clock.tick)
through the title, the menus and a CPU-vs-CPU battle on every arena, and reports what a player would feel.

    .venv/bin/python tools/benchmark.py [seconds-per-scene] [k8ssmash flags, e.g. --render-scale 2]

It runs in booth mode (fullscreen, same config file the service uses if K8SSMASH_CONFIG is set) unless you pass flags.
Each scene gets an untimed warm-up first (caches and backdrops are built on first draw; that cost is reported as
"first" instead of polluting the timing). Two numbers per scene:

  work   CPU time for update + draw, before present(). This is what a slower Pi runs out of. Budget: 16.7 ms.
  seen   wall time between presents, i.e. what the player sees. With vsync this sits at 16.7 ms when healthy.

PASS needs, per scene: work p99 under 14 ms, under 0.5% of frames that missed a vblank (seen > 25 ms), and no
single frame over 100 ms. Exit code 1 if any scene fails.
"""
import statistics
import subprocess
import sys
import time

import pygame

from k8ssmash.config import FPS, RS, Config
from k8ssmash.main import STEP, App, apply_args, parse_args
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.scenes.select import CharacterSelect
from k8ssmash.scenes.stageselect import StageSelect
from k8ssmash.scenes.title import Title
from k8ssmash.stage import STAGES

WARMUP_S = 1.5
WORK_P99_MS = 14.0
MISS_MS = 25.0
MISS_RATE = 0.005
STALL_MS = 100.0


def pct(sorted_ms: list[float], q: float) -> float:
    return sorted_ms[min(len(sorted_ms) - 1, int(len(sorted_ms) * q))]


def run_scene(app: App, make, name: str, seconds: float, clock: pygame.time.Clock) -> dict:
    """Same loop body as App.run(), timed. Returns per-frame work and seen times in ms."""
    t0 = time.perf_counter()
    scene = make()
    app.set_scene(scene)
    app.display.draw_scene(app.scene)
    app.display.present()
    first = (time.perf_counter() - t0) * 1000  # building the scene plus its first drawn frame
    work: list[float] = []
    seen: list[float] = []
    steps_per_frame: list[int] = []
    start = time.perf_counter()
    last = start
    acc = 0.0
    prev_present = start
    while True:
        now = time.perf_counter()
        elapsed = now - start
        if elapsed >= WARMUP_S + seconds:
            break
        timing = elapsed >= WARMUP_S
        acc += min(now - last, 0.25)
        last = now
        w0 = time.perf_counter()
        pygame.event.pump()
        app.handle_events()
        n = 0
        while acc >= STEP:
            app.step()
            acc -= STEP
            n += 1
        app.display.draw_scene(app.scene)
        w1 = time.perf_counter()
        app.display.present()
        done = time.perf_counter()
        clock.tick(FPS * 2)
        if timing:
            work.append((w1 - w0) * 1000)
            seen.append((done - prev_present) * 1000)
            steps_per_frame.append(n)
        prev_present = done
        if app.scene is not scene and not isinstance(scene, Title):
            break  # the match ended early; stop timing rather than time a different scene
    return {"name": name, "first": first, "work": work, "seen": seen, "steps": steps_per_frame}


def judge(r: dict) -> tuple[bool, str]:
    if len(r["work"]) < FPS:  # under a second of data means the scene ended early; do not pass it by default
        return False, "too few frames"
    work_p99 = pct(sorted(r["work"]), 0.99)
    misses = sum(s > MISS_MS for s in r["seen"]) / len(r["seen"])
    worst = max(r["seen"])
    reasons = []
    if work_p99 > WORK_P99_MS:
        reasons.append(f"work p99 {work_p99:.1f} ms > {WORK_P99_MS:.0f}")
    if misses > MISS_RATE:
        reasons.append(f"{misses * 100:.1f}% frames missed vblank")
    if worst > STALL_MS:
        reasons.append(f"stall {worst:.0f} ms")
    return not reasons, "; ".join(reasons)


def sysinfo() -> None:
    try:
        rates = pygame.display.get_desktop_refresh_rates()
        print(f"desktop refresh rates: {rates}  current: {pygame.display.get_current_refresh_rate()}")
    except (AttributeError, pygame.error):
        pass
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2).stdout.strip()
        print(f"{out}  (throttled=0x0 is healthy)")
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    args = sys.argv[1:]
    seconds = float(args.pop(0)) if args and args[0].replace(".", "", 1).isdigit() else 8.0
    cfg = apply_args(Config.load(), parse_args(args or ["--booth"]))
    cfg.save = lambda *a, **k: None  # a benchmark must never rewrite the booth's saved config
    app = App(cfg)
    print(f"driver={pygame.display.get_driver()} gpu_scaled={app.display.gpu} output={app.display.output_size} "
          f"render_scale={RS} canvas={app.display.canvas.get_size()} fullscreen={cfg.fullscreen}")
    sysinfo()
    r = roster()
    clock = pygame.time.Clock()

    scenes = [("title", lambda: Title(app)),
              ("character select", lambda: CharacterSelect(app)),
              ("stage select", lambda: StageSelect(app, [r[0], r[1]], [True, True], [0, 1]))]
    for i, make_stage in enumerate(STAGES):
        def make(i=i, make_stage=make_stage):
            b = Battle(app, [r[i % 8], r[(i + 3) % 8]], stage=make_stage(), human=[False, False], items=True)
            b.frame = READY_FRAMES  # skip the countdown
            return b
        scenes.append((f"battle: {make_stage().name}", make))

    print(f"\n{len(scenes)} scenes x {seconds:.0f}s timed (+{WARMUP_S:.1f}s warm-up each)\n")
    header = f"{'scene':<28}{'first':>8}{'work avg':>10}{'work p99':>10}{'seen avg':>10}{'seen p99':>10}{'worst':>8}{'missed':>8}  result"
    print(header)
    print("-" * len(header))
    failed = []
    for name, make in scenes:
        res = run_scene(app, make, name, seconds, clock)
        ok, why = judge(res)
        if not res["work"]:
            print(f"{name:<28} no frames timed")
            failed.append(name)
            continue
        w, s = sorted(res["work"]), sorted(res["seen"])
        missed = sum(x > MISS_MS for x in res["seen"]) / len(res["seen"]) * 100
        print(f"{name:<28}{res['first']:>6.0f}ms{statistics.mean(w):>8.2f}ms{pct(w, .99):>8.2f}ms"
              f"{statistics.mean(s):>8.2f}ms{pct(s, .99):>8.2f}ms{max(s):>6.0f}ms{missed:>7.1f}%  "
              f"{'ok' if ok else 'FAIL: ' + why}")
        if not ok:
            failed.append(name)
    pygame.quit()
    print()
    if failed:
        print(f"FAIL: {len(failed)} scene(s) do not hold 60 fps: {', '.join(failed)}")
        return 1
    print("PASS: holds 60 fps on every scene")
    return 0


if __name__ == "__main__":
    sys.exit(main())

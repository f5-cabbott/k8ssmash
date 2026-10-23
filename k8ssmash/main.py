from __future__ import annotations

import argparse
import logging
import sys
import time

import pygame

from k8ssmash.audio_manager import Audio
from k8ssmash.config import FPS, Config
from k8ssmash.input import InputManager
from k8ssmash.render import Display
from k8ssmash.scenes.base import Scene
from k8ssmash.watchdog import Watchdog

log = logging.getLogger("k8ssmash")

STEP = 1.0 / FPS
EXIT_COMBO = {"SELECT", "START", "SHIELD", "ATTACK"}  # staff-only: hold ~3s on one pad to quit
EXIT_FRAMES = 180


class App:
    def __init__(self, cfg: Config):
        pygame.init()
        self.cfg = cfg
        self.display = Display(cfg)
        self.input = InputManager(cfg)
        self.audio = Audio(cfg.sfx_volume, cfg.music_volume, cfg.muted)
        self.running = True
        self.scenes: list[Scene] = []
        self._screenshot_n = 0
        self.idle_frames = 0  # frames since any player pressed anything; drives attract/reset
        self.last_match: tuple[list[int], list[bool], int] = ([0, 1], [True, True], 0)
        self._combo_frames = 0
        self._combo_armed = True
        self._exit_frames = 0
        self.show_fps = False
        self.watchdog = Watchdog()
        self._fps_font = pygame.font.Font(None, 18)

    @property
    def scene(self) -> Scene:
        return self.scenes[-1]

    def set_scene(self, scene: Scene) -> None:
        self.scenes = [scene]

    def go_title(self) -> None:
        """Back to the title with the idle clock reset, so attract mode waits a full interval."""
        from k8ssmash.scenes.title import Title

        self.idle_frames = 0
        self.set_scene(Title(self))

    def push_scene(self, scene: Scene) -> None:
        self.scenes.append(scene)

    def pop_scene(self) -> None:
        if len(self.scenes) > 1:
            self.scenes.pop()

    def _check_test_combo(self) -> None:
        """Holding SELECT+START on any player for ~1.5s toggles the controller test screen."""
        from k8ssmash.scenes.padtest import ControllerTest

        held = any({"SELECT", "START"} <= p.held for p in self.input.players)
        self._combo_frames = self._combo_frames + 1 if held else 0
        if not held:
            self._combo_armed = True
        if self._combo_frames >= 90 and self._combo_armed:
            self._combo_armed = False
            if isinstance(self.scene, ControllerTest):
                self.pop_scene()
            else:
                self.push_scene(ControllerTest(self))

    def _check_exit_combo(self) -> None:
        held = any(EXIT_COMBO <= p.held for p in self.input.players)
        self._exit_frames = self._exit_frames + 1 if held else 0
        if self._exit_frames >= EXIT_FRAMES:
            log.info("exit combo held; quitting")
            self.running = False

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.input.handle_event(event)
            if event.type == pygame.KEYDOWN and self.cfg.dev_keys:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F11:
                    self.display.toggle_fullscreen()
                elif event.key == pygame.K_F10:
                    self.display.cycle_resolution()
                elif event.key == pygame.K_F9:
                    self.audio.toggle_mute()
                    self.cfg.muted = self.audio.muted
                elif event.key == pygame.K_F8:
                    self.show_fps = not self.show_fps
                elif event.key == pygame.K_F12:
                    self._screenshot_n += 1
                    self.display.screenshot(f"screenshots/shot_{self._screenshot_n:03d}.png")
            self.scene.handle_event(event)

    def step(self) -> None:
        self.input.poll()
        self.idle_frames = 0 if any(p.pressed for p in self.input.players) else self.idle_frames + 1
        self._check_test_combo()
        self._check_exit_combo()
        self.scene.update()

    def run(self) -> None:
        clock = pygame.time.Clock()
        last = time.perf_counter()
        acc = 0.0
        worst = 0.0
        self.watchdog.ready()
        log.info("running: driver=%s gpu_scaled=%s window=%s pads=%s watchdog=%s",
                 pygame.display.get_driver(), self.display.gpu, self.display.output_size,
                 [p.get_name() if p else None for p in self.input.pads], self.watchdog.active)
        while self.running:
            now = time.perf_counter()
            worst = max(worst * 0.995, now - last)
            acc += min(now - last, 0.25)
            last = now
            self.watchdog.ping()
            self.handle_events()
            while acc >= STEP:
                self.step()
                acc -= STEP
            self.scene.draw(self.display.canvas)
            if self.show_fps:
                text = f"{clock.get_fps():.0f} fps  worst {worst * 1000:.0f} ms"
                self.display.canvas.blit(self._fps_font.render(text, False, (255, 255, 0), (0, 0, 0)), (4, 4))
            self.display.present()
            clock.tick(FPS * 2)
        self.watchdog.stopping()
        self.cfg.save()
        pygame.quit()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="k8ssmash", description="K8s Smash: pods vs. chaos")
    ap.add_argument("--booth", action="store_true",
                    help="kiosk mode: fullscreen, no dev hotkeys, no mouse (use for the booth)")
    ap.add_argument("--fullscreen", action="store_true", help="start fullscreen")
    ap.add_argument("--windowed", action="store_true", help="start in a window (overrides saved fullscreen)")
    ap.add_argument("--size", metavar="WxH", help="window size, e.g. 1920x1080 or 2560x1440")
    ap.add_argument("--no-items", action="store_true", help="disable k8s power-ups")
    ap.add_argument("--mute", action="store_true", help="start muted")
    ap.add_argument("--fps", action="store_true", help="show the FPS overlay (F8 toggles it)")
    ap.add_argument("--software-render", action="store_true", help="scale on the CPU instead of the GPU")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args(argv)


def apply_args(cfg: Config, args: argparse.Namespace) -> Config:
    import os

    if args.booth or os.environ.get("K8SSMASH_BOOTH") == "1":
        cfg.fullscreen, cfg.dev_keys = True, False
    if args.fullscreen:
        cfg.fullscreen = True
    if args.windowed:
        cfg.fullscreen = False
    if args.size:
        w, h = args.size.lower().split("x")
        cfg.width, cfg.height = int(w), int(h)
    if args.no_items:
        cfg.items = False
    if args.mute:
        cfg.muted = True
    return cfg


def main(argv: list[str] | None = None) -> None:
    from k8ssmash.scenes.title import Title

    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    cfg = apply_args(Config.load(), args)
    try:
        app = App(cfg)
        if args.software_render:
            app.display.prefer_gpu = False
            app.display._set_mode()
        app.show_fps = args.fps
        app.set_scene(Title(app))
        app.run()
    except Exception:
        # systemd restarts us (Restart=on-failure); make sure the reason is in the journal.
        log.exception("fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()

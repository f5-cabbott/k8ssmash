from __future__ import annotations

import sys
import time

import pygame

from k8ssmash.config import FPS, Config
from k8ssmash.fighter import FighterStats
from k8ssmash.input import InputManager
from k8ssmash.render import Display
from k8ssmash.scenes.base import Scene

STEP = 1.0 / FPS


def placeholder_roster() -> list[FighterStats]:
    return [
        FighterStats("Pod", (80, 160, 255)),
        FighterStats("Chaos", (255, 110, 90), weight=110, run_speed=2.4),
    ]


class App:
    def __init__(self, cfg: Config):
        pygame.init()
        self.cfg = cfg
        self.display = Display(cfg)
        self.input = InputManager(cfg)
        self.running = True
        self.scenes: list[Scene] = []
        self._screenshot_n = 0
        self._combo_frames = 0
        self._combo_armed = True

    @property
    def scene(self) -> Scene:
        return self.scenes[-1]

    def set_scene(self, scene: Scene) -> None:
        self.scenes = [scene]

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
                elif event.key == pygame.K_F12:
                    self._screenshot_n += 1
                    self.display.screenshot(f"screenshots/shot_{self._screenshot_n:03d}.png")
            self.scene.handle_event(event)

    def step(self) -> None:
        self.input.poll()
        self._check_test_combo()
        self.scene.update()

    def run(self) -> None:
        clock = pygame.time.Clock()
        last = time.perf_counter()
        acc = 0.0
        while self.running:
            now = time.perf_counter()
            acc += min(now - last, 0.25)
            last = now
            self.handle_events()
            while acc >= STEP:
                self.step()
                acc -= STEP
            self.scene.draw(self.display.canvas)
            self.display.present()
            clock.tick(FPS * 2)
        self.cfg.save()
        pygame.quit()


def main() -> None:
    from k8ssmash.scenes.battle import Battle

    cfg = Config.load()
    if "--fullscreen" in sys.argv:
        cfg.fullscreen = True
    app = App(cfg)
    app.set_scene(Battle(app, placeholder_roster()))
    app.run()


if __name__ == "__main__":
    main()

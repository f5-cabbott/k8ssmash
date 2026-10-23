from __future__ import annotations

import math

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W, FPS
from k8ssmash.scenes.base import Scene

BG = (16, 22, 44)
KUBE_BLUE = (50, 108, 229)
ATTRACT_AFTER = 45 * FPS


def draw_helm(canvas: pygame.Surface, cx: int, cy: int, r: int, angle: float, color) -> None:
    """Seven-spoke ship's wheel, the Kubernetes logo shape."""
    pygame.draw.circle(canvas, color, (cx, cy), r, 4)
    pygame.draw.circle(canvas, color, (cx, cy), r // 4)
    for i in range(7):
        a = angle + i * 2 * math.pi / 7
        ex, ey = cx + math.cos(a) * (r + 8), cy + math.sin(a) * (r + 8)
        pygame.draw.line(canvas, color, (cx, cy), (ex, ey), 4)
        pygame.draw.circle(canvas, color, (int(ex), int(ey)), 4)


class Title(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.frame = 0
        self.huge = pygame.font.Font(None, 96)
        self.big = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 22)

    def update(self) -> None:
        from k8ssmash.scenes.attract import Attract
        from k8ssmash.scenes.select import CharacterSelect

        self.frame += 1
        # START with SELECT held is the controller-test combo, not "start game".
        starting = any("START" in p.pressed and "SELECT" not in p.held for p in self.app.input.players)
        if starting:
            self.app.set_scene(CharacterSelect(self.app))
        elif self.app.idle_frames >= ATTRACT_AFTER:
            self.app.set_scene(Attract(self.app))

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        for i in range(0, CANVAS_H, 6):
            shade = 16 + i // 24
            pygame.draw.line(canvas, (shade, shade + 6, shade + 28), (0, i), (CANVAS_W, i), 6)
        draw_helm(canvas, CANVAS_W // 2, 112, 44, self.frame * 0.01, KUBE_BLUE)
        title = self.huge.render("K8S SMASH", False, (255, 255, 255))
        canvas.blit(title, ((CANVAS_W - title.get_width()) // 2, 175))
        sub = self.big.render("PODS  VS.  CHAOS", False, KUBE_BLUE)
        canvas.blit(sub, ((CANVAS_W - sub.get_width()) // 2, 240))
        if (self.frame // 30) % 2 == 0:
            press = self.big.render("PRESS START", False, (255, 220, 90))
            canvas.blit(press, ((CANVAS_W - press.get_width()) // 2, 298))

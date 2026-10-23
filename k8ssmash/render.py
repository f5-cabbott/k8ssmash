"""Virtual pixel canvas with nearest-neighbor integer scaling to the output window."""
from __future__ import annotations

from pathlib import Path

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W, RESOLUTIONS, Config


def integer_scale(out_w: int, out_h: int) -> int:
    return max(1, min(out_w // CANVAS_W, out_h // CANVAS_H))


class Display:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.screen: pygame.Surface
        self._set_mode()
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H)).convert()

    def _set_mode(self) -> None:
        flags = pygame.FULLSCREEN if self.cfg.fullscreen else 0
        size = (self.cfg.width, self.cfg.height)
        self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("K8s Smash")
        pygame.mouse.set_visible(not self.cfg.fullscreen)

    @property
    def scale(self) -> int:
        w, h = self.screen.get_size()
        return integer_scale(w, h)

    def toggle_fullscreen(self) -> None:
        self.cfg.fullscreen = not self.cfg.fullscreen
        self._set_mode()
        self.cfg.save()

    def cycle_resolution(self) -> None:
        current = (self.cfg.width, self.cfg.height)
        idx = RESOLUTIONS.index(current) if current in RESOLUTIONS else -1
        self.cfg.width, self.cfg.height = RESOLUTIONS[(idx + 1) % len(RESOLUTIONS)]
        self._set_mode()
        self.cfg.save()

    def present(self) -> None:
        scale = self.scale
        out_w, out_h = CANVAS_W * scale, CANVAS_H * scale
        sw, sh = self.screen.get_size()
        scaled = pygame.transform.scale(self.canvas, (out_w, out_h))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, ((sw - out_w) // 2, (sh - out_h) // 2))
        pygame.display.flip()

    def screenshot(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self.screen, str(path))

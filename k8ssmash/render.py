"""Virtual pixel canvas, nearest-neighbor scaled to the output.

Primary path: pygame.SCALED, so SDL scales the 640x360 canvas on the GPU (cheap on a Pi 5, vsynced).
Fallback path: scale in software with an integer factor and letterbox (used if SCALED is unavailable).
"""
from __future__ import annotations

from pathlib import Path

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W, RESOLUTIONS, Config


def integer_scale(out_w: int, out_h: int) -> int:
    return max(1, min(out_w // CANVAS_W, out_h // CANVAS_H))


class Display:
    def __init__(self, cfg: Config, prefer_gpu: bool = True):
        self.cfg = cfg
        self.prefer_gpu = prefer_gpu
        self.gpu = False
        self.screen: pygame.Surface
        self._set_mode()
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H)).convert()

    # --- window management ---------------------------------------------------------------
    def _set_mode(self) -> None:
        pygame.display.set_caption("K8s Smash")
        if self.prefer_gpu:
            flags = pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if self.cfg.fullscreen else 0)
            try:
                self.screen = pygame.display.set_mode((CANVAS_W, CANVAS_H), flags, vsync=1)
                self.gpu = True
                if not self.cfg.fullscreen:
                    self._resize_window(self.cfg.width, self.cfg.height)
            except pygame.error:
                self.gpu = False
        if not self.gpu:
            flags = pygame.FULLSCREEN if self.cfg.fullscreen else 0
            self.screen = pygame.display.set_mode((self.cfg.width, self.cfg.height), flags)
        pygame.mouse.set_visible(not self.cfg.fullscreen)

    @staticmethod
    def _resize_window(width: int, height: int) -> None:
        try:
            pygame.Window.from_display_module().size = (width, height)
            pygame.event.pump()
        except (AttributeError, pygame.error):
            pass

    @property
    def output_size(self) -> tuple[int, int]:
        return pygame.display.get_window_size() if self.gpu else self.screen.get_size()

    @property
    def scale(self) -> int:
        return integer_scale(*self.output_size)

    def toggle_fullscreen(self) -> None:
        self.cfg.fullscreen = not self.cfg.fullscreen
        self._set_mode()
        self.cfg.save()

    def cycle_resolution(self) -> None:
        current = (self.cfg.width, self.cfg.height)
        idx = RESOLUTIONS.index(current) if current in RESOLUTIONS else -1
        self.cfg.width, self.cfg.height = RESOLUTIONS[(idx + 1) % len(RESOLUTIONS)]
        if self.gpu and not self.cfg.fullscreen:
            self._resize_window(self.cfg.width, self.cfg.height)
        elif not self.gpu:
            self._set_mode()
        self.cfg.save()

    # --- drawing -------------------------------------------------------------------------
    def present(self) -> None:
        if self.gpu:
            self.screen.blit(self.canvas, (0, 0))
        else:
            scale = self.scale
            out_w, out_h = CANVAS_W * scale, CANVAS_H * scale
            sw, sh = self.screen.get_size()
            scaled = pygame.transform.scale(self.canvas, (out_w, out_h))
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, ((sw - out_w) // 2, (sh - out_h) // 2))
        pygame.display.flip()

    def screenshot(self, path: str | Path) -> None:
        """Saves the canvas scaled by the current integer factor (same pixels the player sees)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        s = self.scale
        pygame.image.save(pygame.transform.scale(self.canvas, (CANVAS_W * s, CANVAS_H * s)), str(path))

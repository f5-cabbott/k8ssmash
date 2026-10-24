"""Virtual pixel canvas, nearest-neighbor scaled to the output.

Primary path: pygame.SCALED, so SDL scales the 640x360 canvas on the GPU (cheap on a Pi 5, vsynced).
Fallback path: scale in software with an integer factor and letterbox (used if SCALED is unavailable).
"""
from __future__ import annotations

from pathlib import Path

import pygame

from k8ssmash.config import RESOLUTIONS, WORLD_H, WORLD_W, Config


def integer_scale(out_w: int, out_h: int) -> int:
    return max(1, min(out_w // WORLD_W, out_h // WORLD_H))


class Display:
    def __init__(self, cfg: Config, prefer_gpu: bool = True):
        self.cfg = cfg
        self.prefer_gpu = prefer_gpu
        self.gpu = False
        self.screen: pygame.Surface
        self._set_mode()
        self.canvas = pygame.Surface((WORLD_W, WORLD_H)).convert()
        self._scratch: dict[tuple[int, int], pygame.Surface] = {}

    # --- window management ---------------------------------------------------------------
    def _set_mode(self) -> None:
        pygame.display.set_caption("K8s Smash")
        if self.prefer_gpu:
            flags = pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if self.cfg.fullscreen else 0)
            try:
                self.screen = pygame.display.set_mode((WORLD_W, WORLD_H), flags, vsync=1)
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
    def desktop_size() -> tuple[int, int]:
        try:
            return tuple(pygame.display.get_desktop_sizes()[0])  # type: ignore[return-value]
        except (pygame.error, IndexError):
            return (1920, 1080)

    @classmethod
    def fit_to_desktop(cls, width: int, height: int) -> tuple[int, int]:
        """Shrink a requested window size (keeping 16:9) so it fits on the desktop with room for the title bar
        and panels; on an ultrawide the height is what runs out first."""
        dw, dh = cls.desktop_size()
        k = min(1.0, dw * 0.94 / width, dh * 0.86 / height)
        return max(WORLD_W // 2, int(width * k) // 16 * 16), max(WORLD_H // 2, int(height * k) // 9 * 9)

    @classmethod
    def _resize_window(cls, width: int, height: int) -> None:
        width, height = cls.fit_to_desktop(width, height)
        try:
            win = pygame.Window.from_display_module()
            win.size = (width, height)
            dw, dh = cls.desktop_size()
            win.position = ((dw - width) // 2, max(40, (dh - height) // 2))  # centered, clear of the top edge
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
        sizes = [r for r in RESOLUTIONS if self.fit_to_desktop(*r) == r] or list(RESOLUTIONS)  # only sizes that fit
        idx = sizes.index(current) if current in sizes else -1
        self.cfg.width, self.cfg.height = sizes[(idx + 1) % len(sizes)]
        if self.gpu and not self.cfg.fullscreen:
            self._resize_window(self.cfg.width, self.cfg.height)
        elif not self.gpu:
            self._set_mode()
        self.cfg.save()

    # --- drawing -------------------------------------------------------------------------
    def draw_scene(self, scene) -> None:
        """Draw a scene onto the world canvas. Scenes designed for a smaller grid (the menus) draw on their own
        surface and are smooth-scaled up, so each screen keeps its layout."""
        size = tuple(scene.native)
        if size == self.canvas.get_size():
            scene.draw(self.canvas)
            return
        scratch = self._scratch.get(size)
        if scratch is None:
            scratch = self._scratch[size] = pygame.Surface(size).convert()
        scene.draw(scratch)
        pygame.transform.smoothscale(scratch, self.canvas.get_size(), self.canvas)

    def present(self) -> None:
        if self.gpu:
            self.screen.blit(self.canvas, (0, 0))
        else:
            scale = self.scale
            out_w, out_h = WORLD_W * scale, WORLD_H * scale
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
        pygame.image.save(pygame.transform.scale(self.canvas, (WORLD_W * s, WORLD_H * s)), str(path))

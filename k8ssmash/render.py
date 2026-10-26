"""The virtual canvas, scaled to the window.

Game logic is 960x540 world units drawn at RS times that (1920x1080 by default), so the play area is PIX_W x PIX_H pixels. On a wider screen (an ultrawide monitor) the canvas grows sideways to match the
display, so the picture fills the screen instead of leaving black bars: battles draw the scenery across the whole
width with the arena centred, and menus sit centred on border art.

Primary path: pygame.SCALED, so SDL scales the canvas on the GPU (cheap on a Pi 5, vsynced).
Fallback path: scale in software with an integer factor and letterbox (used if SCALED is unavailable).
"""
from __future__ import annotations

from pathlib import Path

import pygame

from k8ssmash.config import MAX_CANVAS_W, PIX_H, PIX_W, RESOLUTIONS, RS, WORLD_H, WORLD_W, Config

ASPECTS = ("16:9", "21:9", "auto")
ASPECT_CANVAS_W = {"16:9": WORLD_W, "21:9": 1260}


def integer_scale(out_w: int, out_h: int, canvas_w: int = PIX_W) -> int:
    return max(1, min(out_w // canvas_w, out_h // PIX_H))


def fit_scale(out_w: int, out_h: int, canvas_w: int) -> float:
    """The factor that fits the whole canvas inside the output, keeping its shape (letterboxing the rest)."""
    return min(out_w / canvas_w, out_h / PIX_H)


class Display:
    def __init__(self, cfg: Config, prefer_gpu: bool = True):
        self.cfg = cfg
        self.prefer_gpu = prefer_gpu
        self.gpu = False
        self.screen: pygame.Surface
        self.canvas: pygame.Surface
        self.play: pygame.Surface  # the centred PIX_W x PIX_H area menus draw into
        self.play_rect = pygame.Rect(0, 0, PIX_W, PIX_H)
        self._scratch: dict[tuple[int, int], pygame.Surface] = {}
        self._border: pygame.Surface | None = None
        self._set_mode()

    # --- sizing --------------------------------------------------------------------------
    @staticmethod
    def desktop_size() -> tuple[int, int]:
        try:
            return tuple(pygame.display.get_desktop_sizes()[0])  # type: ignore[return-value]
        except (pygame.error, IndexError):
            return (1920, 1080)

    def canvas_width(self) -> int:
        """How wide the canvas should be: 960 for 16:9, wider when the screen is."""
        mode = self.cfg.shape
        if mode in ASPECT_CANVAS_W:
            return ASPECT_CANVAS_W[mode]
        if self.cfg.fullscreen:  # auto: fill whatever display we are going fullscreen on
            dw, dh = self.desktop_size()
            return max(WORLD_W, min(MAX_CANVAS_W, round(WORLD_H * dw / dh / 2) * 2))
        return WORLD_W  # auto in a window: windows are 16:9

    def window_size(self) -> tuple[int, int]:
        """The requested window size for the current aspect, shrunk to fit the desktop."""
        cw = self.canvas_width()
        return self.fit_to_desktop(round(self.cfg.height * cw / WORLD_H), self.cfg.height)

    @classmethod
    def fit_to_desktop(cls, width: int, height: int) -> tuple[int, int]:
        """Shrink a requested window size (keeping its aspect) so it fits on the desktop with room for the title bar
        and panels; on an ultrawide the height is what runs out first."""
        dw, dh = cls.desktop_size()
        k = min(1.0, dw * 0.94 / width, dh * 0.86 / height)
        return max(480, int(width * k) // 2 * 2), max(270, int(height * k) // 2 * 2)

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

    # --- window management ---------------------------------------------------------------
    def _set_mode(self) -> None:
        pygame.display.set_caption("K8s Smash")
        cw = self.canvas_width()
        if self.prefer_gpu:
            flags = pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if self.cfg.fullscreen else 0)
            try:
                self.screen = pygame.display.set_mode((cw * RS, PIX_H), flags, vsync=1)
                self.gpu = True
                if not self.cfg.fullscreen:
                    self._resize_window(*self.window_size())
            except pygame.error:
                self.gpu = False
        if not self.gpu:
            flags = pygame.FULLSCREEN if self.cfg.fullscreen else 0
            self.screen = pygame.display.set_mode(self.window_size(), flags)
        pygame.mouse.set_visible(not self.cfg.fullscreen)
        self.canvas = pygame.Surface((cw * RS, PIX_H)).convert()
        self.play_rect = pygame.Rect((cw - WORLD_W) // 2 * RS, 0, PIX_W, PIX_H)
        self.play = self.canvas.subsurface(self.play_rect)
        self._border = None

    @property
    def output_size(self) -> tuple[int, int]:
        return pygame.display.get_window_size() if self.gpu else self.screen.get_size()

    @property
    def scale(self) -> float:
        """How much bigger (or smaller) the window shows the canvas than its own pixels."""
        return fit_scale(*self.output_size, self.canvas.get_width())

    def apply(self) -> None:
        """Rebuild the window after a display setting changed, and remember it."""
        self._set_mode()
        self.cfg.save()

    def toggle_fullscreen(self) -> None:
        self.cfg.fullscreen = not self.cfg.fullscreen
        self.apply()

    def set_aspect(self, mode: str) -> None:
        self.cfg.shape = mode if mode in ASPECTS else "16:9"
        self.apply()

    def sizes(self) -> list[tuple[int, int]]:
        """Window sizes (16:9 heights) that fit this desktop at the current aspect."""
        cw = self.canvas_width()
        fit = [r for r in RESOLUTIONS
               if self.fit_to_desktop(round(r[1] * cw / WORLD_H), r[1]) == (round(r[1] * cw / WORLD_H) // 2 * 2, r[1])]
        return fit or list(RESOLUTIONS)

    def cycle_resolution(self) -> None:
        current = (self.cfg.width, self.cfg.height)
        sizes = self.sizes()
        idx = sizes.index(current) if current in sizes else -1
        self.set_size(*sizes[(idx + 1) % len(sizes)])

    def set_size(self, width: int, height: int) -> None:
        self.cfg.width, self.cfg.height = width, height
        if self.gpu and not self.cfg.fullscreen:
            self._resize_window(*self.window_size())
        elif not self.gpu:
            self._set_mode()
        self.cfg.save()

    # --- drawing -------------------------------------------------------------------------
    def _border_art(self) -> pygame.Surface:
        """What fills the space beside the play area on a wide canvas: dark gradient, faint grid, neon rails."""
        if self._border is None:
            from k8ssmash.backdrops import dither_gradient

            cw = self.canvas.get_width()
            art = dither_gradient(cw, PIX_H, [(0, (3, 5, 18)), (0.55, (7, 14, 44)), (1, (2, 3, 12))], bands=20)
            step = 48 * RS
            for x in range(0, cw, step):
                pygame.draw.line(art, (10, 22, 56), (x, 0), (x, PIX_H), RS)
            for y in range(0, PIX_H, step):
                pygame.draw.line(art, (10, 22, 56), (0, y), (cw, y), RS)
            for x in (self.play_rect.left, self.play_rect.right - RS):
                pygame.draw.line(art, (0, 130, 170), (x, 0), (x, PIX_H), 2 * RS)
                inner = x + (3 * RS if x == self.play_rect.left else -4 * RS)
                pygame.draw.line(art, (0, 70, 100), (inner, 0), (inner, PIX_H), RS)
            self._border = art
        return self._border

    def draw_scene(self, scene) -> None:
        """Draw a scene. Battles ("wide" scenes) take the whole canvas; menus draw into the centred play area, and any
        space beside it is filled with border art. A scene with another design size is smooth-scaled into the play area."""
        if getattr(scene, "wide", False):
            scene.draw(self.canvas)
            return
        if self.canvas.get_width() > PIX_W:
            self.canvas.blit(self._border_art(), (0, 0))
        size = tuple(scene.native)
        if size == self.play.get_size():
            scene.draw(self.play)
            return
        scratch = self._scratch.get(size)
        if scratch is None:
            scratch = self._scratch[size] = pygame.Surface(size).convert()
        scene.draw(scratch)
        pygame.transform.smoothscale(scratch, self.play.get_size(), self.play)

    def present(self) -> None:
        if self.gpu:
            self.screen.blit(self.canvas, (0, 0))
        else:
            sw, sh = self.screen.get_size()
            k = self.scale
            cw = self.canvas.get_width()
            out_w, out_h = round(cw * k), round(PIX_H * k)
            scaled = (pygame.transform.smoothscale(self.canvas, (out_w, out_h)) if (out_w, out_h) != (cw, PIX_H)
                      else self.canvas)
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, ((sw - out_w) // 2, (sh - out_h) // 2))
        pygame.display.flip()

    def screenshot(self, path: str | Path) -> None:
        """Saves the canvas at its own resolution (the pixels the game drew)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self.canvas, str(path))

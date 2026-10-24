"""Shared text and window styling: gradient-filled outlined text and SNES RPG-style panels."""
from __future__ import annotations

import pygame

Color = tuple[int, int, int]

_text_cache: dict[tuple, pygame.Surface] = {}
_window_cache: dict[tuple, pygame.Surface] = {}


def _mix(a: Color, b: Color, t: float) -> Color:
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def _luma(c: Color) -> float:
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


class Font:
    """Drop-in for pygame.font.Font(None, size).render(): smooth text, vertical gradient, dark outline."""

    def __init__(self, size: int):
        self.size_px = size
        self._font = pygame.font.Font(None, size)
        self.outline = 1 if size < 44 else 2

    def flat(self, text: str, color: Color) -> pygame.Surface:
        """Plain anti-aliased text with no outline (for tiny labels inside glyphs)."""
        return self._font.render(text, True, color)

    def get_height(self) -> int:
        return self._font.get_height()

    def size(self, text: str) -> tuple[int, int]:
        return self._font.size(text)

    def render(self, text: str, antialias: bool = False, color: Color = (255, 255, 255),
               background: Color | None = None) -> pygame.Surface:
        color = tuple(color[:3])  # type: ignore[assignment]
        if background is not None or _luma(color) < 45 or not text.strip():
            return self._font.render(text, True, color, background) if background else \
                self._font.render(text, True, color)  # flat: debug overlays and drop shadows
        key = (text, self.size_px, color)
        cached = _text_cache.get(key)
        if cached is not None:
            return cached
        mask = self._font.render(text, True, (255, 255, 255))
        w, h = mask.get_size()
        o = self.outline
        top = _mix(color, (255, 255, 255), 0.42)
        bottom = _mix(color, (20, 24, 70), 0.38)
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            pygame.draw.line(grad, _mix(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
        fill = mask.copy()
        fill.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        edge = tuple(max(0, int(c * 0.16)) for c in _mix(color, (30, 30, 90), 0.35))
        dark = mask.copy()
        dark.fill(edge + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        out = pygame.Surface((w + 2 * o + 1, h + 2 * o + 1), pygame.SRCALPHA)
        for dx in range(-o, o + 1):
            for dy in range(-o, o + 2):
                if dx or dy:
                    out.blit(dark, (o + dx, o + dy))
        out.blit(fill, (o, o))
        if len(_text_cache) > 600:
            _text_cache.clear()
        _text_cache[key] = out
        return out


def window(canvas: pygame.Surface, rect: pygame.Rect, accent: Color | None = None, alpha: int = 235) -> None:
    """A Final Fantasy VI-style window: deep blue gradient, bright bevelled border, soft shadow."""
    key = (rect.size, accent, alpha)
    surf = _window_cache.get(key)
    if surf is None:
        w, h = rect.size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        top, bottom = (36, 52, 150), (10, 14, 66)
        for y in range(h):
            pygame.draw.line(surf, _mix(top, bottom, y / max(1, h - 1)) + (alpha,), (0, y), (w, y))
        # dithered sheen on the upper third, like a CRT-era gradient
        for y in range(2, h // 3, 2):
            for x in range(2 + (y // 2) % 2, w - 2, 2):
                surf.set_at((x, y), _mix(top, (200, 210, 255), 0.10) + (alpha,))
        edge = accent or (232, 236, 255)
        pygame.draw.rect(surf, (6, 8, 30), (0, 0, w, h), 1, border_radius=4)
        pygame.draw.rect(surf, edge, (1, 1, w - 2, h - 2), 1, border_radius=3)
        pygame.draw.rect(surf, _mix(edge, (40, 50, 120), 0.7), (2, 2, w - 4, h - 4), 1, border_radius=2)
        pygame.draw.line(surf, (255, 255, 255), (4, 1), (w - 5, 1))  # top specular
        _window_cache[key] = surf
    shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    shadow.fill((0, 0, 12, 90))
    canvas.blit(shadow, (rect.x + 2, rect.y + 3))
    canvas.blit(surf, rect.topleft)


BUTTON_COLORS = {"A": (214, 64, 64), "B": (232, 190, 56), "X": (74, 114, 224), "Y": (72, 190, 96)}
_glyph_font: Font | None = None


def button_glyph(canvas: pygame.Surface, x: int, y: int, label: str) -> int:
    """A tiny SNES-style button (colored face button or shoulder) at (x, y). Returns its width."""
    global _glyph_font
    _glyph_font = _glyph_font or Font(14)
    if label in BUTTON_COLORS:
        c = BUTTON_COLORS[label]
        pygame.draw.circle(canvas, (14, 10, 30), (x + 7, y + 7), 8)
        pygame.draw.circle(canvas, c, (x + 7, y + 7), 7)
        pygame.draw.circle(canvas, _mix(c, (255, 255, 255), 0.45), (x + 5, y + 5), 2)
        t = _glyph_font.flat(label, (255, 255, 255))
        canvas.blit(t, (x + 7 - t.get_width() // 2, y + 7 - t.get_height() // 2 + 1))
        return 16
    pygame.draw.rect(canvas, (14, 10, 30), (x, y + 1, 18, 12), border_radius=4)
    pygame.draw.rect(canvas, (176, 182, 206), (x + 1, y + 2, 16, 10), border_radius=3)
    t = _glyph_font.flat(label, (30, 34, 70))
    canvas.blit(t, (x + 9 - t.get_width() // 2, y + 7 - t.get_height() // 2 + 1))
    return 19


def dpad_glyph(canvas: pygame.Surface, x: int, y: int, direction: str | None = None) -> int:
    """A tiny D-pad; the arm for `direction` ('up'/'down'/'left'/'right') lights up. Returns its width."""
    arms = {"up": (5, 0, 4, 5), "down": (5, 9, 4, 5), "left": (0, 5, 5, 4), "right": (9, 5, 5, 4)}
    pygame.draw.rect(canvas, (14, 10, 30), (x - 1, y - 1, 16, 16), border_radius=3)
    for name, (ax, ay, aw, ah) in arms.items():
        lit = name == direction
        pygame.draw.rect(canvas, (255, 236, 130) if lit else (110, 118, 156), (x + ax, y + ay, aw, ah))
    pygame.draw.rect(canvas, (150, 158, 196), (x + 5, y + 5, 4, 4))
    return 17

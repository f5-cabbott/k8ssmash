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


# --- design-unit scaling for the menu screens ------------------------------------------------------------
# Menus are laid out on a 640x360 grid but drawn at the 960x540 world resolution, so text renders at its real size
# and pixel art lands on whole pixels instead of being stretched (which blurred everything).
SCALE = 1.5


class ScaledDraw:
    """pygame.draw-alike that takes design-grid coordinates (640x360) and draws them at world scale (960x540)."""

    def __init__(self, u: float):
        self.u = u

    def _p(self, pt) -> tuple[int, int]:
        return round(pt[0] * self.u), round(pt[1] * self.u)

    def _w(self, w: float) -> int:
        return int(w) if w <= 1 else max(1, round(w * self.u))  # hairlines stay hairlines

    def _r(self, rect) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        return round(x * self.u), round(y * self.u), max(1, round(w * self.u)), max(1, round(h * self.u))

    def rect(self, surf, color, rect, width=0, border_radius=0):
        pygame.draw.rect(surf, color, self._r(rect), self._w(width) if width else 0,
                         border_radius=round(border_radius * self.u))

    def line(self, surf, color, a, b, width=1):
        pygame.draw.line(surf, color, self._p(a), self._p(b), self._w(width))

    def lines(self, surf, color, closed, pts, width=1):
        pygame.draw.lines(surf, color, closed, [self._p(p) for p in pts], self._w(width))

    def polygon(self, surf, color, pts, width=0):
        pygame.draw.polygon(surf, color, [self._p(p) for p in pts], self._w(width) if width else 0)

    def circle(self, surf, color, center, radius, width=0):
        pygame.draw.circle(surf, color, self._p(center), max(1, round(radius * self.u)), self._w(width) if width else 0)

    def ellipse(self, surf, color, rect, width=0):
        pygame.draw.ellipse(surf, color, self._r(rect), self._w(width) if width else 0)

    def set_at(self, surf, pos, color):
        x, y = self._p(pos)
        size = max(1, round(self.u))
        surf.fill(color, (x, y, size, size))

    def fill(self, surf, color, rect):
        surf.fill(color, self._r(rect))

    def blit(self, dst, src, pos):
        dst.blit(src, self._p(pos))

    def surface(self, size) -> pygame.Surface:
        return pygame.Surface((round(size[0] * self.u), round(size[1] * self.u)), pygame.SRCALPHA)


    def set_clip(self, surf, rect):
        surf.set_clip(None if rect is None else self._r(rect))


pd = ScaledDraw(SCALE)


class DSurface(pygame.Surface):
    """A rendered-text surface that *reports* its size in design units, so layout maths written for the 640x360 grid
    (centering, right-aligning, advancing x past a label) keeps working. Blitting still uses the real pixels."""

    def get_width(self) -> int:
        return round(super().get_width() / SCALE)

    def get_height(self) -> int:
        return round(super().get_height() / SCALE)

    def get_size(self) -> tuple[int, int]:
        return self.get_width(), self.get_height()


def _as_design(surf: pygame.Surface) -> DSurface:
    d = DSurface(pygame.Surface.get_size(surf), pygame.SRCALPHA)
    d.blit(surf, (0, 0))
    return d


class UIFont(Font):
    """Font for menu scenes: pass the design-unit size and it renders at world resolution."""

    def __init__(self, size: int):
        super().__init__(max(8, round(size * SCALE)))
        self._design: dict[tuple, DSurface] = {}

    def render(self, text: str, antialias: bool = False, color: Color = (255, 255, 255),
               background: Color | None = None) -> pygame.Surface:
        key = (text, tuple(color[:3]), background)
        hit = self._design.get(key)
        if hit is None:
            if len(self._design) > 400:
                self._design.clear()
            hit = self._design[key] = _as_design(super().render(text, antialias, color, background))
        return hit

    def get_height(self) -> int:
        return round(super().get_height() / SCALE)

    def size(self, text: str) -> tuple[int, int]:
        w, h = super().size(text)
        return round(w / SCALE), round(h / SCALE)


def blit_c(canvas: pygame.Surface, surf: pygame.Surface, y: float) -> None:
    """Blit horizontally centred on the canvas, at a design-unit y."""
    canvas.blit(surf, ((canvas.get_width() - pygame.Surface.get_width(surf)) // 2, round(y * SCALE)))


def blit_sprite(canvas: pygame.Surface, img: pygame.Surface, x: float, y: float, feet: tuple[int, int]) -> None:
    """Place a sprite so its feet land on a design-unit point. Sprites stay at their native pixel size."""
    canvas.blit(img, (round(x * SCALE) - feet[0], round(y * SCALE) - feet[1]))


def scale_surface(surf: pygame.Surface, k: float) -> pygame.Surface:
    """Smoothly resize a text surface by k (used for gentle pulses). Returns a design-sized surface."""
    w, h = pygame.Surface.get_size(surf)
    return _as_design(pygame.transform.smoothscale(surf, (max(1, int(w * k)), max(1, int(h * k)))))


def window_d(canvas: pygame.Surface, rect: pygame.Rect, accent: Color | None = None, alpha: int = 235) -> None:
    """window() for a rect given in design units."""
    x, y, w, h = pd._r(rect)
    window(canvas, pygame.Rect(x, y, w, h), accent, alpha)


BUTTON_COLORS = {"A": (214, 64, 64), "B": (232, 190, 56), "X": (74, 114, 224), "Y": (72, 190, 96)}
_glyph_font: Font | None = None


def _gfont() -> Font:
    """The glyph label font, rebuilt if pygame was shut down and restarted since it was made."""
    global _glyph_font
    try:
        if _glyph_font is None:
            raise pygame.error("not built yet")
        _glyph_font._font.get_height()
    except pygame.error:
        _glyph_font = Font(round(14 * SCALE))
    return _glyph_font


def button_glyph(canvas: pygame.Surface, x: int, y: int, label: str, s: float = 1.0) -> int:
    """A tiny SNES-style button (colored face button or shoulder) at a design-unit (x, y). Returns its design width."""
    k = SCALE * s  # sizes scale with s; positions stay in design units
    font = _gfont()
    X, Y = round(x * SCALE), round(y * SCALE)
    if label in BUTTON_COLORS:
        c = BUTTON_COLORS[label]
        r = round(7 * k)
        pygame.draw.circle(canvas, (14, 10, 30), (X + r, Y + r), r + 2)
        pygame.draw.circle(canvas, c, (X + r, Y + r), r)
        pygame.draw.circle(canvas, _mix(c, (255, 255, 255), 0.45), (X + r - 2, Y + r - 2), round(2 * k))
        t = font.flat(label, (255, 255, 255))
        canvas.blit(t, (X + r - t.get_width() // 2, Y + r - t.get_height() // 2 + 1))
        return round(16 * s)
    w, h = round(18 * k), round(12 * k)
    pygame.draw.rect(canvas, (14, 10, 30), (X, Y + 1, w, h), border_radius=5)
    pygame.draw.rect(canvas, (176, 182, 206), (X + 2, Y + 3, w - 4, h - 4), border_radius=4)
    t = font.flat(label, (30, 34, 70))
    canvas.blit(t, (X + w // 2 - t.get_width() // 2, Y + h // 2 - t.get_height() // 2 + 2))
    return round(19 * s)


def dpad_glyph(canvas: pygame.Surface, x: int, y: int, direction: str | None = None, s: float = 1.0) -> int:
    """A tiny D-pad at a design-unit (x, y); the arm for `direction` lights up. Returns its design width."""
    k = SCALE * s
    X, Y = round(x * SCALE), round(y * SCALE)
    arms = {"up": (5, 0, 4, 5), "down": (5, 9, 4, 5), "left": (0, 5, 5, 4), "right": (9, 5, 5, 4)}
    pygame.draw.rect(canvas, (14, 10, 30), (X - 2, Y - 2, round(16 * k), round(16 * k)), border_radius=4)
    for name, (ax, ay, aw, ah) in arms.items():
        pygame.draw.rect(canvas, (255, 236, 130) if name == direction else (110, 118, 156),
                         (X + round(ax * k), Y + round(ay * k), round(aw * k), round(ah * k)))
    pygame.draw.rect(canvas, (150, 158, 196), (X + round(5 * k), Y + round(5 * k), round(4 * k), round(4 * k)))
    return round(17 * s)

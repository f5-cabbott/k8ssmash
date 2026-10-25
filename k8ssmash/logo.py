"""The K8S SMASH logo, drawn from strokes: chunky rounded letters with an outline, a deep extrusion, a gradient
face and a rim light. Built once at startup; the title scene bobs and shines the finished letters."""
from __future__ import annotations

import math

import pygame

OUTLINE = (6, 8, 30)

# Letters are polylines in a unit box (0..1 across, 0..1 down). Curves are Catmull-Rom smoothed.
GLYPHS: dict[str, list[tuple[bool, list[tuple[float, float]]]]] = {
    "K": [(False, [(0.12, 0.0), (0.12, 1.0)]), (False, [(0.88, 0.0), (0.14, 0.58)]), (False, [(0.36, 0.4), (0.9, 1.0)])],
    "S": [(True, [(0.86, 0.2), (0.62, 0.02), (0.3, 0.02), (0.12, 0.22), (0.2, 0.42), (0.5, 0.52), (0.82, 0.62),
                  (0.9, 0.8), (0.7, 0.98), (0.34, 0.98), (0.12, 0.8)])],
    "M": [(False, [(0.1, 1.0), (0.1, 0.0), (0.5, 0.64), (0.9, 0.0), (0.9, 1.0)])],
    "A": [(False, [(0.08, 1.0), (0.5, 0.0), (0.92, 1.0)]), (False, [(0.26, 0.68), (0.74, 0.68)])],
    "H": [(False, [(0.12, 0.0), (0.12, 1.0)]), (False, [(0.88, 0.0), (0.88, 1.0)]), (False, [(0.12, 0.5), (0.88, 0.5)])],
    "8": [(True, [(0.5, 0.5), (0.8, 0.34), (0.7, 0.08), (0.5, 0.02), (0.3, 0.08), (0.2, 0.34), (0.5, 0.5), (0.86, 0.7),
                  (0.72, 0.95), (0.5, 0.99), (0.28, 0.95), (0.14, 0.7), (0.5, 0.5)])],
}
WIDTH = {"K": 0.78, "S": 0.74, "M": 0.92, "A": 0.86, "H": 0.8, "8": 0.74}


def _smooth(pts: list[tuple[float, float]], steps: int = 6) -> list[tuple[float, float]]:
    p = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(p) - 2):
        for s in range(steps):
            t = s / steps
            out.append(tuple(0.5 * ((2 * p[i][k]) + (-p[i - 1][k] + p[i + 1][k]) * t
                                    + (2 * p[i - 1][k] - 5 * p[i][k] + 4 * p[i + 1][k] - p[i + 2][k]) * t * t
                                    + (-p[i - 1][k] + 3 * p[i][k] - 3 * p[i + 1][k] + p[i + 2][k]) * t ** 3)
                            for k in (0, 1)))
    out.append(pts[-1])
    return out


def _mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))



def letter(ch: str, h: int, ramp: list[tuple[float, tuple]], depth: int, thick: int | None = None) -> pygame.Surface:
    """One finished letter: transparent surface with room for the outline and extrusion on the right/bottom."""
    thick = thick or max(6, h // 5)
    w = round(h * WIDTH[ch])
    pad = thick // 2 + 4
    size = (w + 2 * pad + depth, h + 2 * pad + depth)
    mask = pygame.Surface(size, pygame.SRCALPHA)
    for smooth, pts in GLYPHS[ch]:
        px = [(pad + x * w, pad + y * h) for x, y in (_smooth(pts) if smooth else pts)]
        for a, b in zip(px, px[1:]):
            pygame.draw.line(mask, (255, 255, 255), a, b, thick)
        for p in px:
            pygame.draw.circle(mask, (255, 255, 255), (round(p[0]), round(p[1])), thick // 2)
    # outline: the mask grown by 3px
    grown = pygame.Surface(size, pygame.SRCALPHA)
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 10:
                grown.blit(mask, (dx, dy))
    # extrusion: the grown shape stepped down and to the right, darkening with depth
    out = pygame.Surface(size, pygame.SRCALPHA)
    for k in range(depth, 0, -1):
        tint = pygame.Surface(size, pygame.SRCALPHA)
        tint.blit(grown, (0, 0))
        tint.fill(_mix((14, 20, 96), (4, 6, 36), k / depth) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        out.blit(tint, (k, k))
    edge = grown.copy()
    edge.fill(OUTLINE + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(edge, (0, 0))
    # face: vertical gradient, then a lighter rim along the top-left edges
    grad = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(size[1]):
        t = (y - pad) / max(1, h)
        for (t0, c0), (t1, c1) in zip(ramp, ramp[1:]):
            if t <= t1 or (t1, c1) == ramp[-1]:
                grad.fill(_mix(c0, c1, max(0.0, min(1.0, (t - t0) / max(1e-6, t1 - t0)))) + (255,), (0, y, size[0], 1))
                break
    face = mask.copy()
    face.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MAX)  # keep alpha, set rgb white
    face.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    face.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    out.blit(face, (0, 0))
    rim = mask.copy()
    shifted = pygame.Surface(size, pygame.SRCALPHA)
    shifted.blit(mask, (2, 2))
    rim.blit(shifted, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)  # what is left is the top-left lip
    rim.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
    lip = pygame.Surface(size, pygame.SRCALPHA)
    lip.fill((255, 255, 255, 255))
    lip.blit(rim, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    lip.set_alpha(170)
    out.blit(lip, (0, 0))
    # an inner shade along the bottom-right keeps big letters from looking flat
    inner = pygame.Surface(size, pygame.SRCALPHA)
    inner.blit(mask, (-2, -2))
    inner.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    inner.fill((0, 0, 40, 255), special_flags=pygame.BLEND_RGBA_MULT)
    inner.set_alpha(90)
    out.blit(inner, (0, 0))
    return out


def word(text: str, h: int, ramp, depth: int, gap: int = 6) -> list[tuple[pygame.Surface, int]]:
    """Letters of a word with their x offsets, and the total width as the last x."""
    letters, x = [], 0
    for ch in text:
        img = letter(ch, h, ramp, depth)
        letters.append((img, x))
        x += img.get_width() - depth + gap
    letters.append((pygame.Surface((0, 0)), x - gap + depth))
    return letters


TUBE_BLUE = [(0.0, (190, 250, 255)), (0.45, (40, 190, 255)), (1.0, (30, 80, 230))]
HOT = [(0.0, (255, 250, 170)), (0.4, (255, 190, 60)), (0.75, (255, 100, 50)), (1.0, (220, 40, 90))]

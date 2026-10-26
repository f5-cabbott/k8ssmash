"""Supersampled drawing helpers: layer callbacks draw smooth shapes at SS x resolution in rig coordinates."""
from __future__ import annotations

import pygame

SS = 4
WHITE = (255, 255, 255, 255)


class Layer(pygame.Surface):
    """A supersampled alpha surface for one body part."""


def new_layer(frame: int) -> Layer:
    return Layer((frame * SS, frame * SS), pygame.SRCALPHA)


def _p(pt) -> tuple[int, int]:
    return round(pt[0] * SS), round(pt[1] * SS)


def circle(s: Layer, center, r: float, width: float = 0) -> None:
    pygame.draw.circle(s, WHITE, _p(center), max(1, round(r * SS)), round(width * SS))


def ellipse(s: Layer, x: float, y: float, w: float, h: float) -> None:
    pygame.draw.ellipse(s, WHITE, (round(x * SS), round(y * SS), round(w * SS), round(h * SS)))


def rect(s: Layer, x: float, y: float, w: float, h: float, radius: float = 0) -> None:
    pygame.draw.rect(s, WHITE, (round(x * SS), round(y * SS), round(w * SS), round(h * SS)),
                     border_radius=round(radius * SS))


def line(s: Layer, a, b, width: float) -> None:
    pygame.draw.line(s, WHITE, _p(a), _p(b), max(1, round(width * SS)))


def poly(s: Layer, pts) -> None:
    pygame.draw.polygon(s, WHITE, [_p(p) for p in pts])


def arc(s: Layer, x: float, y: float, w: float, h: float, a0: float, a1: float, width: float) -> None:
    pygame.draw.arc(s, WHITE, (round(x * SS), round(y * SS), round(w * SS), round(h * SS)), a0, a1,
                    max(1, round(width * SS)))


def limb(s: Layer, pts, width: float) -> None:
    for a, b in zip(pts, pts[1:]):
        line(s, a, b, width)
    for p in pts:
        circle(s, p, width / 2)


def taper(s: Layer, pts, widths) -> None:
    """A limb whose thickness changes along its length (thigh to ankle, shoulder to wrist): quads between joints."""
    for (a, b), (wa, wb) in zip(zip(pts, pts[1:]), zip(widths, widths[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = (dx * dx + dy * dy) ** 0.5 or 1.0
        nx, ny = -dy / d, dx / d
        poly(s, [(a[0] + nx * wa / 2, a[1] + ny * wa / 2), (b[0] + nx * wb / 2, b[1] + ny * wb / 2),
                 (b[0] - nx * wb / 2, b[1] - ny * wb / 2), (a[0] - nx * wa / 2, a[1] - ny * wa / 2)])
    for p, w in zip(pts, widths):
        circle(s, p, w / 2)

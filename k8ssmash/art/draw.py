"""Supersampled drawing helpers: layer callbacks draw smooth shapes at SS x resolution in rig coordinates."""
from __future__ import annotations

import pygame

from k8ssmash.config import RS

SS = 4 * RS  # layer pixels per rig unit: four samples per output pixel at any render scale
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


def catmull(pts, closed: bool = False, steps: int = 8):
    """Smooth curve through the points (Catmull-Rom), returned as a dense list of points."""
    n = len(pts)
    if n < 3:
        return list(pts)
    out = []
    count = n if closed else n - 1
    for i in range(count):
        if closed:
            p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        else:
            p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for k in range(steps):
            t = k / steps
            out.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    if not closed:
        out.append(tuple(pts[-1]))
    return out


def smooth(s: Layer, pts) -> None:
    """A filled closed shape with a smooth, hand-drawn-looking contour (not a circle or a polygon)."""
    poly(s, catmull(pts, closed=True))


def ribbon(s: Layer, pts, widths, steps: int = 8) -> None:
    """A curved limb or tail whose thickness follows `widths` (one per control point) along a smooth centreline."""
    line_pts = catmull(pts, closed=False, steps=steps)
    n = len(line_pts)
    ws = catmull([(i, w) for i, w in enumerate(widths)], closed=False, steps=max(2, (n - 1) // max(1, len(widths) - 1) + 1))
    left, right = [], []
    for i, p in enumerate(line_pts):
        a, b = line_pts[max(i - 1, 0)], line_pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = (dx * dx + dy * dy) ** 0.5 or 1.0
        w = ws[min(len(ws) - 1, round(i / max(1, n - 1) * (len(ws) - 1)))][1] / 2
        left.append((p[0] - dy / d * w, p[1] + dx / d * w))
        right.append((p[0] + dy / d * w, p[1] - dx / d * w))
    poly(s, left + right[::-1])
    circle(s, line_pts[0], ws[0][1] / 2)
    circle(s, line_pts[-1], ws[-1][1] / 2)

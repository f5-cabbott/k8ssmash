"""Factories for hand-shaped body parts. A character is described by a head contour, a torso profile and a limb style;
each factory returns a draw function for Look.head_fn / torso_fn / arm_fn / leg_fn, built from smooth splines and
tapering ribbons instead of circles and capsules. Coordinates are rig units, +x forward (the fighter faces right)."""
from __future__ import annotations

import math

from k8ssmash.art import draw


def head(points, base: float = 10.0, hard: bool = False):
    """A head silhouette from contour points (relative to the head centre, authored for head_r == base)."""
    def fn(s, r) -> None:
        cx, cy = r.head
        k = r.look.head_r / base
        pts = [(cx + x * k, cy + y * k) for x, y in points]
        draw.poly(s, pts) if hard else draw.smooth(s, pts)
    return fn


def torso(profile, hard: bool = False):
    """A torso from (t, side) samples: t runs hip (0) to shoulder (1), side is in half-widths (+ belly, - back)."""
    def fn(s, r) -> None:
        w = r.look.torso_w
        hx, hy = r.hip
        sx, sy = r.shoulder
        ux, uy = sx - hx, sy - hy
        pts = [(hx + ux * t + side * w * 0.5, hy + uy * t) for t, side in profile]
        draw.poly(s, pts) if hard else draw.smooth(s, pts)
    return fn


def _frame(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    return ux, uy, -uy, ux


def arm(style: str = "mitt", taper=(1.1, 0.9, 0.8)):
    """Tapered arm ending in a hand: mitt (rounded fist + thumb), glove (mitt with a cuff), claw, mech or bone."""
    def fn(s, r, back: bool) -> None:
        sh = r.shoulder
        el, hd = (r.elbow_b, r.hand_b) if back else (r.elbow_f, r.hand_f)
        w = r.look.arm_w
        draw.ribbon(s, [sh, el, hd], [w * taper[0], w * taper[1], w * taper[2]])
        ux, uy, nx, ny = _frame(el, hd)

        def P(a: float, b: float):
            return (hd[0] + ux * a * w + nx * b * w, hd[1] + uy * a * w + ny * b * w)
        if style in ("mitt", "glove"):
            draw.smooth(s, [P(-0.3, -0.78), P(0.5, -1.0), P(1.2, -0.72), P(1.5, 0.0), P(1.2, 0.78), P(0.4, 1.0), P(-0.3, 0.66)])
            draw.smooth(s, [P(0.1, -0.7), P(0.8, -1.4), P(1.45, -1.05), P(0.95, -0.45)])  # the thumb
            if style == "glove":
                draw.poly(s, [P(-0.9, -0.95), P(-0.25, -1.05), P(-0.25, 1.05), P(-0.9, 0.95)])  # the cuff
        elif style == "claw":
            draw.smooth(s, [P(-0.3, -0.6), P(0.5, -0.8), P(0.9, 0.0), P(0.5, 0.8), P(-0.3, 0.6)])
            for b in (-0.55, 0.0, 0.55):
                draw.poly(s, [P(0.5, b - 0.28), P(1.9, b * 1.5), P(0.5, b + 0.28)])
        elif style == "mech":
            draw.circle(s, hd, w * 0.78)
            for b in (-0.5, 0.5):
                draw.poly(s, [P(0.4, b - 0.28), P(1.5, b - 0.22), P(1.5, b + 0.22), P(0.4, b + 0.28)])
            draw.circle(s, el, w * 0.62)
        elif style == "bone":
            draw.circle(s, hd, w * 0.55)
            for b in (-0.55, -0.15, 0.25, 0.65):
                draw.ribbon(s, [P(0.2, b * 0.6), P(1.0, b), P(1.7, b * 1.1)], [w * 0.28, w * 0.2, w * 0.1])
    return fn


def leg(style: str = "boot", taper=(1.2, 0.95, 0.8)):
    """Tapered leg ending in a boot, sneaker, pump, armoured piston foot or plain bare foot."""
    def fn(s, r, back: bool) -> None:
        hip = r.hip
        kn, ft = (r.knee_b, r.foot_b) if back else (r.knee_f, r.foot_f)
        w = r.look.leg_w
        draw.ribbon(s, [hip, kn, ft], [w * taper[0], w * taper[1], w * taper[2]])
        fx, fy = ft

        def Q(a: float, b: float):
            return (fx + a * w, fy + b * w)
        if style == "boot":
            draw.smooth(s, [Q(-0.75, -1.0), Q(0.45, -1.05), Q(0.8, -0.3), Q(1.8, -0.05), Q(2.05, 0.45), Q(-0.85, 0.58)])
        elif style == "sneaker":
            draw.smooth(s, [Q(-0.7, -0.95), Q(0.3, -0.95), Q(1.1, -0.4), Q(1.85, 0.0), Q(1.95, 0.5), Q(0.9, 0.65), Q(-0.85, 0.62)])
        elif style == "pump":
            draw.smooth(s, [Q(-0.6, -0.9), Q(0.3, -0.7), Q(1.3, -0.1), Q(1.9, 0.25), Q(1.2, 0.5), Q(-0.1, 0.45), Q(-0.7, 0.75), Q(-0.9, 0.2)])
        elif style == "piston":
            draw.poly(s, [Q(-0.85, -0.95), Q(0.6, -0.95), Q(1.0, -0.15), Q(1.95, 0.05), Q(1.95, 0.6), Q(-0.9, 0.6)])
            draw.circle(s, kn, w * 0.72)
        elif style == "greave":
            draw.smooth(s, [Q(-0.8, -1.0), Q(0.5, -1.05), Q(0.9, -0.25), Q(1.9, 0.0), Q(2.0, 0.55), Q(-0.9, 0.6)])
            draw.smooth(s, [(kn[0] - w * 0.2, kn[1] - w * 0.85), (kn[0] + w * 0.95, kn[1] - w * 0.3), (kn[0] + w * 0.8, kn[1] + w * 0.55),
                            (kn[0] - w * 0.3, kn[1] + w * 0.7)])  # the knee plate
    return fn

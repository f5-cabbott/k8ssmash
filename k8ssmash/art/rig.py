"""Posable 2D rig and pixel-art compositor used to generate fighter sprite sheets.

Each body part is drawn flat onto its own layer, then composited with an outline, a lit top-left
rim, a shaded bottom-right rim and a dithered lower-body shadow. That gives consistent
16-bit-style cel shading across every fighter and every pose.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import pygame

FRAME = 80
FEET = (40, 74)  # where the fighter's feet sit inside a frame

Color = tuple[int, int, int]
ColorSet = tuple[Color, Color, Color]  # base, dark, light
Layer = tuple[Callable[[pygame.Surface, "Rig"], None], str]  # (draw fn, palette key)


@dataclass
class Pose:
    lean: float = 0.0  # torso top offset forward of the hip
    crouch: float = 0.0
    bob: float = 0.0
    hip_dx: float = 0.0
    head_dx: float = 0.0
    head_dy: float = 0.0
    f_foot: tuple[float, float] = (5.0, 0.0)  # (forward offset, lift) of the front foot
    b_foot: tuple[float, float] = (-5.0, 0.0)
    arm_f: tuple[float, float] = (10.0, 20.0)  # upper/forearm angles; 0 = down, 90 = forward, 180 = up
    arm_b: tuple[float, float] = (-10.0, 0.0)
    flash: bool = False  # extra white-ish effect lines (counter, buff)


@dataclass
class Look:
    name: str
    pal: dict[str, ColorSet]
    leg_len: float = 14
    leg_w: float = 6
    torso_h: float = 16
    torso_w: float = 14
    arm_len: float = 15
    arm_w: float = 5
    head_r: float = 10
    head_style: str = "round"  # round | box
    head_w: float = 0  # box/ellipse width override
    head_h: float = 0
    limb_pal: str = "body"
    leg_pal: str = ""  # defaults to limb_pal
    torso_pal: str = "body"
    head_pal: str = "skin"
    back: list[Layer] = field(default_factory=list)  # accessories behind the body
    front: list[Layer] = field(default_factory=list)  # accessories over the body
    details: Callable[[pygame.Surface, "Rig"], None] | None = None  # flat face/chest details


@dataclass
class Rig:
    look: Look
    pose: Pose
    hip: tuple[float, float]
    shoulder: tuple[float, float]
    head: tuple[float, float]
    knee_f: tuple[float, float]
    foot_f: tuple[float, float]
    knee_b: tuple[float, float]
    foot_b: tuple[float, float]
    elbow_f: tuple[float, float]
    hand_f: tuple[float, float]
    elbow_b: tuple[float, float]
    hand_b: tuple[float, float]
    fore_f: tuple[float, float]  # unit direction of the front forearm


def _dir(angle: float) -> tuple[float, float]:
    a = math.radians(angle)
    return math.sin(a), math.cos(a)


def _ik(a: tuple[float, float], b: tuple[float, float], l1: float, l2: float,
        bend: int = -1) -> tuple[tuple[float, float], tuple[float, float]]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 0.001
    d = max(abs(l1 - l2) + 0.01, min(d, l1 + l2 - 0.01))
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    ang = base + bend * math.acos(max(-1.0, min(1.0, cos_a)))
    knee = (a[0] + l1 * math.cos(ang), a[1] + l1 * math.sin(ang))
    end = (a[0] + dx / math.hypot(dx, dy or 0.001) * d, a[1] + dy / math.hypot(dx, dy or 0.001) * d)
    return knee, end


def solve(look: Look, pose: Pose) -> Rig:
    fx, fy = FEET
    hip = (fx + pose.hip_dx, fy - look.leg_len + pose.crouch + pose.bob)
    shoulder = (hip[0] + pose.lean, hip[1] - look.torso_h)
    head = (shoulder[0] + pose.head_dx + pose.lean * 0.3,
            shoulder[1] - look.head_r * 0.8 + pose.head_dy)
    seg = look.leg_len * 0.58
    ft_f = (fx + pose.f_foot[0], fy - pose.f_foot[1])
    ft_b = (fx + pose.b_foot[0], fy - pose.b_foot[1])
    knee_f, foot_f = _ik(hip, ft_f, seg, seg)
    knee_b, foot_b = _ik(hip, ft_b, seg, seg)
    half = look.arm_len / 2

    def arm(sh: tuple[float, float], angles: tuple[float, float]):
        d1, d2 = _dir(angles[0]), _dir(angles[1])
        elbow = (sh[0] + d1[0] * half, sh[1] + d1[1] * half)
        hand = (elbow[0] + d2[0] * half, elbow[1] + d2[1] * half)
        return elbow, hand, d2

    sh_f = (shoulder[0] + 2, shoulder[1] + 2)
    sh_b = (shoulder[0] - 2, shoulder[1] + 2)
    elbow_f, hand_f, fore_f = arm(sh_f, pose.arm_f)
    elbow_b, hand_b, _ = arm(sh_b, pose.arm_b)
    return Rig(look, pose, hip, shoulder, head, knee_f, foot_f, knee_b, foot_b,
               elbow_f, hand_f, elbow_b, hand_b, fore_f)


# --- default part drawing ------------------------------------------------------------------
WHITE = (255, 255, 255, 255)


def limb(surf: pygame.Surface, pts: list[tuple[float, float]], width: float) -> None:
    for a, b in zip(pts, pts[1:]):
        pygame.draw.line(surf, WHITE, a, b, max(1, round(width)))
    for p in pts:
        pygame.draw.circle(surf, WHITE, (round(p[0]), round(p[1])), max(1, round(width / 2)))


def draw_torso(surf: pygame.Surface, r: Rig) -> None:
    w = r.look.torso_w
    hx, hy = r.hip
    sx, sy = r.shoulder
    pygame.draw.polygon(surf, WHITE, [(hx - w / 2, hy), (hx + w / 2, hy),
                                      (sx + w / 2 + 1, sy), (sx - w / 2 - 1, sy)])
    pygame.draw.circle(surf, WHITE, (round(hx), round(hy)), round(w / 2))
    pygame.draw.circle(surf, WHITE, (round(sx), round(sy + 1)), round(w / 2 + 1))


def draw_head(surf: pygame.Surface, r: Rig) -> None:
    lk = r.look
    cx, cy = r.head
    if lk.head_style == "box":
        w, h = lk.head_w or lk.head_r * 2, lk.head_h or lk.head_r * 1.6
        pygame.draw.rect(surf, WHITE, (round(cx - w / 2), round(cy - h / 2), round(w), round(h)),
                         border_radius=3)
    else:
        w, h = lk.head_w or lk.head_r * 2, lk.head_h or lk.head_r * 2
        pygame.draw.ellipse(surf, WHITE, (round(cx - w / 2), round(cy - h / 2), round(w), round(h)))


def _shade(frame: pygame.Surface, layer: pygame.Surface, colors: ColorSet) -> None:
    base, dark, light = colors
    outline = tuple(max(0, int(c * 0.28)) for c in dark)
    mask = pygame.mask.from_surface(layer)
    if mask.count() == 0:
        return
    size = layer.get_size()

    def paint(m: pygame.mask.Mask, color: Color) -> None:
        frame.blit(m.to_surface(setcolor=color + (255,), unsetcolor=(0, 0, 0, 0)), (0, 0))

    sil = mask.to_surface(setcolor=outline + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        frame.blit(sil, (dx, dy))
    paint(mask, base)

    # lower-body shadow zone with a dithered edge
    bbox = layer.get_bounding_rect()
    zone_top = bbox.top + int(bbox.height * 0.6)
    zone = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(zone, WHITE, (0, zone_top, size[0], size[1]))
    shadow = mask.overlap_mask(pygame.mask.from_surface(zone), (0, 0))
    paint(shadow, dark)
    for x in range(bbox.left, bbox.right):
        y = zone_top - 1
        if (x + y) % 2 == 0 and 0 <= x < size[0] and mask.get_at((x, y)):
            frame.set_at((x, y), dark + (255,))

    # rim light top-left (2px) and rim shade bottom-right (1px)
    hi = mask.copy()
    hi.erase(mask, (1, 1))
    paint(hi, light)
    hi2 = mask.copy()
    hi2.erase(mask, (2, 2))
    paint(hi2, light)
    sh = mask.copy()
    sh.erase(mask, (-1, -1))
    paint(sh, dark)


def render(look: Look, pose: Pose) -> pygame.Surface:
    r = solve(look, pose)
    frame = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)

    def layer(fn: Callable[[pygame.Surface, Rig], None], pal: str) -> None:
        surf = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)
        fn(surf, r)
        _shade(frame, surf, look.pal[pal])

    for fn, pal in look.back:
        layer(fn, pal)
    layer(lambda s, rg: limb(s, [rg.shoulder, rg.elbow_b, rg.hand_b], look.arm_w), look.limb_pal + "_back")
    leg_pal = look.leg_pal or look.limb_pal
    layer(lambda s, rg: limb(s, [rg.hip, rg.knee_b, rg.foot_b], look.leg_w), leg_pal + "_back")
    layer(draw_torso, look.torso_pal)
    layer(lambda s, rg: limb(s, [rg.hip, rg.knee_f, rg.foot_f], look.leg_w), leg_pal)
    layer(draw_head, look.head_pal)
    layer(lambda s, rg: limb(s, [rg.shoulder, rg.elbow_f, rg.hand_f], look.arm_w), look.limb_pal)
    for fn, pal in look.front:
        layer(fn, pal)
    if look.details:
        look.details(frame, r)
    if pose.flash:
        for i in range(5):
            a = math.radians(-70 + i * 35)
            cx, cy = r.hip[0], r.hip[1] - 6
            pygame.draw.line(frame, (255, 250, 200),
                             (cx + math.cos(a) * 22, cy + math.sin(a) * 26),
                             (cx + math.cos(a) * 30, cy + math.sin(a) * 34), 2)
    return frame


def with_back_palettes(pal: dict[str, ColorSet]) -> dict[str, ColorSet]:
    """Adds '<name>_back' variants (darker, for the far-side limbs) for each palette entry."""
    out = dict(pal)
    for name, (base, dark, light) in pal.items():
        d = lambda c, k: tuple(int(v * k) for v in c)
        out[name + "_back"] = (d(dark, 1.05), d(dark, 0.7), d(base, 0.85))
    return out

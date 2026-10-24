"""Posable 2D rig. Body parts are drawn as smooth supersampled silhouettes, then shaded and
composited by art.shade into SNES-style pixel art (ramps, dithering, colored outlines)."""
from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass, field, replace
from typing import Callable

import numpy as np
import pygame

from k8ssmash.art import draw
from k8ssmash.art.shade import SHINY, layer_mask, make_ramp, paint_part

FRAME = 96
FEET = (48, 90)  # where the fighter's feet sit inside a frame

Color = tuple[int, int, int]
Layer = tuple[Callable[[draw.Layer, "Rig"], None], str]  # (draw fn, palette key)


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
    flash: bool = False  # extra effect lines (counter, buff)
    squash: float = 1.0  # vertical scale of the body: <1 squashed (anticipation, landing), >1 stretched (strikes, leaps)
    face: str = "neutral"  # expression: neutral blink happy angry hurt effort shock focus
    smear: float = 0.0  # degrees of motion smear trailing the front arm (attack swings)


@dataclass
class Look:
    name: str
    pal: dict[str, Color]  # palette name -> base color; '<name>_back' variants are added automatically
    leg_len: float = 14
    leg_w: float = 6
    torso_h: float = 16
    torso_w: float = 14
    arm_len: float = 15
    arm_w: float = 5
    head_r: float = 10
    head_style: str = "round"  # round | box
    head_w: float = 0
    head_h: float = 0
    limb_pal: str = "body"
    leg_pal: str = ""  # defaults to limb_pal
    torso_pal: str = "body"
    head_pal: str = "skin"
    flat: tuple[str, ...] = ()  # palette names shaded as hard flat surfaces (screens, plates)
    textures: dict = field(default_factory=dict)  # palette name -> fur | cloth | metal | panel
    no_hue_shift: tuple[str, ...] = ()  # palette names kept as-is in the alternate colour scheme (skin, steel...)
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


def _ik(a, b, l1: float, l2: float, bend: int = -1):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 0.001
    d = max(abs(l1 - l2) + 0.01, min(d, l1 + l2 - 0.01))
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    ang = base + bend * math.acos(max(-1.0, min(1.0, cos_a)))
    knee = (a[0] + l1 * math.cos(ang), a[1] + l1 * math.sin(ang))
    n = math.hypot(dx, dy) or 0.001
    return knee, (a[0] + dx / n * d, a[1] + dy / n * d)


def solve(look: Look, pose: Pose) -> Rig:
    fx, fy = FEET
    hip = (fx + pose.hip_dx, fy - look.leg_len + pose.crouch + pose.bob)
    shoulder = (hip[0] + pose.lean, hip[1] - look.torso_h)
    head = (shoulder[0] + pose.head_dx + pose.lean * 0.3, shoulder[1] - look.head_r * 0.8 + pose.head_dy)
    seg = look.leg_len * 0.58
    knee_f, foot_f = _ik(hip, (fx + pose.f_foot[0], fy - pose.f_foot[1]), seg, seg)
    knee_b, foot_b = _ik(hip, (fx + pose.b_foot[0], fy - pose.b_foot[1]), seg, seg)
    half = look.arm_len / 2

    def arm(sh, angles):
        d1, d2 = _dir(angles[0]), _dir(angles[1])
        elbow = (sh[0] + d1[0] * half, sh[1] + d1[1] * half)
        return elbow, (elbow[0] + d2[0] * half, elbow[1] + d2[1] * half), d2

    elbow_f, hand_f, fore_f = arm((shoulder[0] + 2, shoulder[1] + 2), pose.arm_f)
    elbow_b, hand_b, _ = arm((shoulder[0] - 2, shoulder[1] + 2), pose.arm_b)
    return Rig(look, pose, hip, shoulder, head, knee_f, foot_f, knee_b, foot_b,
               elbow_f, hand_f, elbow_b, hand_b, fore_f)


# --- default part drawing (supersampled) ----------------------------------------------------
def draw_torso(s: draw.Layer, r: Rig) -> None:
    w = r.look.torso_w
    hx, hy = r.hip
    sx, sy = r.shoulder
    draw.poly(s, [(hx - w / 2, hy), (hx + w / 2, hy), (sx + w / 2 + 1, sy), (sx - w / 2 - 1, sy)])
    draw.circle(s, (hx, hy), w / 2)
    draw.circle(s, (sx, sy + 1), w / 2 + 1)


def draw_head(s: draw.Layer, r: Rig) -> None:
    lk = r.look
    cx, cy = r.head
    if lk.head_style == "box":
        w, h = lk.head_w or lk.head_r * 2, lk.head_h or lk.head_r * 1.6
        draw.rect(s, cx - w / 2, cy - h / 2, w, h, radius=3)
    else:
        w, h = lk.head_w or lk.head_r * 2, lk.head_h or lk.head_r * 2
        draw.ellipse(s, cx - w / 2, cy - h / 2, w, h)


def with_back_palettes(pal: dict[str, Color]) -> dict[str, Color]:
    """Adds '<name>_back' (darker, cooler) variants for the far-side limbs."""
    out = dict(pal)
    for name, c in pal.items():
        out[name + "_back"] = tuple(int(v * 0.64 + w * 0.12) for v, w in zip(c, (40, 34, 90)))
    return out


_ramps: dict[Color, np.ndarray] = {}


def _ramp(c: Color) -> np.ndarray:
    if c not in _ramps:
        _ramps[c] = make_ramp(c)
    return _ramps[c]


def squashed(look: Look, k: float) -> Look:
    """Squash-and-stretch: scale the body vertically and widen it the other way so the volume feels constant."""
    if abs(k - 1.0) < 0.005:
        return look
    w = 1 / math.sqrt(k)
    return replace(look, leg_len=look.leg_len * k, torso_h=look.torso_h * k, torso_w=look.torso_w * w,
                   leg_w=look.leg_w * w, arm_w=look.arm_w * w, arm_len=look.arm_len * (1 + (k - 1) * 0.6),
                   head_r=look.head_r * (1 + (k - 1) * 0.35))


def alternate_look(look: Look) -> Look:
    """The mirror-match colour scheme: rotate every hue except the materials listed in no_hue_shift."""
    keep = set(look.no_hue_shift)
    pal = {}
    for name, c in look.pal.items():
        base = name.removesuffix("_back")
        if base in keep:
            pal[name] = c
            continue
        h, sat, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
        pal[name] = tuple(int(x * 255) for x in colorsys.hsv_to_rgb((h + 0.42) % 1.0, min(1.0, sat * 1.05), v))
    return replace(look, pal=pal)


def render(look: Look, pose: Pose) -> pygame.Surface:
    look = squashed(look, pose.squash)
    r = solve(look, pose)
    arr = np.zeros((FRAME, FRAME, 4), dtype=np.uint8)

    def part(fn: Callable[[draw.Layer, Rig], None], pal: str) -> None:
        layer = draw.new_layer(FRAME)
        fn(layer, r)
        mask = layer_mask(layer, FRAME)
        base = look.pal[pal]
        shiny = any(k in pal for k in SHINY)
        paint_part(arr, mask, _ramp(base), shiny, flat=pal.removesuffix("_back") in look.flat,
                   texture=look.textures.get(pal.removesuffix("_back"), ""))

    for fn, pal in look.back:
        part(fn, pal)
    leg_pal = look.leg_pal or look.limb_pal
    part(lambda s, rg: draw.limb(s, [rg.shoulder, rg.elbow_b, rg.hand_b], look.arm_w), look.limb_pal + "_back")
    part(lambda s, rg: draw.limb(s, [rg.hip, rg.knee_b, rg.foot_b], look.leg_w), leg_pal + "_back")
    part(draw_torso, look.torso_pal)
    part(lambda s, rg: draw.limb(s, [rg.hip, rg.knee_f, rg.foot_f], look.leg_w), leg_pal)
    part(draw_head, look.head_pal)
    part(lambda s, rg: draw.limb(s, [rg.shoulder, rg.elbow_f, rg.hand_f], look.arm_w), look.limb_pal)
    for fn, pal in look.front:
        part(fn, pal)

    frame = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(frame)[:] = arr[:, :, :3].transpose(1, 0, 2)
    pygame.surfarray.pixels_alpha(frame)[:] = arr[:, :, 3].T
    if look.details:
        look.details(frame, r)
    if pose.smear:
        sh = (r.shoulder[0] + 2, r.shoulder[1] + 2)
        half = look.arm_len / 2
        ghost = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)
        for k in (3, 2, 1):  # oldest first, fading: the arm's recent path
            a1, a2 = pose.arm_f[0] - pose.smear * k * 0.45, pose.arm_f[1] - pose.smear * k * 0.9
            d1, d2 = _dir(a1), _dir(a2)
            el = (sh[0] + d1[0] * half, sh[1] + d1[1] * half)
            hd = (el[0] + d2[0] * half, el[1] + d2[1] * half)
            pygame.draw.line(ghost, (255, 244, 214, 150 - k * 36), (round(el[0]), round(el[1])), (round(hd[0]), round(hd[1])), 3)
        frame.blit(ghost, (0, 0))
    if pose.flash:
        for i in range(5):
            a = math.radians(-70 + i * 35)
            cx, cy = r.hip[0], r.hip[1] - 6
            pygame.draw.line(frame, (255, 250, 200), (cx + math.cos(a) * 22, cy + math.sin(a) * 26),
                             (cx + math.cos(a) * 30, cy + math.sin(a) * 34), 2)
    return frame

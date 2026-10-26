"""Procedural Tron-style datacenter scenery: dithered gradient skies, several parallax layers per stage, animated
details and neon platforms. Scenery is authored on a 640x360 design grid and drawn at the 960x540 world size through
ScaledDraw, so it stays crisp. Everything is generated once per stage and then just blitted."""
from __future__ import annotations

import math
import random
from typing import Callable

import numpy as np
import pygame

from k8ssmash.art.shade import BAYER
from k8ssmash.config import CANVAS_H, CANVAS_W, PIX_H, PIX_W, RS
from k8ssmash.ui import wd
from k8ssmash.stage import Platform
from k8ssmash.ui import ScaledDraw

W, H = CANVAS_W, CANVAS_H  # design grid
U = PIX_W / CANVAS_W  # design -> render pixels (3 at the default 2x)
MARGIN = 160  # layers extend this far past each side so they cover an ultrawide canvas and can slide with the camera
CAM_LIMIT = 150
WIDE = W + 2 * MARGIN  # width of a parallax layer in design px
EXTRA = 170  # how far the floor grid runs past the play area on each side (design px)

Color = tuple[int, int, int]


pd = ScaledDraw(U)  # design -> world drawing (see k8ssmash.ui)


def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _stop_color(stops, t: float) -> Color:
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            return _lerp(c0, c1, (t - p0) / max(1e-6, p1 - p0))
    return stops[-1][1]


def dither_gradient(w: int, h: int, stops, bands: int = 20) -> pygame.Surface:
    """A vertical gradient quantized to `bands` tones with ordered dithering between them (SNES sky look)."""
    t = np.linspace(0, 1, h)
    pos = t * bands
    lo = np.floor(pos).astype(int)
    frac = pos - lo
    col_lo = np.array([_stop_color(stops, min(1.0, b / bands)) for b in lo])
    col_hi = np.array([_stop_color(stops, min(1.0, (b + 1) / bands)) for b in lo])
    thresh = np.tile(BAYER + 0.5, (h // 4 + 1, w // 4 + 1))[:h, :w]
    use_hi = (frac[:, None] > thresh)[..., None]
    arr = np.where(use_hi, col_hi[:, None, :], col_lo[:, None, :]).astype(np.uint8)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, arr.transpose(1, 0, 2))
    return surf









# --- match-reactive state and slow moods -----------------------------------------------------------------------
REACT = {"energy": 0.0, "leader": 0.0, "kos": 0, "ripples": []}  # set by the battle: how heated the fight is, who leads (-1..1), KOs so far

# Each stage drifts through a few lighting moods, like Final Destination's cycling nebulae: very slow, never flashing.
MOODS = {
    "datacenter": [((0, 0, 0), 0), ((255, 150, 40), 34), ((40, 70, 255), 40)],  # day shift, backup window, night ops
    "controlplane": [((0, 0, 0), 0), ((255, 210, 110), 30), ((150, 80, 255), 36)],
    "nodepool": [((0, 0, 0), 0), ((0, 200, 255), 32), ((255, 90, 140), 30)],
    "etcd": [((0, 0, 0), 0), ((110, 255, 176), 28), ((200, 120, 255), 34)],
    "mesh": [((0, 0, 0), 0), ((255, 120, 220), 30), ((100, 200, 255), 32)],
    "cloud": [((0, 0, 0), 0), ((255, 150, 160), 26), ((120, 170, 255), 28)],
}
MOOD_HOLD, MOOD_FADE = 2700, 700  # frames each mood holds, and how long the crossfade between moods takes
_tints: dict[tuple, pygame.Surface] = {}


def _tint(color: Color, strength: int, w: int) -> pygame.Surface:
    """A full-width wash that is strongest in the sky and fades out toward the floor."""
    key = (color, strength, w)
    if key not in _tints:
        surf = pygame.Surface((w, PIX_H), pygame.SRCALPHA)
        for y in range(0, PIX_H, 2):
            a = int(strength * (1.0 - 0.75 * y / PIX_H))
            pygame.draw.rect(surf, (*color, a), (0, y, w, 2))
        _tints[key] = surf
    return _tints[key]


def apply_mood(canvas: pygame.Surface, theme: str, frame: int) -> None:
    moods = MOODS.get(theme)
    if not moods:
        return
    n = len(moods)
    t = frame % (MOOD_HOLD * n)
    idx, into = divmod(t, MOOD_HOLD)
    cur, nxt = moods[idx], moods[(idx + 1) % n]
    blend = max(0.0, (into - (MOOD_HOLD - MOOD_FADE)) / MOOD_FADE)  # crossfade near the end of the hold
    w = canvas.get_width()
    for (color, strength), amount in ((cur, 1.0 - blend), (nxt, blend)):
        if strength and amount > 0.02:
            wash = _tint(color, strength, w)
            wash.set_alpha(int(255 * amount))
            canvas.blit(wash, (0, 0))


_hazes: dict[tuple, pygame.Surface] = {}


def haze_band(canvas: pygame.Surface, y: int, color: Color, height: int = 70, peak: int = 70) -> None:
    """Atmospheric perspective: a soft glow lying along the horizon so far scenery sits behind near scenery."""
    w = canvas.get_width()
    key = (y, color, height, peak, w)
    if key not in _hazes:
        surf = pygame.Surface((w, height), pygame.SRCALPHA)
        for i in range(height):
            pygame.draw.line(surf, (*color, int(peak * (i / height) ** 1.6)), (0, i), (w, i))
        _hazes[key] = surf
    canvas.blit(_hazes[key], (0, int(y * U) - height))



class Layer:
    """A parallax layer authored in design px (wider than the screen by MARGIN each side)."""

    def __init__(self, surf: pygame.Surface, factor: float, y: int, drift: float = 0.0, wrap: bool = False, x: int = 0):
        if pygame.display.get_surface() is not None:
            surf = surf.convert_alpha() if surf.get_flags() & pygame.SRCALPHA else surf.convert()  # display format: much faster blits
        self.surf, self.factor, self.y, self.drift, self.wrap, self.x = surf, factor, y, drift, wrap, x

    def draw(self, canvas: pygame.Surface, frame: int, cam: float) -> None:
        ox = (self.x - MARGIN - cam * self.factor + frame * self.drift) * U + (canvas.get_width() - PIX_W) // 2
        oy = self.y * U
        if self.wrap:
            w = self.surf.get_width()
            ox = ox % w - w
            for k in range(0, int(PIX_W // w) + 3):
                canvas.blit(self.surf, (ox + k * w, oy))
        else:
            canvas.blit(self.surf, (ox, oy))


class Animated:
    def __init__(self, fn: Callable[[pygame.Surface, int, float], None]):
        self.fn = fn

    def draw(self, canvas: pygame.Surface, frame: int, cam: float) -> None:
        self.fn(canvas, frame, cam)


class Backdrop:
    def __init__(self, sky: pygame.Surface, items: list, theme: str = ""):
        self.sky, self.items, self.theme = (sky.convert() if pygame.display.get_surface() is not None else sky), items, theme

    def draw(self, canvas: pygame.Surface, frame: int, cam: float = 0.0) -> None:
        canvas.blit(self.sky, (0, 0))
        cam = max(-CAM_LIMIT, min(CAM_LIMIT, cam / (U / RS)))  # the camera arrives in world units; scenery thinks in design px
        off = (canvas.get_width() - PIX_W) // 2  # on a wide canvas the arena sits in the middle
        for item in self.items:
            if isinstance(item, Animated):
                pd.ox = off
                try:
                    item.draw(canvas, frame, cam)
                finally:
                    pd.ox = 0
            else:
                item.draw(canvas, frame, cam)
        apply_mood(canvas, self.theme, frame)


def _wide() -> pygame.Surface:
    return pd.surface((W + 2 * MARGIN, H))


# --- Tron-style neon helpers --------------------------------------------------------------------
ACCENT = {"datacenter": (0, 226, 255), "controlplane": (176, 238, 255), "nodepool": (255, 150, 34), "etcd": (110, 255, 176),
          "mesh": (255, 120, 214), "cloud": (255, 214, 236)}
SECOND = {"datacenter": (255, 140, 40), "controlplane": (255, 214, 110), "nodepool": (0, 214, 255), "etcd": (196, 120, 255),
          "mesh": (110, 200, 255), "cloud": (150, 196, 255)}


def _scale(c: Color, k: float) -> Color:
    return tuple(max(0, min(255, int(v * k))) for v in c)  # type: ignore[return-value]


def neon(surf: pygame.Surface, a, b, color: Color, w: int = 1) -> None:
    """A banded glow (dark halo, mid halo, bright core): pixel-art friendly and cheap."""
    pd.line(surf, _scale(color, 0.2), a, b, w + 4)
    pd.line(surf, _scale(color, 0.5), a, b, w + 2)
    pd.line(surf, color, a, b, w)


def neon_rect(surf: pygame.Surface, rect, color: Color, w: int = 1) -> None:
    x, y, rw, rh = rect
    for a, b in (((x, y), (x + rw, y)), ((x + rw, y), (x + rw, y + rh)), ((x + rw, y + rh), (x, y + rh)), ((x, y + rh), (x, y))):
        neon(surf, a, b, color, w)


def grid_floor(canvas: pygame.Surface, frame: int, cam: float, horizon: int, color: Color, speed: float = 0.012,
               fade: float = 1.0) -> None:
    """The Grid: a perspective floor whose cross-lines roll toward the viewer."""
    vp = 320 - cam * 0.12
    depth = H - horizon
    for k in range(-26, 27):  # lines converging on the vanishing point
        bx = vp + k * 70
        t = abs(k) / 26
        pd.line(canvas, _scale(color, (0.5 - 0.35 * t) * fade), (vp + (bx - vp) * 0.03, horizon), (bx, H), 1)
    n = 16
    pulse = (frame * 0.0045) % 1.4  # a faint ripple that drifts toward the viewer every few seconds
    for i in range(n):  # cross lines, nearer ones farther apart
        u = ((i + (frame * speed) % 1.0) / n) ** 2.1
        y = horizon + depth * u
        k = 0.25 + 0.75 * u
        boost = max(0.0, 1 - abs(u - pulse) / 0.09)
        pd.line(canvas, _scale(color, (0.22 + 0.5 * k) * fade + boost * 0.35), (-EXTRA, int(y)), (W + EXTRA, int(y)), 1 if u < 0.6 else 2)
    pd.line(canvas, _scale(color, 1.0 * fade), (-EXTRA, horizon), (W + EXTRA, horizon), 1)  # bright horizon seam


def reflection(layer: pygame.Surface, ground: int, depth: int = 64, strength: int = 110) -> pygame.Surface:
    """A faded, upside-down copy of a scenery layer for the shiny floor under it. `ground` is in design px."""
    gy, dh = round(ground * U), round(depth * U)
    w = layer.get_width()
    ref = pygame.transform.flip(layer.subsurface((0, max(0, gy - dh), w, min(dh, gy))).copy(), False, True)
    fade = pygame.Surface(ref.get_size(), pygame.SRCALPHA)
    for y in range(ref.get_height()):
        a = int(strength * (1 - y / ref.get_height()) ** 1.5)
        pygame.draw.line(fade, (255, 255, 255, a), (0, y), (w, y))
    ref.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return ref


def light_cycle(canvas: pygame.Surface, frame: int, cam: float, horizon: int, color: Color, depth_t: float,
                speed: float, phase: float, direction: int = 1) -> None:
    """A light-cycle streaking across the grid, leaving a fading ribbon of light."""
    y = int(horizon + (H - horizon) * depth_t ** 2.1)
    span = W + 360
    x = (frame * speed * direction + phase) % span - 180
    size = 1 + int(depth_t * 3)
    for k in range(9):  # trail
        tx = x - direction * k * (10 + depth_t * 8)
        pd.line(canvas, _scale(color, 1.0 - k * 0.11), (tx, y), (tx - direction * (10 + depth_t * 8), y), size)
    pd.rect(canvas, (255, 255, 255), (int(x) - 3 * size, y - 2 * size, 6 * size, 3 * size))
    pd.rect(canvas, color, (int(x) - 4 * size, y - 3 * size, 8 * size, size))


def _mute(surf: pygame.Surface, k: float, tint: Color = (8, 14, 36), desat: float = 0.3) -> None:
    """Push a scenery layer back: lower its contrast, drain some colour and blend it toward the dark ambient tint.
    Background art in 16-bit games sits in a hazy mid-value range so the fighters and platforms always read first."""
    rgb = pygame.surfarray.pixels3d(surf)
    live = (pygame.surfarray.pixels_alpha(surf) > 0)[..., None]
    gray = rgb.mean(axis=2, keepdims=True)
    out = (rgb * (1 - desat) + gray * desat) * k + np.array(tint) * (1 - k)
    rgb[:] = np.where(live, out, rgb).astype(rgb.dtype)


def _greeble(surf, x, y, w, h, accent, rng, density=1.0, dark=(4, 8, 20)):
    """Fine machine detail at sub-unit scale: vent slats, label plates, rivet rows, panel seams and tiny status lights.
    Only the hi-res canvas can show it; it is dim and static, so it adds richness without competing with the fighters."""
    n = int(w * h / 240 * density)
    leds = ((90, 255, 160), accent, (255, 190, 80))
    for _ in range(n):
        kind = rng.random()
        px, py = x + rng.random() * w, y + rng.random() * h
        if kind < 0.28:  # vent slats
            for j in range(rng.randint(3, 5)):
                pd.rect(surf, dark, (px, py + j * 1.3, rng.uniform(4, 8), 0.55))
        elif kind < 0.48:  # a label plate with a lit edge
            pw = rng.uniform(3.5, 7)
            pd.rect(surf, _scale(accent, 0.09), (px, py, pw, 1.8))
            pd.rect(surf, _scale(accent, 0.24), (px, py, pw, 0.45))
        elif kind < 0.68:  # a row of rivets
            for j in range(rng.randint(3, 6)):
                pd.rect(surf, _scale(accent, 0.2), (px + j * 1.7, py, 0.55, 0.55))
        elif kind < 0.84:  # a panel seam
            pd.line(surf, _scale(accent, 0.10), (px, py), (px, py + rng.uniform(5, 13)), 1)
        else:  # a cluster of tiny status lights
            for j in range(rng.randint(2, 3)):
                pd.rect(surf, _scale(rng.choice(leds), 0.34), (px + j * 1.5, py, 0.7, 0.7))


def _tower(surf, x, top, w, ground, accent, rng, led_out=None, leds=True, dark=(8, 12, 28)):
    h = ground - top
    for yy in range(top, ground):
        pd.line(surf, _lerp((18, 26, 60), dark, (yy - top) / max(1, h)), (x, yy), (x + w, yy))
    neon(surf, (x, top), (x, ground), _scale(accent, 0.9), 1)
    neon(surf, (x + w, top), (x + w, ground), _scale(accent, 0.55), 1)
    pd.line(surf, accent, (x, top), (x + w, top), 2)
    for yy in range(top + 8, ground - 6, 9):
        pd.rect(surf, (10, 16, 40), (x + 5, yy, w - 10, 6))
        pd.line(surf, _scale(accent, 0.3), (x + 5, yy), (x + w - 6, yy))
        if leds and led_out is not None:
            for k in range(3):
                led_out.append((x + 8 + k * 5, yy + 2, rng.randint(0, 6),
                                rng.choice([(90, 255, 160), accent, (255, 190, 80)])))
    _greeble(surf, x + 3, top + 3, w - 6, h - 6, accent, rng, 1.3)


# --- whimsy: small, dim props that give each arena a bit of character without competing with the fight -------------
def _duck(surf, x, y, s=1.0):  # a rubber duck: the debugger's best friend
    pd.ellipse(surf, (232, 196, 52), (x - 5 * s, y - 4 * s, 10 * s, 6 * s))
    pd.circle(surf, (240, 206, 60), (x + 3 * s, y - 6 * s), 3 * s)
    pd.polygon(surf, (236, 130, 40), [(x + 5.6 * s, y - 6.4 * s), (x + 8.4 * s, y - 5.6 * s), (x + 5.6 * s, y - 4.8 * s)])
    pd.circle(surf, (30, 20, 20), (x + 3.4 * s, y - 6.6 * s), 0.6 * s)
    pd.lines(surf, (200, 160, 36), False, [(x - 4 * s, y - 2.4 * s), (x - 1 * s, y - 1.2 * s), (x + 1 * s, y - 2.6 * s)], 1)


def _cat(surf, x, y, s=1.0):  # a cat asleep on a warm server, with a couple of z's
    pd.ellipse(surf, (80, 76, 96), (x - 8 * s, y - 6 * s, 16 * s, 7 * s))
    pd.circle(surf, (86, 82, 102), (x + 6 * s, y - 5 * s), 3.4 * s)
    pd.polygon(surf, (86, 82, 102), [(x + 4 * s, y - 7.6 * s), (x + 5.4 * s, y - 10 * s), (x + 6.6 * s, y - 7.8 * s)])
    pd.polygon(surf, (86, 82, 102), [(x + 7 * s, y - 7.8 * s), (x + 8.6 * s, y - 10 * s), (x + 9 * s, y - 7 * s)])
    pd.lines(surf, (60, 56, 76), False, [(x - 7 * s, y - 1 * s), (x - 12 * s, y - 2 * s), (x - 13 * s, y - 5 * s)], 1)  # the tail
    pd.line(surf, (50, 46, 66), (x + 5 * s, y - 5.2 * s), (x + 6.6 * s, y - 5.2 * s), 0.5)
    for k in range(2):
        zx, zy = x + 10 * s + k * 3.6 * s, y - 11 * s - k * 4 * s
        pd.lines(surf, (150, 160, 210), False, [(zx, zy), (zx + 2.4 * s, zy), (zx, zy + 2.4 * s), (zx + 2.4 * s, zy + 2.4 * s)], 1)


def _mug(surf, x, y, s=1.0):  # a coffee mug with steam
    pd.rect(surf, (210, 210, 224), (x - 3 * s, y - 5 * s, 6 * s, 5 * s))
    pd.circle(surf, (210, 210, 224), (x + 3.4 * s, y - 2.6 * s), 1.8 * s, 1)
    pd.rect(surf, (120, 80, 50), (x - 2.4 * s, y - 4.6 * s, 4.8 * s, 1 * s))
    for k in range(2):
        pd.lines(surf, (130, 140, 170), False, [(x - 1 * s + k * 2 * s + math.sin(i) * 0.9, y - 6.6 * s - i * 1.6 * s) for i in range(5)], 1)


def _sign(surf, x, y, s=1.0):  # a hanging sign
    pd.line(surf, (60, 66, 90), (x - 5 * s, y - 8 * s), (x - 5 * s, y), 1)
    pd.line(surf, (60, 66, 90), (x + 5 * s, y - 8 * s), (x + 5 * s, y), 1)
    pd.rect(surf, (200, 60, 60), (x - 8 * s, y, 16 * s, 7 * s))
    pd.rect(surf, (240, 220, 220), (x - 6.4 * s, y + 1.6 * s, 12.8 * s, 0.9 * s))
    pd.rect(surf, (240, 220, 220), (x - 6.4 * s, y + 3.6 * s, 9 * s, 0.9 * s))


def _bonsai(surf, x, y, s=1.0):  # a little bonsai on a console
    pd.polygon(surf, (150, 90, 60), [(x - 5 * s, y - 5 * s), (x + 5 * s, y - 5 * s), (x + 3.4 * s, y), (x - 3.4 * s, y)])
    pd.lines(surf, (110, 76, 54), False, [(x, y - 5 * s), (x - 1 * s, y - 9 * s), (x + 1.4 * s, y - 12 * s), (x, y - 15 * s)], 2)
    for dx, dy, r in ((-4, -13, 4), (4, -15, 4.4), (0, -19, 4.6), (-1, -14.6, 3.6)):
        pd.circle(surf, (50, 130, 90), (x + dx * s, y + dy * s), r * s)
        pd.circle(surf, (80, 170, 116), (x + (dx - 1) * s, y + (dy - 1) * s), r * 0.55 * s)


def _trophy(surf, x, y, s=1.0):  # a golden trophy for the elected leader
    pd.rect(surf, (140, 110, 40), (x - 4 * s, y - 3 * s, 8 * s, 3 * s))
    pd.rect(surf, (200, 160, 50), (x - 1 * s, y - 8 * s, 2 * s, 5 * s))
    pd.polygon(surf, (236, 190, 60), [(x - 5 * s, y - 16 * s), (x + 5 * s, y - 16 * s), (x + 3.4 * s, y - 8 * s), (x - 3.4 * s, y - 8 * s)])
    pd.lines(surf, (236, 190, 60), False, [(x - 5 * s, y - 15 * s), (x - 8 * s, y - 13 * s), (x - 5 * s, y - 10 * s)], 1)
    pd.lines(surf, (236, 190, 60), False, [(x + 5 * s, y - 15 * s), (x + 8 * s, y - 13 * s), (x + 5 * s, y - 10 * s)], 1)
    pd.line(surf, (255, 240, 170), (x - 2.6 * s, y - 15 * s), (x - 2 * s, y - 10 * s), 1)


def _pennant(surf, x, y, s=1.0, color=(200, 160, 50)):  # a hanging banner with a crown
    pd.line(surf, (70, 70, 100), (x - 6 * s, y), (x + 6 * s, y), 1)
    pd.polygon(surf, color, [(x - 5.4 * s, y), (x + 5.4 * s, y), (x + 5.4 * s, y + 14 * s), (x, y + 18 * s), (x - 5.4 * s, y + 14 * s)])
    pd.polygon(surf, (255, 240, 170), [(x - 3 * s, y + 10 * s), (x - 3.4 * s, y + 5 * s), (x - 1.4 * s, y + 7.4 * s), (x, y + 4 * s),
                                       (x + 1.4 * s, y + 7.4 * s), (x + 3.4 * s, y + 5 * s), (x + 3 * s, y + 10 * s)])


def _sleepy_face(surf, x, y, asleep: bool):  # a pod in its cell, asleep (z) or smiling
    c = (30, 14, 8)
    if asleep:
        pd.lines(surf, c, False, [(x - 3.4, y - 1.6), (x - 2.2, y - 0.8), (x - 1, y - 1.6)], 1)
        pd.lines(surf, c, False, [(x + 1, y - 1.6), (x + 2.2, y - 0.8), (x + 3.4, y - 1.6)], 1)
        pd.lines(surf, (190, 180, 210), False, [(x + 5, y - 6), (x + 7.4, y - 6), (x + 5, y - 3.6), (x + 7.4, y - 3.6)], 1)
    else:
        pd.circle(surf, c, (x - 2, y - 1.4), 0.9)
        pd.circle(surf, c, (x + 2, y - 1.4), 0.9)
        pd.lines(surf, c, False, [(x - 2.4, y + 1.2), (x, y + 2.6), (x + 2.4, y + 1.2)], 1)


def _key(surf, x, y, s=1.0, color=(150, 110, 220)):  # a giant skeleton key stuck in the wall
    pd.circle(surf, color, (x, y), 9 * s, 2)
    pd.circle(surf, _scale(color, 0.4), (x, y), 4 * s)
    pd.rect(surf, color, (x - 1.6 * s, y + 9 * s, 3.2 * s, 36 * s))
    for k, w in enumerate((8, 5, 9)):
        pd.rect(surf, color, (x + 1.6 * s, y + (30 + k * 5) * s, w * s, 2.6 * s))


def _chest(surf, x, y, s=1.0, glow=(110, 255, 176)):  # a treasure chest of data, glowing at the seam
    pd.rect(surf, (96, 70, 56), (x - 7 * s, y - 5 * s, 14 * s, 5 * s))
    pd.polygon(surf, (120, 86, 66), [(x - 7 * s, y - 5 * s), (x - 6 * s, y - 10 * s), (x + 6 * s, y - 10 * s), (x + 7 * s, y - 5 * s)])
    pd.line(surf, glow, (x - 6 * s, y - 5 * s), (x + 6 * s, y - 5 * s), 1)
    pd.rect(surf, (200, 170, 80), (x - 1 * s, y - 6 * s, 2 * s, 2.6 * s))
    pd.polygon(surf, _scale(glow, 0.35), [(x - 5 * s, y - 5.4 * s), (x + 5 * s, y - 5.4 * s), (x + 9 * s, y - 20 * s), (x - 9 * s, y - 20 * s)])


def _bat(surf, x, y, s=1.0):  # a bat asleep, hanging upside down
    pd.ellipse(surf, (40, 34, 60), (x - 2 * s, y, 4 * s, 6 * s))
    pd.polygon(surf, (40, 34, 60), [(x - 2 * s, y + 1 * s), (x - 7 * s, y + 5 * s), (x - 3 * s, y + 6 * s)])
    pd.polygon(surf, (40, 34, 60), [(x + 2 * s, y + 1 * s), (x + 7 * s, y + 5 * s), (x + 3 * s, y + 6 * s)])
    pd.circle(surf, (50, 44, 72), (x, y + 6.4 * s), 2 * s)


def _planet(surf, x, y, r, s=1.0):  # a ringed planet
    pd.ellipse(surf, (150, 90, 170), (x - r * 1.9, y - r * 0.28, r * 3.8, r * 0.56), 1)
    pd.circle(surf, (110, 60, 150), (x, y), r)
    pd.circle(surf, (150, 96, 190), (x - r * 0.28, y - r * 0.3), r * 0.55)
    pd.lines(surf, (190, 130, 210), False, [(x - r * 1.9 + i * r * 0.38, y + math.sin(i / 10 * math.pi) * r * 0.28) for i in range(11)], 1)


def _satellite(surf, x, y, s=1.0):  # a small satellite with solar wings and a dish
    pd.rect(surf, (150, 150, 190), (x - 3 * s, y - 3 * s, 6 * s, 6 * s))
    for sx in (-1, 1):
        pd.rect(surf, (50, 80, 150), (x + sx * 4 * s + (-9 * s if sx < 0 else 0), y - 2 * s, 9 * s, 4 * s))
        for k in range(3):
            pd.line(surf, (110, 150, 220), (x + sx * (7 + k * 2.6) * s, y - 2 * s), (x + sx * (7 + k * 2.6) * s, y + 2 * s), 1)
    pd.line(surf, (190, 190, 220), (x, y - 3 * s), (x, y - 8 * s), 1)
    pd.polygon(surf, (200, 200, 230), [(x - 3 * s, y - 8 * s), (x + 3 * s, y - 8 * s), (x, y - 5.4 * s)])


def _comet(surf, x, y, s=1.0):  # a sleepy comet with a long tail
    for k in range(8):
        pd.circle(surf, tuple(int(c * (1 - k * 0.1)) for c in (200, 190, 230)), (x - k * 5 * s, y - k * 1.4 * s), (3.2 - k * 0.3) * s)
    pd.circle(surf, (230, 224, 250), (x, y), 3.4 * s)
    pd.lines(surf, (60, 50, 90), False, [(x - 1.6 * s, y - 0.4 * s), (x - 0.8 * s, y + 0.4 * s), (x, y - 0.4 * s)], 1)


# --- Datacenter: the server hall, lit like the Grid ---------------------------------------------
def build_datacenter(canvas_w: int = PIX_W) -> Backdrop:
    rng = random.Random(7)
    accent = ACCENT["datacenter"]
    horizon = 214
    sky = dither_gradient(canvas_w, PIX_H, [(0, (2, 4, 14)), (0.35, (4, 10, 36)), (0.56, (8, 36, 92)), (0.595, (34, 150, 210)),
                                 (0.6, (4, 10, 30)), (1.0, (1, 3, 12))], bands=26)

    far = _wide()
    x = 0
    while x < WIDE:  # a distant city of towers on the horizon
        w, h = rng.randint(16, 34), rng.randint(40, 120)
        pd.rect(far, (6, 12, 34), (x, horizon - h, w, h))
        pd.line(far, _scale(accent, 0.7), (x, horizon - h), (x + w, horizon - h), 1)
        pd.line(far, _scale(accent, 0.35), (x, horizon - h), (x, horizon), 1)
        for wy in range(horizon - h + 5, horizon - 3, 6):
            for wx in range(x + 3, x + w - 3, 5):
                if rng.random() < 0.3:
                    pd.set_at(far, (wx, wy), _scale(accent, rng.choice([0.5, 0.8])))
        x += w + rng.randint(1, 6)

    mid = _wide()
    leds: list[tuple[int, int, int, Color]] = []
    tops = []
    for tx in range(8, WIDE - 40, 84):
        w, top = rng.randint(48, 64), 214 - rng.randint(110, 190)
        _tower(mid, tx, top, w, horizon + 6, accent, rng, leds)
        tops.append((tx, w, top))
    cables = []
    for (tx, w, top), (nx, _, ntop) in zip(tops, tops[1:]):
        for k, drop in enumerate((10, 18)):
            y0, y1 = top + 20 + k * 34, ntop + 24 + k * 30
            pts = [(tx + w + (nx - tx - w) * i / 20, y0 + (y1 - y0) * i / 20 + math.sin(i / 20 * math.pi) * drop) for i in range(21)]
            pd.lines(mid, (6, 10, 28), False, pts, 3)
            pd.lines(mid, _scale(accent, 0.6), False, [(px, py - 1) for px, py in pts], 1)
            cables.append(pts)

    near = _wide()
    for gx in (MARGIN - 6, WIDE - MARGIN - 58):  # foreground pillars with neon seams
        pd.rect(near, (4, 6, 18), (gx, 0, 64, H))
        pd.rect(near, (12, 18, 44), (gx + 6, 0, 6, H))
        for yy in range(14, H, 30):
            pd.line(near, _scale(accent, 0.28), (gx + 6, yy), (gx + 58, yy), 1)
            pd.rect(near, _scale(accent, 0.9), (gx + 22, yy + 3, 14, 2))
        neon(near, (gx + (60 if gx < W else 0), 0), (gx + (60 if gx < W else 0), H), accent, 1)
    for gx in (MARGIN - 6, WIDE - MARGIN - 58):
        _greeble(near, gx + 14, 20, 40, H - 40, accent, rng, 1.6)
        for yy in range(6, H, 30):  # hazard-stripe bands across the pillars
            for k in range(0, 56, 6):
                pd.polygon(near, _scale((255, 190, 60), 0.16), [(gx + 4 + k, yy + 24), (gx + 8 + k, yy + 24), (gx + 11 + k, yy + 27), (gx + 7 + k, yy + 27)])
    pd.rect(near, (2, 4, 12), (0, 0, WIDE, 18))  # ceiling with converging light strips
    for k in range(-8, 9):
        neon(near, (WIDE // 2 + k * 60, 0), (WIDE // 2 + k * 18, 18), _scale(accent, 0.8), 1)
    neon(near, (0, 18), (WIDE, 18), _scale(accent, 0.6), 1)

    tx_, w_, top_ = tops[2]  # whimsy: a duck, a cat on a warm server, a mug, a sign
    _duck(mid, tx_ + w_ * 0.4, top_)
    tx_, w_, top_ = tops[4]
    _cat(mid, tx_ + w_ * 0.5, top_)
    tx_, w_, top_ = tops[6]
    _mug(mid, tx_ + w_ * 0.3, top_)
    _sign(mid, tops[3][0] + tops[3][1] + 20, tops[3][2] + 40)
    _mute(far, 0.5)
    _mute(mid, 0.62)
    _mute(near, 0.74)

    def led_fn(canvas, frame, cam):  # status lights: dim, and they change rarely
        ox = -MARGIN - cam * 0.09
        for x, y, ph, col in leds:
            if ((frame + ph * 9) // 50 + ph) % (5 + int(REACT['energy'] * 3)) != 0:  # staggered, so they never flip in unison
                pd.fill(canvas, _scale(col, 0.55), (int(x + ox), y, 2, 1))

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent, speed=0.003, fade=0.5)

    panels = [(92, 44, 86, 50, 0.0), (468, 58, 92, 52, 2.1)]

    def holo_fn(canvas, frame, cam):  # wall displays: dim, with slowly drifting bars
        ox = -cam * 0.07
        for x, y, w, h, seed in panels:
            pd.rect(canvas, (4, 12, 30), (x + ox, y, w, h))
            neon_rect(canvas, (x + ox, y, w, h), _scale(accent, 0.38))
            bars = 7
            for i in range(bars):
                bh = min(1.0, (0.3 + 0.7 * abs(math.sin(frame * 0.008 + i * 1.3 + seed))) * (0.75 + 0.45 * REACT['energy'])) * (h - 16)
                pd.fill(canvas, _scale(accent, 0.4), (x + ox + 5 + i * (w - 10) / bars, y + h - 5 - bh, (w - 10) / bars - 2, bh))


    def haze_fn(canvas, frame, cam):
        haze_band(canvas, horizon, _scale(accent, 0.45), 80, 80)

    items = [Layer(far, 0.03, 0), Animated(haze_fn), Animated(floor_fn), Layer(reflection(mid, horizon + 6, strength=70), 0.09, horizon + 6),
             Layer(mid, 0.09, 0), Animated(holo_fn), Animated(led_fn), Layer(near, 0.13, 0)]
    return Backdrop(sky, items, 'datacenter')


# --- Control Plane: the core chamber with a hologram of the helm wheel -----------------------------
def build_controlplane(canvas_w: int = PIX_W) -> Backdrop:
    rng = random.Random(11)
    accent, gold = ACCENT["controlplane"], SECOND["controlplane"]
    horizon = 236
    sky = dither_gradient(canvas_w, PIX_H, [(0, (3, 6, 24)), (0.4, (8, 18, 62)), (0.62, (22, 58, 140)), (0.655, (110, 190, 255)),
                                 (0.66, (4, 8, 28)), (1.0, (1, 3, 12))], bands=26)

    far = _wide()
    cx, cy = WIDE // 2, 120
    for r in (210, 176, 142, 108):  # concentric portal rings in the back wall
        pd.circle(far, _scale(accent, 0.18), (cx, cy), r, 2)
    for k in range(48):
        a = k * math.pi / 24
        pd.line(far, _scale(accent, 0.1), (cx + math.cos(a) * 108, cy + math.sin(a) * 108),
                         (cx + math.cos(a) * 214, cy + math.sin(a) * 214), 1)
    for hx in range(-30, WIDE + 30, 52):  # hex-panel wall along the lower back
        for row, hy in enumerate(range(150, 236, 30)):
            ox = hx + (26 if row % 2 else 0)
            pts = [(ox + math.cos(a * math.pi / 3 + math.pi / 6) * 22, hy + math.sin(a * math.pi / 3 + math.pi / 6) * 22) for a in range(6)]
            pd.polygon(far, _scale(accent, 0.12), pts, 1)
            pd.polygon(far, _scale(accent, 0.06), [(ox + (px_ - ox) * 0.72, hy + (py_ - hy) * 0.72) for px_, py_ in pts], 1)
            for a_ in range(0, 6, 2):  # a tiny circuit node on alternate corners
                pd.rect(far, _scale(accent, 0.2), (pts[a_][0] - 0.5, pts[a_][1] - 0.5, 1, 1))
            if rng.random() < 0.18:
                pd.polygon(far, (16, 52, 104), pts)

    mid = _wide()
    tubes = []
    for tx in (MARGIN + 70, MARGIN + 170, W + MARGIN - 190, W + MARGIN - 90):  # glass data conduits
        pd.rect(mid, (8, 18, 52), (tx, 30, 26, horizon - 24), border_radius=10)
        neon_rect(mid, (tx, 30, 26, horizon - 24), _scale(accent, 0.8))
        for yy in range(52, horizon - 4, 26):
            pd.line(mid, _scale(accent, 0.3), (tx + 3, yy), (tx + 23, yy), 1)
        tubes.append(tx)
    for tx in tubes:  # fine rings and bubbles inside the glass conduits
        for yy in range(40, horizon - 8, 13):
            pd.rect(mid, _scale(accent, 0.16), (tx + 5 + (yy * 7) % 11, yy, 1.1, 1.1))
            pd.line(mid, _scale(accent, 0.12), (tx + 2, yy + 5), (tx + 24, yy + 5), 1)
    for sx, w in ((MARGIN + 250, 36), (W + MARGIN - 286, 36)):  # server spines behind the core
        _tower(mid, sx, 120, w, horizon + 6, accent, rng, None, leds=False)

    near = _wide()
    for gx, side in ((MARGIN - 6, 0), (WIDE - MARGIN - 52, 1)):  # arched ribs with gold trim
        pd.rect(near, (4, 8, 24), (gx, 0, 58, H))
        pd.rect(near, (14, 26, 70), (gx + (46 if side == 0 else 0), 0, 12, H))
        neon(near, (gx + (58 if side == 0 else 0), 0), (gx + (58 if side == 0 else 0), H), gold, 1)
        for yy in range(24, H, 36):
            pd.polygon(near, _scale(accent, 0.55), [(gx, yy), (gx + 58, yy + 6), (gx + 58, yy + 10), (gx, yy + 4)])
    for gx in (MARGIN - 6, WIDE - MARGIN - 52):
        _greeble(near, gx + 2, 14, 54, H - 30, accent, rng, 1.5)
    pd.rect(near, (3, 6, 20), (0, 0, WIDE, 12))
    neon(near, (0, 12), (WIDE, 12), gold, 1)

    _bonsai(mid, MARGIN + 126, horizon + 4)  # whimsy: a bonsai, a trophy and leader banners
    _trophy(mid, W + MARGIN - 128, horizon + 4)
    for bx in (MARGIN + 208, MARGIN + 432):
        _pennant(mid, bx, 28)
    _mute(far, 0.5)
    _mute(mid, 0.62)
    _mute(near, 0.74)

    def holo_fn(canvas, frame, cam):  # the big slow hologram wheel: the one large moving shape in the room
        hx, hy, r = int(320 - cam * 0.03), 128, 78
        beam = pd.surface((r * 2, 130))  # projector cone down to the floor
        for yy in range(130):
            half = int(r * (0.35 + yy / 130 * 0.5))
            pd.line(beam, accent + (int(14 * (1 - yy / 130)),), (r - half, yy), (r + half, yy))
        pd.blit(canvas, beam, (hx - r, hy + 56))
        pd.circle(canvas, _scale(accent, 0.34), (hx, hy), r, 2)
        pd.circle(canvas, _scale(accent, 0.2), (hx, hy), r - 5, 1)
        pd.circle(canvas, _scale(gold, 0.5), (hx, hy), 13, 2)
        for i in range(8):
            a = frame * 0.0025 + i * math.pi / 4
            pd.line(canvas, _scale(accent, 0.34), (hx + math.cos(a) * 13, hy + math.sin(a) * 13),
                    (hx + math.cos(a) * r, hy + math.sin(a) * r), 1)
            pd.circle(canvas, _scale(gold, 0.45), (hx + math.cos(a) * (r + 10), hy + math.sin(a) * (r + 10)), 4, 1)

    def orbit_fn(canvas, frame, cam):  # faint tilted rings, nothing riding on them
        hx, hy = 320 - cam * 0.03, 128
        for rx, ry, tilt, color in ((128, 36, 0.32, accent), (100, 28, -0.55, gold), (160, 52, 0.95, accent)):
            ct, st = math.cos(tilt), math.sin(tilt)
            pts = [(hx + math.cos(a) * rx * ct - math.sin(a) * ry * st, hy + math.cos(a) * rx * st + math.sin(a) * ry * ct)
                   for a in (i / 72 * math.tau for i in range(72))]
            pd.lines(canvas, _scale(color, 0.22), True, pts, 1)

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent, speed=0.0025, fade=0.46)

    crown = {"x": 0.0}

    def haze_fn(canvas, frame, cam):
        haze_band(canvas, horizon, _scale(accent, 0.4), 80, 76)

    def crown_fn(canvas, frame, cam):  # the leader's crown: it glides to whichever side is winning, slowly
        crown["x"] += (REACT["leader"] - crown["x"]) * 0.01
        cx = 320 - cam * 0.03 + crown["x"] * 112
        cy = 30 + math.sin(frame * 0.03) * 2
        col = _scale(gold, 0.6)
        pd.polygon(canvas, col, [(cx - 9, cy + 8), (cx - 11, cy - 4), (cx - 5, cy + 2), (cx, cy - 8), (cx + 5, cy + 2),
                                 (cx + 11, cy - 4), (cx + 9, cy + 8)])
        pd.line(canvas, _scale(gold, 0.85), (cx - 9, cy + 8), (cx + 9, cy + 8), 2)
        pd.circle(canvas, _scale(gold, 0.95), (cx, cy - 8), 2)

    items = [Layer(far, 0.02, 0), Animated(haze_fn), Animated(holo_fn), Animated(orbit_fn), Animated(crown_fn), Animated(floor_fn),
             Layer(reflection(mid, horizon + 6, strength=70), 0.08, horizon + 6), Layer(mid, 0.08, 0), Layer(near, 0.13, 0)]
    return Backdrop(sky, items, 'controlplane')


# --- Node Pool: an amber hot-aisle pod bay with honeycomb pod cells --------------------------------
def build_nodepool(canvas_w: int = PIX_W) -> Backdrop:
    rng = random.Random(23)
    accent, cyan = ACCENT["nodepool"], SECOND["nodepool"]
    horizon = 222
    sky = dither_gradient(canvas_w, PIX_H, [(0, (6, 2, 4)), (0.35, (22, 6, 8)), (0.56, (74, 22, 10)), (0.605, (255, 140, 34)),
                                 (0.61, (10, 4, 6)), (1.0, (3, 1, 2))], bands=26)

    far = _wide()
    pods = []
    for row, hy in enumerate(range(20, 218, 26)):  # honeycomb wall of pod cells
        for hx in range(-20, WIDE + 20, 30):
            ox = hx + (15 if row % 2 else 0)
            pts = [(ox + math.cos(a * math.pi / 3 + math.pi / 6) * 15.5, hy + math.sin(a * math.pi / 3 + math.pi / 6) * 15.5) for a in range(6)]
            pd.polygon(far, _scale(accent, 0.13), pts, 1)
            pd.polygon(far, _scale(accent, 0.07), [(ox + (px_ - ox) * 0.78, hy + (py_ - hy) * 0.78) for px_, py_ in pts], 1)
            roll = rng.random()
            if roll < 0.22:
                pd.polygon(far, _scale(accent, 0.2), pts)
                pd.ellipse(far, _scale(accent, 0.8), (ox - 4, hy - 7, 8, 14))  # a pod in its cell
                pods.append((ox, hy, rng.randint(0, 6)))
            elif roll < 0.27:
                pd.ellipse(far, _scale(cyan, 0.7), (ox - 4, hy - 7, 8, 14))

    mid = _wide()
    leds: list[tuple[int, int, int, Color]] = []
    pipes = []
    for tx in range(20, WIDE - 40, 120):
        w, top = rng.randint(64, 84), 222 - rng.randint(70, 150)
        _tower(mid, tx, top, w, horizon + 6, accent, rng, leds)
        for k in range(rng.randint(2, 3)):  # pod cartridges
            py = top + 14 + k * 28
            for px in range(tx + 8, tx + w - 14, 14):
                pd.rect(mid, (36, 12, 8), (px, py, 10, 20), border_radius=4)
                pd.rect(mid, _scale(accent, rng.choice([0.4, 0.7, 1.0])), (px + 2, py + 3, 6, 14), border_radius=3)
        pipes.append((tx + w, 196 + rng.randint(-8, 12)))
    for (px, py), (nx, _) in zip(pipes, pipes[1:]):  # coolant pipes between the racks
        pd.rect(mid, (24, 12, 12), (px, py, nx - px - 0, 8))
        pd.line(mid, _scale(accent, 0.7), (px, py + 1), (nx, py + 1), 1)
        pd.line(mid, (6, 2, 2), (px, py + 7), (nx, py + 7), 1)
        for jx in range(int(px) + 6, int(nx) - 4, 14):  # pipe flanges and bolts
            pd.rect(mid, (40, 20, 18), (jx, py - 1, 2, 10))
            pd.rect(mid, _scale(accent, 0.3), (jx, py + 2, 0.7, 0.7))

    near = _wide()
    for gx in (MARGIN - 8, WIDE - MARGIN - 56):
        pd.rect(near, (6, 2, 4), (gx, 0, 64, H))
        pd.rect(near, (28, 10, 8), (gx + 6, 0, 8, H))
        for yy in range(10, H, 34):
            pd.rect(near, (60, 20, 10), (gx + 14, yy, 40, 14))
            pd.line(near, accent, (gx + 14, yy + 14), (gx + 54, yy + 14), 1)
            for k in range(4):
                pd.circle(near, rng.choice([(90, 255, 140), accent, (255, 80, 60)]), (gx + 20 + k * 9, yy + 6), 2)
        neon(near, (gx + (62 if gx < W else 2), 0), (gx + (62 if gx < W else 2), H), accent, 1)
    for gx in (MARGIN - 8, WIDE - MARGIN - 56):
        _greeble(near, gx + 14, 4, 42, H - 8, accent, rng, 1.4, dark=(10, 4, 4))
    pd.rect(near, (4, 2, 3), (0, 0, WIDE, 14))
    for k in range(0, WIDE, 44):  # hanging cable swags
        pd.lines(near, (20, 8, 8), False, [(k + i * 4, 14 + math.sin(i / 11 * math.pi) * 9) for i in range(12)], 2)

    for i, (px_, py_, ph_) in enumerate(pods):  # whimsy: every pod has a little face, some asleep
        _sleepy_face(far, px_, py_ + 1.5, asleep=(i % 3 != 0))
    _mute(far, 0.5)
    _mute(mid, 0.62)
    _mute(near, 0.74)

    def led_fn(canvas, frame, cam):  # status lights: dim, and they change rarely
        for x, y, ph, col in leds:
            if ((frame + ph * 9) // 50 + ph) % (5 + int(REACT['energy'] * 3)) != 0:  # staggered, so they never flip in unison
                pd.fill(canvas, _scale(col, 0.55), (int(x - MARGIN - cam * 0.09), y, 2, 1))

    fans = [(110, 78), (320, 62), (530, 84)]

    def fan_fn(canvas, frame, cam):  # big, slow exhaust fans in the honeycomb wall
        ox = -cam * 0.035
        for i, (fx, fy) in enumerate(fans):
            cx = fx + ox
            pd.circle(canvas, (10, 5, 6), (cx, fy), 27)
            pd.circle(canvas, _scale(accent, 0.34), (cx, fy), 27, 2)
            for b in range(5):
                a = frame * (0.007 if i % 2 else -0.006) + b * math.tau / 5
                pd.polygon(canvas, _scale(accent, 0.26), [(cx, fy), (cx + math.cos(a - 0.3) * 24, fy + math.sin(a - 0.3) * 24),
                                                          (cx + math.cos(a + 0.28) * 24, fy + math.sin(a + 0.28) * 24)])
            pd.circle(canvas, _scale(accent, 0.5), (cx, fy), 5)

    steam = [(rng.uniform(0, W), rng.uniform(0, 80), rng.uniform(0.25, 0.5)) for _ in range(8)]

    def steam_fn(canvas, frame, cam):  # soft, slow, low-contrast vapour
        for i, (x, y0, sp) in enumerate(steam):
            t = (frame * sp * 0.6 + y0 * 3) % 150
            yy, rr = horizon + 6 - t * 1.2, 4 + t * 0.07
            puff = pd.surface((28, 28))
            pd.circle(puff, (200, 140, 100, int(20 * (1 - t / 150))), (14, 14), int(rr))
            pd.blit(canvas, puff, (int(x - cam * 0.1 + math.sin(t * 0.05 + i) * 5) - 14, int(yy) - 14))

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent, speed=0.003, fade=0.5)

    def haze_fn(canvas, frame, cam):
        haze_band(canvas, horizon, _scale(accent, 0.4), 80, 76)

    def ko_lamps_fn(canvas, frame, cam):  # a row of pod lamps on the far wall: one lights up for every KO so far
        ox = -cam * 0.05
        for i in range(8):
            lit = i < REACT["kos"]
            x = 232 + i * 16 + ox
            pd.rect(canvas, (6, 10, 24), (x - 1, 17, 12, 9))
            pd.rect(canvas, _scale(accent, 0.8) if lit else _scale(accent, 0.18), (x + 1, 19, 8, 5))

    items = [Layer(far, 0.03, 0), Animated(haze_fn), Animated(fan_fn), Animated(ko_lamps_fn), Animated(floor_fn),
             Layer(reflection(mid, horizon + 6, strength=70), 0.09, horizon + 6), Layer(mid, 0.09, 0),
             Animated(led_fn), Animated(steam_fn), Layer(near, 0.13, 0)]
    return Backdrop(sky, items, 'nodepool')


# --- Etcd Vault: a crystal archive where the cluster keeps its state --------------------------------------
def _crystal(surf, x, base, w, h, color, rng, glow=0.5):
    """A tall hexagonal crystal column: two lit facets and a dark one, with a pointed tip and faint inner light."""
    tip = base - h
    left, right = (x, base), (x + w, base)
    pd.polygon(surf, _scale(color, 0.10), [left, (x, tip + w * 0.5), (x + w * 0.5, tip), (x + w * 0.5, base)])
    pd.polygon(surf, _scale(color, 0.20), [(x + w * 0.5, base), (x + w * 0.5, tip), (x + w, tip + w * 0.5), right])
    pd.line(surf, _scale(color, glow), (x + w * 0.5, tip), (x + w * 0.5, base), 1)
    pd.lines(surf, _scale(color, glow * 0.8), False, [(x, base), (x, tip + w * 0.5), (x + w * 0.5, tip), (x + w, tip + w * 0.5), (x + w, base)], 1)
    for yy in range(int(tip + w * 0.9), int(base) - 4, 11):  # etched rows of keys and values
        if rng.random() < 0.7:
            pd.rect(surf, _scale(color, 0.28), (x + 4 + rng.randint(0, 4), yy, rng.randint(4, int(w * 0.5)), 2))


def build_etcd(canvas_w: int = PIX_W) -> Backdrop:
    rng = random.Random(23)
    accent, violet = ACCENT["etcd"], SECOND["etcd"]
    horizon = 240
    sky = dither_gradient(canvas_w, PIX_H, [(0, (2, 8, 12)), (0.42, (4, 24, 28)), (0.62, (12, 66, 60)), (0.665, (70, 210, 170)),
                                 (0.67, (3, 10, 12)), (1.0, (1, 4, 6))], bands=26)
    far = _wide()
    x = 0
    while x < WIDE:  # a distant range of small crystals
        w, h = rng.randint(14, 26), rng.randint(30, 90)
        _crystal(far, x, horizon, w, h, accent, rng, 0.45)
        x += w + rng.randint(-4, 6)
    mid = _wide()
    for cx in range(10, WIDE - 40, 74):  # the great columns
        w, h = rng.randint(34, 50), rng.randint(110, 200)
        _crystal(mid, cx, horizon + 6, w, h, accent if rng.random() < 0.7 else violet, rng, 0.6)
    near = _wide()
    for gx in (MARGIN - 8, WIDE - MARGIN - 56):  # carved stone pillars with glowing runes
        pd.rect(near, (3, 8, 12), (gx, 0, 64, H))
        pd.rect(near, (10, 24, 30), (gx + 6, 0, 8, H))
        for yy in range(16, H, 34):
            pd.rect(near, _scale(violet, 0.6), (gx + 24, yy, 10, 2))
            pd.lines(near, _scale(violet, 0.38), False, [(gx + 20, yy + 6), (gx + 29, yy + 12), (gx + 38, yy + 6)], 1)
        neon(near, (gx + (60 if gx < W else 0), 0), (gx + (60 if gx < W else 0), H), accent, 1)
    pd.rect(near, (2, 6, 8), (0, 0, WIDE, 20))
    for k in range(-9, 10):  # stalactite crystals along the ceiling
        cx = WIDE // 2 + k * 52
        pd.polygon(near, _scale(accent, 0.16), [(cx - 8, 20), (cx + 8, 20), (cx + rng.randint(-2, 2), 20 + rng.randint(10, 26))])
    neon(near, (0, 20), (WIDE, 20), _scale(accent, 0.5), 1)
    _key(mid, MARGIN + 60, 48, 0.9)  # whimsy: a giant key, two chests of data and sleeping bats
    _chest(mid, MARGIN + 142, horizon + 4, 1.1)
    _chest(mid, W + MARGIN - 150, horizon + 4, 1.1, glow=(200, 120, 255))
    for bx in (MARGIN + 190, MARGIN + 300, MARGIN + 470):
        _bat(near, bx, 22 + (bx % 7))
    _mute(far, 0.5)
    _mute(mid, 0.62)
    _mute(near, 0.74)
    cubes = [(86, 70, 0.0), (210, 100, 1.7), (430, 52, 3.1), (560, 92, 4.4), (330, 130, 5.6)]

    def cubes_fn(canvas, frame, cam):  # key-value cubes drifting in the air: big, dim and very slow
        ox = -cam * 0.08
        for x, y, ph in cubes:
            yy = y + math.sin(frame * 0.012 + ph) * 3.5
            for dx, dy, c in ((0, 0, 0.22), (6, -3, 0.34), (0, -6, 0.5)):
                pd.polygon(canvas, _scale(accent if ph < 3 else violet, c), [(x + ox + dx, yy + dy), (x + ox + dx + 12, yy + dy), (x + ox + dx + 12, yy + dy + 12), (x + ox + dx, yy + dy + 12)])
            neon_rect(canvas, (x + ox, yy, 12, 12), _scale(accent if ph < 3 else violet, 0.55))

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent, speed=0.003, fade=0.5)

    def haze_fn(canvas, frame, cam):
        haze_band(canvas, horizon, _scale(accent, 0.4), 90, 80)

    items = [Layer(far, 0.03, 0), Animated(haze_fn), Animated(floor_fn), Layer(reflection(mid, horizon + 6, strength=70), 0.09, horizon + 6),
             Layer(mid, 0.09, 0), Animated(cubes_fn), Layer(near, 0.13, 0)]
    return Backdrop(sky, items, "etcd")


# --- Service Mesh: islands in a night sky under a web of nodes ---------------------------------------------------
def build_mesh(canvas_w: int = PIX_W) -> Backdrop:
    rng = random.Random(31)
    accent, blue = ACCENT["mesh"], SECOND["mesh"]
    sky = dither_gradient(canvas_w, PIX_H, [(0, (6, 2, 18)), (0.35, (14, 6, 40)), (0.6, (40, 16, 86)), (0.82, (110, 40, 130)),
                                 (1.0, (30, 12, 56))], bands=28)
    far = _wide()
    for _ in range(150):  # a dim, static starfield
        pd.set_at(far, (rng.randrange(WIDE), rng.randrange(int(H * 0.8))), _scale((200, 190, 255), rng.choice([0.25, 0.4, 0.6])))
    nodes = []
    for _ in range(26):
        nodes.append((rng.randrange(40, WIDE - 40), rng.randrange(24, 230)))
    mid = _wide()
    for i, (nx, ny) in enumerate(nodes):  # the mesh: each node links to its two nearest neighbours
        near_ = sorted(nodes, key=lambda q: (q[0] - nx) ** 2 + (q[1] - ny) ** 2)[1:3]
        for mx, my in near_:
            pd.line(mid, _scale(blue, 0.22), (nx, ny), (mx, my), 1)
    for nx, ny in nodes:
        hexp = [(nx + math.cos(a) * 7, ny + math.sin(a) * 6) for a in [i * math.pi / 3 for i in range(6)]]
        pd.polygon(mid, (10, 6, 28), hexp)
        pd.lines(mid, _scale(accent, 0.55), True, hexp, 1)
        pd.circle(mid, _scale(accent, 0.5), (nx, ny), 2)
    _planet(far, MARGIN + 470, 96, 17)  # whimsy: a ringed planet, a satellite and a sleepy comet
    _comet(far, MARGIN + 150, 46, 1.0)
    _satellite(far, MARGIN + 300, 150, 1.2)
    _mute(far, 0.6)
    _mute(mid, 0.55)
    near = _wide()
    pd.ellipse(near, (24, 8, 50), (-120, 308, WIDE + 240, 160))  # the curve of a huge planet far below
    pd.lines(near, _scale(accent, 0.5), False, [(-60 + i * 12, 312 - math.sin(i / (WIDE / 12) * math.pi) * 30) for i in range(int(WIDE / 12) + 6)], 1)
    _mute(near, 0.7)
    pulse_nodes = [(120, 80), (320, 60), (500, 110), (260, 150)]

    def pulse_fn(canvas, frame, cam):  # a few nodes breathe, slowly
        ox = -cam * 0.05
        for i, (x, y) in enumerate(pulse_nodes):
            k = 0.5 + 0.5 * math.sin(frame * 0.015 + i * 1.7)
            pd.circle(canvas, _scale(accent, 0.14 + 0.2 * k), (x + ox, y), 9 + 3 * k, 1)
            pd.circle(canvas, _scale(accent, 0.25 + 0.2 * k), (x + ox, y), 3)

    def ring_fn(canvas, frame, cam):  # a vast, faint orbital ring that creeps around
        ox = -cam * 0.04
        a = frame * 0.0015
        for rr, c in ((150, 0.16), (156, 0.1)):
            pts = [(W / 2 + ox + math.cos(t + a) * rr, 128 + math.sin(t + a) * rr * 0.28) for t in [i * math.pi / 24 for i in range(49)]]
            pd.lines(canvas, _scale(blue, c), True, pts, 1)

    def haze_fn(canvas, frame, cam):
        haze_band(canvas, 262, _scale(accent, 0.35), 100, 70)

    items = [Layer(far, 0.02, 0), Animated(ring_fn), Layer(mid, 0.06, 0), Animated(pulse_fn), Animated(haze_fn), Layer(near, 0.1, 0)]
    return Backdrop(sky, items, "mesh")


# --- Cloud Native: a dusk sky of shaded cumulus, floating islands, balloons, a zeppelin and a whale ------------------
CLOUD_COLS = ((34, 30, 80), (56, 48, 106), (84, 70, 128), (150, 98, 128))  # shadow, body, lit side, rim light (all dusk-dim)


def _cumulus(surf, cx, by, w, h, rng, cols=CLOUD_COLS, scale=1.0):
    """A cumulus built the way an illustrator would: a heap of overlapping puffs, a dark underbelly, a mid body, a lit
    upper-left, and a thin warm rim light along the tops. `by` is the flat bottom of the cloud."""
    shadow, body, light, rim = (tuple(int(c * scale) for c in col) for col in cols)
    n = max(5, int(w / (h * 0.5)))
    puffs = []
    for i in range(n):
        u = (i + 0.5) / n
        r = h * (0.30 + 0.5 * math.sin(u * math.pi) ** 0.8) * rng.uniform(0.85, 1.15)
        puffs.append((cx - w / 2 + u * w + rng.uniform(-2, 2), by - r * 0.55, r))
    for _ in range(max(1, n // 3)):  # little towers on top
        x, y, r = puffs[rng.randrange(n)]
        puffs.append((x + rng.uniform(-r * 0.4, r * 0.4), y - r * 0.6, r * rng.uniform(0.55, 0.8)))
    for x, y, r in puffs:
        pd.circle(surf, shadow, (x, y), r)
    for x, y, r in puffs:
        pd.circle(surf, body, (x - r * 0.10, y - r * 0.14), r * 0.88)
    for x, y, r in puffs:
        pd.circle(surf, light, (x - r * 0.22, y - r * 0.30), r * 0.60)
    for x, y, r in puffs:  # rim light on the upper-left edge of each puff
        pd.lines(surf, rim, False, [(x - r * 0.1 + math.cos(a) * r * 0.9, y - r * 0.14 + math.sin(a) * r * 0.9)
                                    for a in (math.radians(d) for d in range(200, 285, 14))], 1)


def _cirrus(surf, x, y, w, rng, col):
    """A long, wispy streak of high cloud."""
    for k in range(3):
        pts = [(x + i * w / 12, y + k * 2.6 + math.sin(i * 0.9 + k) * 1.2 - i * 0.18) for i in range(13)]
        pd.lines(surf, tuple(int(c * (1 - 0.18 * k)) for c in col), False, pts, 1)


def _balloon(canvas, x, y, size, t, ph):
    """A striped hot-air balloon carrying a shipping container, bobbing gently."""
    y += math.sin(t * 0.012 + ph) * 3
    r = 15 * size
    stripes = [(104, 40, 74), (150, 96, 60), (96, 70, 130), (60, 100, 126)]
    for i in range(8):  # gores: pie wedges of the envelope
        a0, a1 = math.pi + i * math.pi / 8 * 1.0 - math.pi * 0.0, math.pi + (i + 1) * math.pi / 8
        pts = [(x, y + r * 0.9)] + [(x + math.cos(a0 + (a1 - a0) * j / 3) * r * (1 - 0.0), y + math.sin(a0 + (a1 - a0) * j / 3) * r * 1.05) for j in range(4)]
        pd.polygon(canvas, stripes[i % 4], pts)
    pd.polygon(canvas, (70, 60, 110), [(x - r, y), (x + r, y), (x + r * 0.45, y + r * 0.8), (x - r * 0.45, y + r * 0.8)])
    pd.circle(canvas, (130, 100, 140), (x - r * 0.35, y - r * 0.4), r * 0.18)
    for dx in (-r * 0.45, r * 0.45):
        pd.line(canvas, (40, 34, 70), (x + dx, y + r * 0.8), (x + dx * 0.4, y + r * 1.5), 1)
    pd.rect(canvas, (150, 80, 70), (x - 5 * size, y + r * 1.5, 10 * size, 6 * size))  # a tiny shipping container
    pd.rect(canvas, (84, 44, 40), (x - 5 * size, y + r * 1.5, 10 * size, 1.4 * size))
    for k in range(4):
        pd.line(canvas, (96, 52, 46), (x - 3.6 * size + k * 2.4 * size, y + r * 1.5 + 1.4 * size), (x - 3.6 * size + k * 2.4 * size, y + r * 1.5 + 6 * size), 0.5)


def _zeppelin(canvas, x, y, size, t):
    """A proper airship: a ribbed, tapering envelope with a lit back, cross tail fins, a gondola with lit windows,
    struts and a slowly spinning propeller."""
    L, Hh = 76 * size, 24 * size
    env = []
    for i in range(21):  # a teardrop: blunt nose on the right, tapering tail on the left
        u = i / 20
        half = Hh / 2 * math.sin(math.pi * u ** 0.85) ** 0.8
        env.append((x - L / 2 + u * L, y - half))
    for i in range(20, -1, -1):
        u = i / 20
        half = Hh / 2 * math.sin(math.pi * u ** 0.85) ** 0.8
        env.append((x - L / 2 + u * L, y + half))
    pd.polygon(canvas, (52, 46, 104), env)
    top = [(px, py + (y - py) * 0.0) for px, py in env[:21]]
    pd.polygon(canvas, (86, 74, 138), top + [(x + L / 2 - 4 * size, y - Hh * 0.1), (x - L / 2 + 8 * size, y - Hh * 0.05)])  # the lit back
    for k in range(1, 9):  # panel ribs
        u = k / 9
        half = Hh / 2 * math.sin(math.pi * u ** 0.85) ** 0.8
        pd.line(canvas, (40, 34, 84), (x - L / 2 + u * L, y - half), (x - L / 2 + u * L, y + half), 0.5)
    pd.lines(canvas, (118, 84, 130), False, [(px, py) for px, py in env[2:19]], 1)  # rim light along the top
    tx = x - L / 2
    pd.polygon(canvas, (40, 34, 86), [(tx + 6 * size, y), (tx - 3 * size, y - 12 * size), (tx + 12 * size, y - 2 * size)])
    pd.polygon(canvas, (40, 34, 86), [(tx + 6 * size, y), (tx - 3 * size, y + 12 * size), (tx + 12 * size, y + 2 * size)])
    pd.polygon(canvas, (60, 50, 108), [(tx + 4 * size, y), (tx - 6 * size, y - 3 * size), (tx - 6 * size, y + 3 * size)])
    gx = x + 2 * size
    pd.polygon(canvas, (34, 30, 72), [(gx - 9 * size, y + Hh * 0.46), (gx + 9 * size, y + Hh * 0.46), (gx + 7 * size, y + Hh * 0.46 + 8 * size), (gx - 7 * size, y + Hh * 0.46 + 8 * size)])
    for k in range(4):  # warm little windows
        pd.rect(canvas, (150, 112, 70), (gx - 6 * size + k * 3.4 * size, y + Hh * 0.46 + 2 * size, 2 * size, 2.6 * size))
    for dx in (-5, 5):
        pd.line(canvas, (36, 30, 74), (gx + dx * size, y + Hh * 0.4), (gx + dx * 0.8 * size, y + Hh * 0.46), 0.5)
    px_, py_ = gx - 11 * size, y + Hh * 0.46 + 4 * size
    a = t * 0.12
    for k in range(2):  # the propeller, turning
        ang = a + k * math.pi / 2
        pd.line(canvas, (120, 100, 150), (px_ - math.cos(ang) * 4 * size, py_ - math.sin(ang) * 4 * size),
                (px_ + math.cos(ang) * 4 * size, py_ + math.sin(ang) * 4 * size), 0.7)
    pd.circle(canvas, (60, 52, 100), (px_, py_), 1.1 * size)
    pd.lines(canvas, (110, 90, 130), False, [(x + L / 2 - 2 * size, y - Hh * 0.25), (x + L / 2 + 6 * size, y - Hh * 0.55), (x + L / 2 + 6 * size, y - Hh * 0.2)], 1)  # a pennant


def _whale(canvas, x, y, size, t):
    """A giant, friendly whale drifting through the sky: round body, pale belly, an eye, and flukes that sway."""
    sway = math.sin(t * 0.01) * 3 * size
    body = [(x - 34 * size, y + 2 * size), (x - 28 * size, y - 9 * size), (x - 12 * size, y - 15 * size), (x + 10 * size, y - 15 * size),
            (x + 30 * size, y - 9 * size), (x + 38 * size, y + 1 * size), (x + 30 * size, y + 11 * size), (x + 10 * size, y + 15 * size),
            (x - 14 * size, y + 12 * size), (x - 30 * size, y + 6 * size)]
    pd.polygon(canvas, (36, 52, 104), body)
    pd.polygon(canvas, (86, 104, 150), [(x - 14 * size, y + 10 * size), (x + 12 * size, y + 12 * size), (x + 32 * size, y + 8 * size), (x + 36 * size, y + 2 * size),
                                       (x + 16 * size, y + 6 * size), (x - 12 * size, y + 6 * size)])
    pd.lines(canvas, (120, 140, 190), False, [(x - 20 * size + i * 3.4 * size, y - 13 * size - math.sin(i / 14 * math.pi) * 1.0) for i in range(15)], 1)
    tail = [(x - 30 * size, y + 4 * size), (x - 42 * size, y + sway), (x - 52 * size, y - 10 * size + sway), (x - 47 * size, y - 1 * size + sway),
            (x - 54 * size, y + 6 * size + sway), (x - 44 * size, y + 6 * size + sway * 0.6)]
    pd.polygon(canvas, (36, 52, 104), tail)
    pd.polygon(canvas, (60, 78, 128), [(x - 4 * size, y + 6 * size), (x + 8 * size, y + 14 * size), (x + 12 * size, y + 8 * size)])  # flipper
    pd.circle(canvas, (170, 190, 230), (x + 24 * size, y - 3 * size), 2.0 * size)
    pd.circle(canvas, (20, 24, 56), (x + 24.6 * size, y - 3 * size), 1.1 * size)
    pd.lines(canvas, (24, 30, 70), False, [(x + 36 * size, y + 4 * size), (x + 30 * size, y + 6.4 * size), (x + 24 * size, y + 6 * size)], 1)  # a smile
    for k in range(3):  # a gentle spout of tiny clouds
        pd.circle(canvas, (96, 90, 150), (x + 4 * size + k * 3.4 * size, y - 20 * size - k * 4 * size), (1.6 + k * 0.7) * size)


def build_cloud(canvas_w: int = PIX_W) -> Backdrop:
    rng = random.Random(41)
    accent, blue = ACCENT["cloud"], SECOND["cloud"]
    sky = dither_gradient(canvas_w, PIX_H, [(0, (3, 6, 26)), (0.30, (10, 16, 58)), (0.55, (26, 24, 80)), (0.74, (72, 44, 88)),
                                 (0.86, (96, 60, 84)), (1.0, (24, 16, 46))], bands=34)
    far = _wide()
    for _ in range(150):  # a field of stars, a few of them four-pointed sparkles
        x, y = rng.randrange(WIDE), rng.randrange(int(H * 0.5))
        pd.set_at(far, (x, y), _scale((210, 200, 255), rng.choice([0.25, 0.4, 0.55])))
        if rng.random() < 0.06:
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                pd.set_at(far, (x + dx, y + dy), _scale((210, 200, 255), 0.3))
    mx, my, mr = 470, 64, 24  # a crescent moon in a soft halo
    halo = ((36, 34, 88), (50, 46, 112), (66, 60, 138))  # soft rings of moonlight, brighter toward the moon
    for k, col in zip((3.2, 2.3, 1.55), halo):
        pd.circle(far, col, (mx, my), mr * k)
    pd.circle(far, (200, 196, 232), (mx, my), mr)
    pd.circle(far, halo[2], (mx + mr * 0.42, my - mr * 0.1), mr * 0.9)  # the bite out of the moon shows the halo behind it
    for band, col in enumerate(((120, 54, 70), (140, 92, 60), (150, 130, 70), (60, 120, 90), (60, 90, 140), (92, 70, 140))):  # a very dim rainbow
        rr = 150 - band * 3.2
        pd.lines(far, _scale(col, 0.34), False, [(WIDE // 2 - 40 + math.cos(math.pi + i * math.pi / 40) * rr * 1.3, 252 + math.sin(math.pi + i * math.pi / 40) * rr * 0.7)
                                               for i in range(41)], 1)
    for _ in range(7):
        _cirrus(far, rng.randrange(0, WIDE - 80), rng.randrange(20, 170), rng.randint(60, 120), rng, (74, 68, 128))
    for x in range(-40, WIDE + 40, 62):  # a distant range of cloud mountains on the horizon
        _cumulus(far, x + rng.randint(-8, 8), 262, rng.randint(70, 110), rng.randint(22, 34), rng, scale=0.72)
    mid = _wide()
    for _ in range(8):
        _cumulus(mid, rng.randrange(40, WIDE - 40), rng.randrange(80, 250), rng.randint(110, 190), rng.randint(32, 50), rng)
    for ix, iy in ((120, 176), (330, 128), (560, 188), (730, 140)):  # floating islands, each a little world
        pd.polygon(mid, (30, 26, 62), [(ix - 30, iy), (ix + 30, iy), (ix + 22, iy + 16), (ix + 12, iy + 30), (ix + 1, iy + 40), (ix - 9, iy + 26), (ix - 20, iy + 14)])
        for k in range(1, 5):  # rock strata
            pd.line(mid, (44, 38, 80), (ix - 26 + k * 3, iy + k * 5), (ix + 26 - k * 3, iy + k * 5), 1)
        pd.polygon(mid, (40, 76, 80), [(ix - 31, iy), (ix + 31, iy), (ix + 26, iy - 4), (ix - 26, iy - 4)])  # grassy top
        pd.lines(mid, (70, 120, 110), False, [(ix - 30 + i * 4, iy - 3.6 - (i % 2) * 1.2) for i in range(16)], 1)
        for tx in (ix + 14, ix + 20):  # little round trees
            pd.rect(mid, (50, 36, 40), (tx - 0.7, iy - 12, 1.4, 8))
            pd.circle(mid, (36, 84, 84), (tx, iy - 13), 4.2)
            pd.circle(mid, (56, 112, 104), (tx - 1, iy - 14.4), 2.4)
        if (ix // 10) % 2 == 0:  # a cosy hut with a lit window and a chimney
            pd.rect(mid, (66, 50, 78), (ix - 20, iy - 14, 14, 10))
            pd.polygon(mid, (92, 54, 70), [(ix - 22, iy - 14), (ix - 13, iy - 22), (ix - 4, iy - 14)])
            pd.rect(mid, (176, 130, 74), (ix - 16, iy - 11, 4, 4))
            pd.rect(mid, (50, 38, 60), (ix - 9, iy - 22, 2.4, 6))
        else:  # a server shed with a dish
            pd.rect(mid, (40, 44, 88), (ix - 22, iy - 15, 16, 11))
            for ly in range(3):
                pd.rect(mid, _scale(accent, 0.4), (ix - 20, iy - 13 + ly * 3, 5, 1))
            pd.line(mid, (70, 70, 120), (ix - 12, iy - 15), (ix - 12, iy - 22), 1)
            pd.polygon(mid, (88, 88, 140), [(ix - 17, iy - 21), (ix - 7, iy - 21), (ix - 12, iy - 18)])
    near = _wide()
    for x in range(-60, WIDE + 60, 50):  # the sea of cloud far below the stage, towering in places
        _cumulus(near, x + rng.randint(-8, 8), 322 + rng.randint(-4, 6), rng.randint(90, 130), rng.randint(40, 62), rng, scale=0.86)
    pd.rect(near, (24, 18, 50), (0, 328, WIDE, 40))
    _mute(far, 0.64)
    _mute(mid, 0.7)
    _mute(near, 0.76)
    balloons = [(96, 120, 1.0, 0.0), (420, 78, 0.8, 2.0), (610, 150, 1.1, 4.1)]
    wind = (190, 240)

    def sky_fn(canvas, frame, cam):
        ox = -cam * 0.05
        for bx, by, bs, ph in balloons:
            _balloon(canvas, bx + ox + math.sin(frame * 0.002 + ph) * 6, by, bs, frame, ph)
        for k, (zx0, zy, zs, spd) in enumerate(((20.0, 54, 1.0, 0.09), (400.0, 138, 0.7, 0.06))):
            zx = ((zx0 + frame * spd) % (W + 260)) - 130 + ox
            _zeppelin(canvas, zx, zy, zs, frame)
        _whale(canvas, ((frame * 0.035 + 180) % (W + 300)) - 150 + ox, 214, 0.9, frame)

    def windmill_fn(canvas, frame, cam):  # the windmill on the second island, turning slowly
        wx, wy = 330 - cam * 0.06 + 18, 128 - 24
        pd.rect(canvas, (60, 46, 84), (wx - 2.6, wy, 5.2, 22))
        for k in range(4):
            a = frame * 0.008 + k * math.pi / 2
            pd.polygon(canvas, (150, 120, 130), [(wx, wy), (wx + math.cos(a) * 15 - math.sin(a) * 2.4, wy + math.sin(a) * 15 + math.cos(a) * 2.4),
                                                  (wx + math.cos(a) * 15 + math.sin(a) * 2.4, wy + math.sin(a) * 15 - math.cos(a) * 2.4)])
        pd.circle(canvas, (96, 70, 100), (wx, wy), 2)

    def haze_fn(canvas, frame, cam):
        haze_band(canvas, 252, _scale((255, 160, 170), 0.5), 110, 70)

    items = [Layer(far, 0.02, 0), Layer(mid, 0.06, 0), Animated(sky_fn), Animated(windmill_fn), Animated(haze_fn), Layer(near, 0.11, 0)]
    return Backdrop(sky, items, "cloud")


BUILDERS = {"datacenter": build_datacenter, "controlplane": build_controlplane, "nodepool": build_nodepool,
            "etcd": build_etcd, "mesh": build_mesh, "cloud": build_cloud}
_backdrops: dict[tuple[str, int], Backdrop] = {}


def get_backdrop(theme: str, canvas_w: int = PIX_W) -> Backdrop:
    key = (theme, canvas_w)
    if key not in _backdrops:
        _backdrops[key] = BUILDERS.get(theme, build_datacenter)(canvas_w)
    return _backdrops[key]


def draw_backdrop(canvas: pygame.Surface, theme: str, frame: int, cam: float = 0.0) -> None:
    get_backdrop(theme, canvas.get_width()).draw(canvas, frame, cam)


RIPPLE_LIFE = 56


def hit_ripple(x: float) -> None:
    """A heavy hit sends a slow ring across the floor grid under the victim (scenery reacting, never flashing)."""
    ripples = REACT["ripples"]
    ripples.append([x, 0])
    del ripples[:-5]


def draw_ripples(canvas: pygame.Surface, theme: str, floor_y: int) -> None:
    c = ACCENT.get(theme, ACCENT["datacenter"])
    for rip in REACT["ripples"]:
        age = rip[1]
        u = age / RIPPLE_LIFE
        r = 14 + 120 * (1 - (1 - u) ** 2)
        color = _scale(c, 0.55 * (1 - u))
        wd.ellipse(canvas, color, (rip[0] - r, floor_y + 4 - r * 0.1, 2 * r, r * 0.2 + 2), 2)
        if u < 0.7:
            r2 = r * 0.6
            wd.ellipse(canvas, _scale(c, 0.3 * (1 - u)), (rip[0] - r2, floor_y + 4 - r2 * 0.1, 2 * r2, r2 * 0.2 + 2), 1)


def tick_ripples() -> None:
    for rip in REACT["ripples"]:
        rip[1] += 1
    REACT["ripples"][:] = [r for r in REACT["ripples"] if r[1] < RIPPLE_LIFE]


def neon_px(surf: pygame.Surface, a, b, color: Color, w: int = 1) -> None:
    """neon() for surfaces that are already in render pixels (platform art)."""
    pygame.draw.line(surf, _scale(color, 0.2), a, b, w + 4 * RS)
    pygame.draw.line(surf, _scale(color, 0.5), a, b, w + 2 * RS)
    pygame.draw.line(surf, color, a, b, w)


# --- platforms: dark glass slabs with neon edges, and holographic planks -------------------------
_platform_cache: dict[tuple, pygame.Surface] = {}


def _cloud_platform(wu: int, hu: int, thin: bool) -> pygame.Surface:
    """A cloud you can stand on: a bright, flat top edge, a shaded body with rounded ends and a billowing, varied underside."""
    S = RS
    w, h = wu * S, hu * S
    drop = (14 if thin else 34) * S
    s = pygame.Surface((w, h + drop + 6 * S), pygame.SRCALPHA)
    rng = random.Random(wu * 17 + hu)
    n = max(3, wu // (13 if thin else 24))
    puffs = []
    for i in range(n):  # the billowing underside: puffs of varied size hanging below the walkway
        u = (i + 0.5) / n
        r = (5 if thin else 12) * S * (0.6 + 0.6 * math.sin(u * math.pi) ** 0.7) * rng.uniform(0.85, 1.15)
        puffs.append((int(w * u + rng.uniform(-2, 2) * S), h + int(r * 0.25), int(r)))
    for x, y, r in puffs:
        pygame.draw.circle(s, (170, 162, 222), (x, y), r)
    for x, y, r in puffs:
        pygame.draw.circle(s, (198, 192, 238), (x - int(r * 0.08), y - int(r * 0.12)), int(r * 0.86))
    for x, y, r in puffs:
        pygame.draw.circle(s, (228, 222, 252), (x - int(r * 0.25), y - int(r * 0.3)), int(r * 0.5))
    body = pygame.Surface((w, h), pygame.SRCALPHA)
    for yy in range(h):  # the walkway slab: bright on top, a lilac underside
        t = yy / max(1, h - 1)
        c = tuple(int(a_ + (b_ - a_) * t) for a_, b_ in zip((248, 244, 255), (206, 200, 242)))
        pygame.draw.line(body, c, (0, yy), (w, yy))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=int(h * 0.45))
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(body, (0, 0))
    pygame.draw.line(s, (255, 255, 255), (int(h * 0.45), 0), (w - int(h * 0.45), 0), S)  # the bright top you stand on
    pygame.draw.line(s, (255, 196, 222), (int(h * 0.5), S), (w - int(h * 0.5), S), S)
    for x in range(10 * S, w - 10 * S, 26 * S):  # little glints and a soft fold line
        pygame.draw.line(s, (255, 255, 255), (x, 2 * S), (x + 5 * S, 2 * S), S)
    return s


def _platform_surface(wu: int, hu: int, theme: str, thin: bool) -> pygame.Surface:
    """Platform art for a platform wu x hu world units, drawn at render resolution."""
    S = RS
    w, h = wu * S, hu * S
    if theme == "cloud":
        return _cloud_platform(wu, hu, thin)
    c = ACCENT.get(theme, ACCENT["datacenter"])
    c2 = SECOND.get(theme, SECOND["datacenter"])
    s = pygame.Surface((w, h + 6 * S), pygame.SRCALPHA)
    rng = random.Random(wu * 31 + hu)
    if thin:  # a hologram plank: solid enough to never get lost against the scenery
        for y in range(h):
            pygame.draw.line(s, _scale(c, 0.4) + (170 if (y // S) % 2 == 0 else 120,), (0, y), (w, y))
        pygame.draw.rect(s, c, (0, 0, w, 3 * S))
        pygame.draw.line(s, (255, 255, 255), (2 * S, 0), (w - 3 * S, 0), S)  # a hot white core along the top edge
        pygame.draw.line(s, _scale(c, 0.6), (0, h - S), (w, h - S), 2 * S)
        for x in (0, w - 4 * S):
            pygame.draw.rect(s, c, (x, 0, 4 * S, h))
        for x in range(10 * S, w - 10 * S, 20 * S):  # tick marks so it reads as a surface, not a line
            pygame.draw.line(s, _scale(c, 0.9), (x, 3 * S), (x + 7 * S, 3 * S), S)
        return s
    for y in range(h):  # the slab: near-black glass gradient
        pygame.draw.line(s, _lerp((16, 24, 54), (3, 5, 16), y / max(1, h - 1)) + (255,), (0, y), (w, y))
    # etched circuit traces
    for _ in range(max(3, wu // 40)):
        x, y = rng.randrange(8, wu - 8), rng.randrange(10, max(11, hu - 6))
        pts = [(x * S, y * S)]
        for _ in range(4):
            if rng.random() < 0.5:
                x += rng.choice([-1, 1]) * rng.randint(8, 24)
            else:
                y += rng.choice([-1, 1]) * rng.randint(4, 10)
            x, y = max(4, min(wu - 4, x)), max(8, min(hu - 3, y))
            pts.append((x * S, y * S))
        pygame.draw.lines(s, _scale(c, 0.3), False, pts, S)
        pygame.draw.circle(s, _scale(c2, 0.9), pts[-1], S)
    for x in range(0, w, 40 * S):  # panel seams
        pygame.draw.line(s, (2, 4, 12), (x, 6 * S), (x, h), S)
        pygame.draw.line(s, _scale(c, 0.22), (x + S, 6 * S), (x + S, h), S)
    pygame.draw.rect(s, c, (0, 0, w, 3 * S))  # lit top edge with a hot white core and soft glow below
    pygame.draw.line(s, (255, 255, 255), (2 * S, 0), (w - 3 * S, 0), S)
    pygame.draw.line(s, _scale(c, 0.45), (0, 3 * S), (w, 3 * S), S)
    pygame.draw.line(s, _scale(c, 0.2), (0, 4 * S), (w, 4 * S), S)
    neon_px(s, (0, h - S), (w, h - S), _scale(c, 0.55), S)
    for x in (0, w - 4 * S):  # end caps
        pygame.draw.rect(s, c2, (x, 0, 4 * S, h))
    pygame.draw.polygon(s, _scale(c, 0.25), [(14 * S, h), (w - 14 * S, h), (w - 30 * S, h + 5 * S), (30 * S, h + 5 * S)])
    return s


def draw_platform(canvas: pygame.Surface, plat: Platform, theme: str) -> None:
    r = plat.rect
    if plat.glow <= 0.01:
        return  # a set-piece platform that is currently away
    key = (r.w, r.h, theme, plat.dropthrough)
    surf = _platform_cache.get(key)
    if surf is None:
        surf = _platform_cache[key] = _platform_surface(r.w, r.h, theme, plat.dropthrough)
    if plat.glow < 0.99:
        ghost = surf.copy()
        ghost.set_alpha(int(255 * max(0.0, min(1.0, plat.glow))))
        canvas.blit(ghost, (r.x * RS, r.y * RS))
        if not plat.solid:  # the warning outline: where it is about to appear
            wd.rect(canvas, ACCENT.get(theme, ACCENT["datacenter"]), r.inflate(2, 2), 1)
        return
    canvas.blit(surf, (r.x * RS, r.y * RS))

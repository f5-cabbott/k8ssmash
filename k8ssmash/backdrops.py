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
ACCENT = {"datacenter": (0, 226, 255), "controlplane": (176, 238, 255), "nodepool": (255, 150, 34)}
SECOND = {"datacenter": (255, 140, 40), "controlplane": (255, 214, 110), "nodepool": (0, 214, 255)}


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
    pd.rect(near, (2, 4, 12), (0, 0, WIDE, 18))  # ceiling with converging light strips
    for k in range(-8, 9):
        neon(near, (WIDE // 2 + k * 60, 0), (WIDE // 2 + k * 18, 18), _scale(accent, 0.8), 1)
    neon(near, (0, 18), (WIDE, 18), _scale(accent, 0.6), 1)

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
    for sx, w in ((MARGIN + 250, 36), (W + MARGIN - 286, 36)):  # server spines behind the core
        _tower(mid, sx, 120, w, horizon + 6, accent, rng, None, leds=False)

    near = _wide()
    for gx, side in ((MARGIN - 6, 0), (WIDE - MARGIN - 52, 1)):  # arched ribs with gold trim
        pd.rect(near, (4, 8, 24), (gx, 0, 58, H))
        pd.rect(near, (14, 26, 70), (gx + (46 if side == 0 else 0), 0, 12, H))
        neon(near, (gx + (58 if side == 0 else 0), 0), (gx + (58 if side == 0 else 0), H), gold, 1)
        for yy in range(24, H, 36):
            pd.polygon(near, _scale(accent, 0.55), [(gx, yy), (gx + 58, yy + 6), (gx + 58, yy + 10), (gx, yy + 4)])
    pd.rect(near, (3, 6, 20), (0, 0, WIDE, 12))
    neon(near, (0, 12), (WIDE, 12), gold, 1)

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
    pd.rect(near, (4, 2, 3), (0, 0, WIDE, 14))
    for k in range(0, WIDE, 44):  # hanging cable swags
        pd.lines(near, (20, 8, 8), False, [(k + i * 4, 14 + math.sin(i / 11 * math.pi) * 9) for i in range(12)], 2)

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


BUILDERS = {"datacenter": build_datacenter, "controlplane": build_controlplane, "nodepool": build_nodepool}
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


def _platform_surface(wu: int, hu: int, theme: str, thin: bool) -> pygame.Surface:
    """Platform art for a platform wu x hu world units, drawn at render resolution."""
    S = RS
    w, h = wu * S, hu * S
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

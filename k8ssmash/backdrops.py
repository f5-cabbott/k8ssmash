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
from k8ssmash.config import CANVAS_H, CANVAS_W, WORLD_H, WORLD_W
from k8ssmash.stage import Platform

W, H = CANVAS_W, CANVAS_H  # design grid
U = WORLD_W / CANVAS_W  # design -> world scale (1.5)
MARGIN = 64  # layers are wider than the screen so they can slide with the camera (design px)
CAM_LIMIT = 150
WIDE = W + 2 * MARGIN  # width of a parallax layer in design px

Color = tuple[int, int, int]


class ScaledDraw:
    """pygame.draw-alike that takes design-grid coordinates and draws them at world scale."""

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


pd = ScaledDraw(U)


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










class Layer:
    """A parallax layer authored in design px (wider than the screen by MARGIN each side)."""

    def __init__(self, surf: pygame.Surface, factor: float, y: int, drift: float = 0.0, wrap: bool = False, x: int = 0):
        self.surf, self.factor, self.y, self.drift, self.wrap, self.x = surf, factor, y, drift, wrap, x

    def draw(self, canvas: pygame.Surface, frame: int, cam: float) -> None:
        ox = (self.x - MARGIN - cam * self.factor + frame * self.drift) * U
        oy = self.y * U
        if self.wrap:
            w = self.surf.get_width()
            ox = ox % w - w
            for k in range(0, int(WORLD_W // w) + 3):
                canvas.blit(self.surf, (ox + k * w, oy))
        else:
            canvas.blit(self.surf, (ox, oy))


class Animated:
    def __init__(self, fn: Callable[[pygame.Surface, int, float], None]):
        self.fn = fn

    def draw(self, canvas: pygame.Surface, frame: int, cam: float) -> None:
        self.fn(canvas, frame, cam)


class Backdrop:
    def __init__(self, sky: pygame.Surface, items: list):
        self.sky, self.items = sky, items

    def draw(self, canvas: pygame.Surface, frame: int, cam: float = 0.0) -> None:
        canvas.blit(self.sky, (0, 0))
        cam = max(-CAM_LIMIT, min(CAM_LIMIT, cam / U))  # the camera arrives in world px; scenery thinks in design px
        for item in self.items:
            item.draw(canvas, frame, cam)


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
    for i in range(n):  # cross lines, nearer ones farther apart
        u = ((i + (frame * speed) % 1.0) / n) ** 2.1
        y = horizon + depth * u
        k = 0.25 + 0.75 * u
        pd.line(canvas, _scale(color, (0.22 + 0.5 * k) * fade), (0, int(y)), (W, int(y)), 1 if u < 0.6 else 2)
    pd.line(canvas, _scale(color, 1.0 * fade), (0, horizon), (W, horizon), 1)  # bright horizon seam


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
def build_datacenter() -> Backdrop:
    rng = random.Random(7)
    accent = ACCENT["datacenter"]
    horizon = 214
    sky = dither_gradient(WORLD_W, WORLD_H, [(0, (2, 4, 14)), (0.35, (4, 10, 36)), (0.56, (8, 36, 92)), (0.595, (34, 150, 210)),
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

    motes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.2, 0.55)) for _ in range(30)]

    def led_fn(canvas, frame, cam):
        ox = -MARGIN - cam * 0.09
        for x, y, ph, col in leds:
            if ((frame // 18) + ph) % 4 != 0:
                pd.fill(canvas, col, (int(x + ox), y, 2, 1))
        for i, pts in enumerate(cables):  # packets sliding along the cables
            px, py = pts[int((frame * 0.5 + i * 7) % 21)]
            pd.fill(canvas, (255, 255, 255), (int(px + ox), int(py) - 1, 2, 2))

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent)
        light_cycle(canvas, frame, cam, horizon, accent, 0.30, 3.4, 40)
        light_cycle(canvas, frame, cam, horizon, SECOND["datacenter"], 0.42, -4.4, 300, -1)
        light_cycle(canvas, frame, cam, horizon, accent, 0.55, 5.2, 120)

    def mote_fn(canvas, frame, cam):
        for x, y, sp in motes:
            yy = (y - frame * sp) % H
            xx = (x + math.sin(frame * 0.02 + y) * 5 - cam * 0.14) % W
            pd.fill(canvas, accent if int(y) % 3 else (255, 255, 255), (int(xx), int(yy), 1, 1 + int(y) % 2))

    items = [Layer(far, 0.03, 0), Animated(floor_fn), Layer(mid, 0.09, 0), Animated(led_fn), Animated(mote_fn),
             Layer(near, 0.22, 0)]
    return Backdrop(sky, items)


# --- Control Plane: the core chamber with a hologram of the helm wheel -----------------------------
def build_controlplane() -> Backdrop:
    rng = random.Random(11)
    accent, gold = ACCENT["controlplane"], SECOND["controlplane"]
    horizon = 236
    sky = dither_gradient(WORLD_W, WORLD_H, [(0, (3, 6, 24)), (0.4, (8, 18, 62)), (0.62, (22, 58, 140)), (0.655, (110, 190, 255)),
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

    def holo_fn(canvas, frame, cam):
        hx, hy, r = int(320 - cam * 0.03), 128, 78
        beam = pd.surface((r * 2, 130))  # projector cone down to the floor
        for yy in range(130):
            half = int(r * (0.35 + yy / 130 * 0.5))
            pd.line(beam, accent + (int(26 * (1 - yy / 130)),), (r - half, yy), (r + half, yy))
        pd.blit(canvas, beam, (hx - r, hy + 56))
        for k, rr in enumerate((r, r - 5)):
            pd.circle(canvas, _scale(accent, 0.35 + 0.35 * (k == 0)), (hx, hy), rr, 1 if k else 2)
        pd.circle(canvas, gold, (hx, hy), 13, 2)
        pd.circle(canvas, (255, 255, 255), (hx, hy), 4)
        for i in range(8):
            a = frame * 0.006 + i * math.pi / 4
            ex, ey = hx + math.cos(a) * (r + 10), hy + math.sin(a) * (r + 10)
            neon(canvas, (hx + math.cos(a) * 13, hy + math.sin(a) * 13), (hx + math.cos(a) * r, hy + math.sin(a) * r), accent, 1)
            pd.circle(canvas, gold, (int(ex), int(ey)), 4, 1)
            pd.circle(canvas, (255, 255, 255), (int(ex), int(ey)), 1)
        tilt = pygame.Rect(hx - 106, hy - 22, 212, 44)  # an orbiting data ring
        pd.ellipse(canvas, _scale(accent, 0.5), tilt, 1)
        ang = frame * 0.02
        pd.circle(canvas, (255, 255, 255), (int(hx + math.cos(ang) * 106), int(hy + math.sin(ang) * 22)), 2)
        scan = int((frame * 1.6) % (r * 2))
        pd.line(canvas, _scale(accent, 0.6), (hx - int(math.sqrt(max(0, r * r - (scan - r) ** 2))), hy - r + scan),
                         (hx + int(math.sqrt(max(0, r * r - (scan - r) ** 2))), hy - r + scan), 1)

    def stream_fn(canvas, frame, cam):
        ox = -MARGIN - cam * 0.08
        for i, tx in enumerate(tubes):
            for k in range(5):
                y = horizon - ((frame * (1.2 + 0.2 * i) + k * 52) % (horizon - 40))
                pd.fill(canvas, (255, 255, 255) if k % 2 else accent, (int(tx + ox) + 11, int(y), 4, 5))

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent, speed=0.009, fade=0.9)
        light_cycle(canvas, frame, cam, horizon, gold, 0.32, 3.0, 220)
        light_cycle(canvas, frame, cam, horizon, accent, 0.5, -3.8, 60, -1)

    def spark_fn(canvas, frame, cam):
        for i in range(8):
            if (frame // 9 + i * 5) % 11 == 0:
                x = int((i * 83 + 40 - cam * 0.1) % W)
                y = 40 + (i * 37) % 150
                pd.line(canvas, (255, 255, 255), (x - 3, y), (x + 3, y))
                pd.line(canvas, (255, 255, 255), (x, y - 3), (x, y + 3))

    items = [Layer(far, 0.02, 0), Animated(holo_fn), Animated(floor_fn), Layer(mid, 0.08, 0), Animated(stream_fn),
             Animated(spark_fn), Layer(near, 0.22, 0)]
    return Backdrop(sky, items)


# --- Node Pool: an amber hot-aisle pod bay with honeycomb pod cells --------------------------------
def build_nodepool() -> Backdrop:
    rng = random.Random(23)
    accent, cyan = ACCENT["nodepool"], SECOND["nodepool"]
    horizon = 222
    sky = dither_gradient(WORLD_W, WORLD_H, [(0, (6, 2, 4)), (0.35, (22, 6, 8)), (0.56, (74, 22, 10)), (0.605, (255, 140, 34)),
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

    def pod_fn(canvas, frame, cam):
        ox = -MARGIN - cam * 0.04
        for x, y, ph in pods:
            if ((frame // 24) + ph) % 5 == 0:
                pd.fill(canvas, (255, 255, 255), (int(x + ox) - 1, y - 2, 2, 3))
        for x, y, ph, col in leds:
            if ((frame // 16) + ph) % 4 != 0:
                pd.fill(canvas, col, (int(x - MARGIN - cam * 0.09), y, 2, 1))

    steam = [(rng.uniform(0, W), rng.uniform(0, 80), rng.uniform(0.3, 0.7)) for _ in range(14)]

    def steam_fn(canvas, frame, cam):
        for i, (x, y0, sp) in enumerate(steam):
            t = (frame * sp + y0 * 3) % 120
            yy, rr = horizon + 6 - t * 1.6, 3 + t * 0.07
            puff = pd.surface((24, 24))
            pd.circle(puff, (255, 200, 150, int(46 * (1 - t / 120))), (12, 12), int(rr))
            pd.blit(canvas, puff, (int(x - cam * 0.1 + math.sin(t * 0.07 + i) * 5) - 12, int(yy) - 12))

    def floor_fn(canvas, frame, cam):
        grid_floor(canvas, frame, cam, horizon, accent, speed=0.01)
        light_cycle(canvas, frame, cam, horizon, accent, 0.3, 3.6, 150)
        light_cycle(canvas, frame, cam, horizon, cyan, 0.48, -4.2, 400, -1)

    items = [Layer(far, 0.03, 0), Animated(floor_fn), Layer(mid, 0.09, 0), Animated(pod_fn), Animated(steam_fn),
             Layer(near, 0.22, 0)]
    return Backdrop(sky, items)


BUILDERS = {"datacenter": build_datacenter, "controlplane": build_controlplane, "nodepool": build_nodepool}
_backdrops: dict[str, Backdrop] = {}


def get_backdrop(theme: str) -> Backdrop:
    if theme not in _backdrops:
        _backdrops[theme] = BUILDERS.get(theme, build_datacenter)()
    return _backdrops[theme]


def draw_backdrop(canvas: pygame.Surface, theme: str, frame: int, cam: float = 0.0) -> None:
    get_backdrop(theme).draw(canvas, frame, cam)


def neon_px(surf: pygame.Surface, a, b, color: Color, w: int = 1) -> None:
    """neon() for surfaces that are already in world pixels (platform art)."""
    pygame.draw.line(surf, _scale(color, 0.2), a, b, w + 4)
    pygame.draw.line(surf, _scale(color, 0.5), a, b, w + 2)
    pygame.draw.line(surf, color, a, b, w)


# --- platforms: dark glass slabs with neon edges, and holographic planks -------------------------
_platform_cache: dict[tuple, pygame.Surface] = {}


def _platform_surface(w: int, h: int, theme: str, thin: bool) -> pygame.Surface:
    c = ACCENT.get(theme, ACCENT["datacenter"])
    c2 = SECOND.get(theme, SECOND["datacenter"])
    s = pygame.Surface((w, h + 6), pygame.SRCALPHA)
    rng = random.Random(w * 31 + h)
    if thin:  # a hologram plank: translucent, scanlined, bright-edged
        for y in range(h):
            pygame.draw.line(s, _scale(c, 0.35) + (96 if y % 2 == 0 else 60,), (0, y), (w, y))
        pygame.draw.line(s, c, (0, 0), (w, 0), 2)
        pygame.draw.line(s, _scale(c, 0.5), (0, h - 1), (w, h - 1), 1)
        for x in (0, w - 3):
            pygame.draw.rect(s, c, (x, 0, 3, h))
        for x in range(8, w - 8, 18):
            pygame.draw.line(s, _scale(c, 0.8), (x, 2), (x + 6, 2), 1)
        return s
    for y in range(h):  # the slab: near-black glass gradient
        pygame.draw.line(s, _lerp((16, 24, 54), (3, 5, 16), y / max(1, h - 1)) + (255,), (0, y), (w, y))
    # etched circuit traces
    for _ in range(max(3, w // 40)):
        x, y = rng.randrange(8, w - 8), rng.randrange(10, max(11, h - 6))
        pts = [(x, y)]
        for _ in range(4):
            if rng.random() < 0.5:
                x += rng.choice([-1, 1]) * rng.randint(8, 24)
            else:
                y += rng.choice([-1, 1]) * rng.randint(4, 10)
            x, y = max(4, min(w - 4, x)), max(8, min(h - 3, y))
            pts.append((x, y))
        pygame.draw.lines(s, _scale(c, 0.3), False, pts, 1)
        pygame.draw.circle(s, _scale(c2, 0.9), pts[-1], 1)
    for x in range(0, w, 40):  # panel seams
        pygame.draw.line(s, (2, 4, 12), (x, 6), (x, h))
        pygame.draw.line(s, _scale(c, 0.22), (x + 1, 6), (x + 1, h))
    pygame.draw.rect(s, c, (0, 0, w, 3))  # lit top edge with a hot white core and soft glow below
    pygame.draw.line(s, (255, 255, 255), (2, 0), (w - 3, 0), 1)
    pygame.draw.line(s, _scale(c, 0.45), (0, 3), (w, 3), 1)
    pygame.draw.line(s, _scale(c, 0.2), (0, 4), (w, 4), 1)
    neon_px(s, (0, h - 1), (w, h - 1), _scale(c, 0.55), 1)
    for x in (0, w - 4):  # end caps
        pygame.draw.rect(s, c2, (x, 0, 4, h))
    pygame.draw.polygon(s, _scale(c, 0.25), [(14, h), (w - 14, h), (w - 30, h + 5), (30, h + 5)])
    return s


def draw_platform(canvas: pygame.Surface, plat: Platform, theme: str) -> None:
    r = plat.rect
    key = (r.w, r.h, theme, plat.dropthrough)
    surf = _platform_cache.get(key)
    if surf is None:
        surf = _platform_cache[key] = _platform_surface(r.w, r.h, theme, plat.dropthrough)
    canvas.blit(surf, r.topleft)

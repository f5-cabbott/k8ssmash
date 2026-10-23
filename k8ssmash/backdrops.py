"""Procedural stage scenery: dithered gradient skies, several parallax layers per stage, animated details,
and textured platforms. Everything is generated once per stage and then just blitted."""
from __future__ import annotations

import math
import random
from typing import Callable

import numpy as np
import pygame

from k8ssmash.art.shade import BAYER, make_ramp, paint_part
from k8ssmash.config import CANVAS_H, CANVAS_W
from k8ssmash.stage import Platform

W, H = CANVAS_W, CANVAS_H
MARGIN = 64  # layers are wider than the screen so they can slide with the camera
CAM_LIMIT = 150

Color = tuple[int, int, int]


# --- helpers --------------------------------------------------------------------------------
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


def disc(mask: np.ndarray, cx: float, cy: float, r: float) -> None:
    ys, xs = np.ogrid[:mask.shape[0], :mask.shape[1]]
    mask |= (xs - cx) ** 2 + (ys - cy) ** 2 <= r * r


def shaded(mask: np.ndarray, base: Color, shiny: bool = False) -> pygame.Surface:
    """Light a binary shape like a sprite part (ramps, dithering, colored outline) and return it."""
    pad = np.pad(mask, 2)
    arr = np.zeros(pad.shape + (4,), dtype=np.uint8)
    paint_part(arr, pad, make_ramp(base), shiny)
    surf = pygame.Surface((pad.shape[1], pad.shape[0]), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(surf)[:] = arr[:, :, :3].transpose(1, 0, 2)
    pygame.surfarray.pixels_alpha(surf)[:] = arr[:, :, 3].T
    return surf


def cloud(rng: random.Random, w: int, base: Color = (246, 250, 255)) -> pygame.Surface:
    h = int(w * 0.5)
    mask = np.zeros((h, w), dtype=bool)
    x = w * 0.18
    while x < w * 0.86:
        r = rng.uniform(w * 0.11, w * 0.2)
        disc(mask, x, h * 0.62 - r * 0.45 * rng.uniform(0.6, 1.2), r)
        x += r * 0.9
    mask[int(h * 0.74):, :] = False
    disc(mask, w * 0.5, h * 0.7, w * 0.07)  # keeps the underside soft
    mask[int(h * 0.74):, :] = False
    surf = shaded(mask, base)
    _haze(surf, (176, 208, 255), 0.16)  # shadows read as sky-blue, not gray
    return surf


def hill(w: int, h: int, base: Color, eyes: bool = False) -> pygame.Surface:
    mask = np.zeros((h, w), dtype=bool)
    xs = np.arange(w)
    top = (h * np.sqrt(np.clip(1 - ((xs - w / 2) / (w / 2)) ** 2, 0, 1))).astype(int)
    for x in range(w):
        mask[h - top[x]:, x] = True
    surf = shaded(mask, base)
    if eyes:  # the soft vertical highlight ovals SMW hills wear
        light = tuple(min(255, int(c * 1.18 + 14)) for c in base)
        for ex in (0.38, 0.62):
            ew, eh = max(3, w // 22), max(7, h // 5)
            ey = int(h * (0.36 if ex < 0.5 else 0.42))
            pygame.draw.ellipse(surf, light, (int(w * ex), ey, ew, eh))
    return surf


class Layer:
    def __init__(self, surf: pygame.Surface, factor: float, y: int, drift: float = 0.0, wrap: bool = False,
                 x: int = 0):
        self.surf, self.factor, self.y, self.drift, self.wrap, self.x = surf, factor, y, drift, wrap, x

    def draw(self, canvas: pygame.Surface, frame: int, cam: float) -> None:
        ox = self.x - MARGIN - cam * self.factor + frame * self.drift
        if self.wrap:
            w = self.surf.get_width()
            ox = ox % w - w
            for k in range(0, W // w + 3):
                canvas.blit(self.surf, (ox + k * w, self.y))
        else:
            canvas.blit(self.surf, (ox, self.y))


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
        cam = max(-CAM_LIMIT, min(CAM_LIMIT, cam))
        for item in self.items:
            item.draw(canvas, frame, cam)


def _wide() -> pygame.Surface:
    return pygame.Surface((W + 2 * MARGIN, H), pygame.SRCALPHA)


def _haze(surf: pygame.Surface, color: Color, amount: float) -> None:
    """Atmospheric perspective: blend the opaque pixels of a far layer toward the horizon color."""
    arr = pygame.surfarray.pixels3d(surf)
    alpha = pygame.surfarray.pixels_alpha(surf)
    opaque = (alpha > 0)[..., None]
    tinted = (arr * (1 - amount) + np.array(color) * amount).astype(arr.dtype)
    arr[:] = np.where(opaque, tinted, arr)


# --- Datacenter: a dusk skyline of server towers ---------------------------------------------
def build_datacenter() -> Backdrop:
    rng = random.Random(7)
    sky = dither_gradient(W, H, [(0, (10, 10, 38)), (0.35, (30, 22, 80)), (0.62, (96, 44, 120)),
                                 (0.82, (206, 100, 120)), (1.0, (250, 172, 130))])
    horizon = (170, 80, 120)
    ground = 292

    far = _wide()
    x = 0
    while x < far.get_width():
        w, h = rng.randint(18, 36), rng.randint(70, 175)
        col = (52, 38, 104)
        pygame.draw.rect(far, col, (x, ground - h, w, h))
        pygame.draw.rect(far, (92, 68, 150), (x, ground - h, w, 2))
        for wy in range(ground - h + 6, ground - 6, 8):
            for wx in range(x + 4, x + w - 4, 7):
                if rng.random() < 0.34:
                    far.set_at((wx, wy), (170, 140, 220))
        if rng.random() < 0.3:
            pygame.draw.line(far, (92, 68, 150), (x + w // 2, ground - h), (x + w // 2, ground - h - 14))
        x += w + rng.randint(0, 6)
    _haze(far, horizon, 0.38)

    mid = _wide()
    leds: list[tuple[int, int, int, Color]] = []
    xs = list(range(10, mid.get_width() - 40, 78))
    tops = []
    for tx in xs:
        w, h = rng.randint(46, 62), rng.randint(130, 238)
        top = ground - h
        tops.append((tx, w, top))
        for yy in range(top, ground):
            t = (yy - top) / h
            pygame.draw.line(mid, _lerp((38, 44, 98), (16, 18, 52), t), (tx, yy), (tx + w, yy))
        pygame.draw.rect(mid, (110, 150, 230), (tx, top, w, 2))
        pygame.draw.rect(mid, (70, 90, 170), (tx, top, 2, h))
        pygame.draw.rect(mid, (10, 12, 36), (tx + w - 3, top, 3, h))
        for yy in range(top + 8, ground - 6, 9):
            pygame.draw.rect(mid, (26, 32, 78), (tx + 5, yy, w - 10, 6))
            pygame.draw.line(mid, (52, 64, 128), (tx + 5, yy), (tx + w - 6, yy))
            for k in range(3):
                col = rng.choice([(90, 255, 160), (90, 220, 255), (255, 190, 80)])
                leds.append((tx + 8 + k * 5, yy + 2, rng.randint(0, 6), col))
    # cables sagging between neighbouring towers
    for (tx, w, top), (nx, _, ntop) in zip(tops, tops[1:]):
        for k, drop in enumerate((12, 20)):
            y0, y1 = top + 18 + k * 30, ntop + 22 + k * 28
            pts = []
            for i in range(21):
                u = i / 20
                pts.append((tx + w + (nx - tx - w) * u, y0 + (y1 - y0) * u + math.sin(u * math.pi) * drop))
            pygame.draw.lines(mid, (10, 12, 34), False, pts, 3)
            pygame.draw.lines(mid, (58, 168, 190), False, [(px, py - 1) for px, py in pts], 1)
    _haze(mid, (60, 36, 100), 0.12)

    near = _wide()
    for side in (0, 1):
        gx = MARGIN if side == 0 else near.get_width() - MARGIN - 64
        pygame.draw.rect(near, (8, 8, 26), (gx, 0, 64, H))
        for yy in range(0, H, 22):
            pygame.draw.line(near, (22, 24, 58), (gx, yy), (gx + 64, yy + 22), 2)
            pygame.draw.line(near, (22, 24, 58), (gx + 64, yy), (gx, yy + 22), 2)
        pygame.draw.rect(near, (34, 40, 90), (gx + (60 if side == 0 else 0), 0, 4, H))
    pygame.draw.rect(near, (8, 8, 26), (0, 0, near.get_width(), 12))
    pygame.draw.line(near, (40, 48, 104), (0, 12), (near.get_width(), 12), 2)
    for k in range(0, near.get_width(), 36):
        pygame.draw.line(near, (22, 24, 58), (k, 12), (k + 18, 4), 2)

    fog = pygame.Surface((W + 2 * MARGIN, 120), pygame.SRCALPHA)
    for yy in range(120):
        a = int(110 * (yy / 120) ** 1.6)
        pygame.draw.line(fog, (210, 120, 170, a), (0, yy), (fog.get_width(), yy))

    motes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.15, 0.5), rng.choice([1, 2])) for _ in range(34)]

    def led_fn(canvas, frame, cam):
        ox = -MARGIN - cam * 0.1
        for x, y, ph, col in leds:
            if ((frame // 18) + ph) % 4 != 0:
                canvas.set_at((int(x + ox), y), col)
                canvas.set_at((int(x + ox) + 1, y), col)

    def mote_fn(canvas, frame, cam):
        for x, y, sp, size in motes:
            yy = (y - frame * sp) % H
            xx = (x + math.sin(frame * 0.02 + y) * 6 - cam * 0.14) % W
            canvas.fill((120, 230, 255), (int(xx), int(yy), size, size))

    items = [Layer(far, 0.04, 0), Layer(mid, 0.10, 0), Animated(led_fn), Layer(fog, 0.12, 190, drift=0.05, wrap=True),
             Animated(mote_fn), Layer(near, 0.22, 0)]
    return Backdrop(sky, items)


# --- Control Plane: a sky temple around a giant ship's wheel ----------------------------------
def build_controlplane() -> Backdrop:
    rng = random.Random(11)
    sky = dither_gradient(W, H, [(0, (22, 46, 124)), (0.4, (66, 128, 210)), (0.75, (168, 214, 246)),
                                 (1, (255, 236, 204))])

    def wheel_fn(canvas, frame, cam):
        cx, cy, r = 320 - cam * 0.02, 128, 78
        glow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
        for k in range(8, 0, -1):
            pygame.draw.circle(glow, (255, 244, 210, 4 + k * 2), (r * 3 // 2, r * 3 // 2), int(r * (0.95 + k * 0.06)))
        canvas.blit(glow, (cx - r * 3 // 2, cy - r * 3 // 2))
        col, hi = (255, 242, 196), (255, 255, 235)
        pygame.draw.circle(canvas, col, (cx, cy), r, 5)
        pygame.draw.circle(canvas, hi, (cx, cy), r - 3, 1)
        pygame.draw.circle(canvas, col, (cx, cy), 14)
        pygame.draw.circle(canvas, hi, (cx - 3, cy - 3), 5)
        for i in range(8):
            a = frame * 0.0035 + i * math.pi / 4
            ex, ey = cx + math.cos(a) * (r + 12), cy + math.sin(a) * (r + 12)
            pygame.draw.line(canvas, col, (cx, cy), (cx + math.cos(a) * r, cy + math.sin(a) * r), 4)
            pygame.draw.circle(canvas, hi, (int(ex), int(ey)), 5)
            pygame.draw.circle(canvas, col, (int(ex), int(ey)), 5, 1)

    def clouds(count: int, lo: int, hi: int, y0: int, y1: int, tone: Color) -> pygame.Surface:
        s = pygame.Surface((W + 2 * MARGIN + 200, H), pygame.SRCALPHA)
        for i in range(count):
            c = cloud(rng, rng.randint(lo, hi), tone)
            s.blit(c, (int(i * (s.get_width() / count)) + rng.randint(-10, 20), rng.randint(y0, y1)))
        return s

    far_clouds = clouds(5, 90, 150, 150, 210, (222, 238, 255))
    mid_clouds = clouds(4, 110, 190, 190, 250, (255, 255, 255))

    islands = pygame.Surface((W + 2 * MARGIN, H), pygame.SRCALPHA)
    for ix, iy, iw in ((60, 168, 150), (300, 120, 120), (500, 188, 160)):
        mask = np.zeros((70, iw), dtype=bool)
        xs = np.arange(iw)
        depth = (62 * np.sqrt(np.clip(1 - ((xs - iw / 2) / (iw / 2)) ** 2, 0, 1)) ** 1.5).astype(int)
        for x in range(iw):
            mask[8:8 + depth[x], x] = True
        mask[:10, :] = np.arange(iw)[None, :] % iw >= 0
        mask[:10, :4] = False
        mask[:10, -4:] = False
        rock = shaded(mask, (118, 130, 176))
        islands.blit(rock, (ix, iy))
        pygame.draw.rect(islands, (150, 220, 160), (ix + 6, iy + 6, iw - 8, 6), border_radius=3)
        for k in range(rng.randint(2, 3)):  # glass crystal spires
            sx = ix + 24 + k * (iw - 50) // 3
            h = rng.randint(24, 44)
            pygame.draw.polygon(islands, (150, 226, 240), [(sx, iy + 8), (sx + 7, iy + 8 - h), (sx + 14, iy + 8)])
            pygame.draw.polygon(islands, (230, 255, 255), [(sx + 7, iy + 8 - h), (sx + 14, iy + 8), (sx + 8, iy + 8)])
            pygame.draw.polygon(islands, (70, 160, 200), [(sx, iy + 8), (sx + 7, iy + 8 - h), (sx + 4, iy + 8)])

    near = _wide()
    for gx in (MARGIN + 4, near.get_width() - MARGIN - 56):
        pygame.draw.rect(near, (214, 226, 246), (gx + 8, 16, 36, H))
        pygame.draw.rect(near, (252, 254, 255), (gx + 8, 16, 7, H))
        pygame.draw.rect(near, (146, 168, 214), (gx + 36, 16, 8, H))
        for yy in range(30, H, 26):
            pygame.draw.line(near, (170, 190, 226), (gx + 15, yy), (gx + 36, yy), 1)
        pygame.draw.rect(near, (236, 244, 255), (gx, 4, 52, 16), border_radius=3)
        pygame.draw.rect(near, (255, 226, 150), (gx, 4, 52, 3))
        pygame.draw.rect(near, (130, 150, 200), (gx, 16, 52, 4))
    pygame.draw.rect(near, (226, 236, 252), (0, 0, near.get_width(), 8))
    pygame.draw.rect(near, (255, 226, 150), (0, 7, near.get_width(), 2))

    def rays_fn(canvas, frame, cam):
        rays = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(9):
            a = math.radians(-100 + i * 25 + math.sin(frame * 0.004 + i) * 4)
            spread = 0.07
            p0 = (320 - cam * 0.02, 128)
            p1 = (p0[0] + math.cos(a - spread) * 700, p0[1] - math.sin(a - spread) * -700)
            p2 = (p0[0] + math.cos(a + spread) * 700, p0[1] - math.sin(a + spread) * -700)
            pygame.draw.polygon(rays, (255, 248, 210, 16), [p0, p1, p2])
        canvas.blit(rays, (0, 0))

    def twinkle_fn(canvas, frame, cam):
        for i, (x, y) in enumerate(((120, 196), (380, 150), (560, 222), (260, 214), (470, 236))):
            if (frame // 14 + i) % 5 == 0:
                px, py = int(x - cam * 0.11), y
                pygame.draw.line(canvas, (255, 255, 255), (px - 3, py), (px + 3, py))
                pygame.draw.line(canvas, (255, 255, 255), (px, py - 3), (px, py + 3))

    items = [Animated(wheel_fn), Animated(rays_fn), Layer(far_clouds, 0.04, 0, drift=0.06, wrap=True),
             Layer(islands, 0.10, 20), Animated(twinkle_fn),
             Layer(mid_clouds, 0.07, 30, drift=0.12, wrap=True), Layer(near, 0.22, 0)]
    return Backdrop(sky, items)


# --- Node Pool: a sunny meadow in the sky (the Super Mario World mood) -------------------------
def build_nodepool() -> Backdrop:
    rng = random.Random(23)
    sky = dither_gradient(W, H, [(0, (52, 130, 246)), (0.45, (112, 186, 255)), (0.85, (202, 234, 255)),
                                 (1, (236, 248, 255))])

    def clouds(count, lo, hi, y0, y1, drift_pad) -> pygame.Surface:
        s = pygame.Surface((W + drift_pad, H), pygame.SRCALPHA)
        for i in range(count):
            c = cloud(rng, rng.randint(lo, hi))
            s.blit(c, (int(i * s.get_width() / count) + rng.randint(-14, 20), rng.randint(y0, y1)))
        return s

    far_clouds = clouds(6, 70, 120, 30, 150, 160)
    near_clouds = clouds(4, 120, 190, 60, 200, 200)

    far_hills = _wide()
    mid_hills = _wide()
    ground = H
    for hx, hw, hh in ((-20, 280, 150), (210, 340, 190), (480, 300, 140), (660, 280, 160)):
        far_hills.blit(hill(hw, hh, (136, 200, 214)), (hx + MARGIN, ground - hh - 40))
    for hx, hw, hh in ((10, 220, 130), (170, 260, 100), (390, 300, 150), (600, 200, 110)):
        mid_hills.blit(hill(hw, hh, (92, 196, 104), eyes=True), (hx + MARGIN, ground - hh - 18))
    _haze(far_hills, (200, 232, 255), 0.22)

    near = _wide()
    for side, gx in ((0, MARGIN), (1, near.get_width() - MARGIN - 150)):
        for i in range(5):
            cx = gx + 20 + i * 26 + rng.randint(-6, 6)
            m = np.zeros((60, 70), dtype=bool)
            disc(m, 35, 38, rng.randint(20, 27))
            disc(m, 18, 44, 15)
            disc(m, 54, 44, 15)
            m[50:, :] = False
            near.blit(shaded(m, (60, 170, 80)), (cx - 14, 258 - rng.randint(0, 16)))
        for k in range(9):
            fx, fy = gx + rng.randint(8, 142), 280 + rng.randint(0, 10)
            pygame.draw.line(near, (40, 130, 60), (fx, fy), (fx, fy + 7))
            pygame.draw.circle(near, rng.choice([(255, 140, 190), (255, 230, 90), (255, 255, 255)]), (fx, fy), 2)

    def sparkle_fn(canvas, frame, cam):
        for i in range(10):
            x = (i * 97 + 31) % W
            y = (i * 53 + 20) % 150 + 20
            if (frame // 10 + i * 3) % 12 == 0:
                px = int(x - cam * 0.05)
                pygame.draw.line(canvas, (255, 255, 255), (px - 2, y), (px + 2, y))
                pygame.draw.line(canvas, (255, 255, 255), (px, y - 2), (px, y + 2))

    items = [Layer(far_clouds, 0.03, 0, drift=0.05, wrap=True), Layer(far_hills, 0.05, 0),
             Layer(near_clouds, 0.07, 0, drift=0.12, wrap=True), Layer(mid_hills, 0.11, 0),
             Animated(sparkle_fn), Layer(near, 0.22, 0)]
    return Backdrop(sky, items)


BUILDERS = {"datacenter": build_datacenter, "controlplane": build_controlplane, "nodepool": build_nodepool}
_backdrops: dict[str, Backdrop] = {}


def get_backdrop(theme: str) -> Backdrop:
    if theme not in _backdrops:
        _backdrops[theme] = BUILDERS.get(theme, build_datacenter)()
    return _backdrops[theme]


def draw_backdrop(canvas: pygame.Surface, theme: str, frame: int, cam: float = 0.0) -> None:
    get_backdrop(theme).draw(canvas, frame, cam)


# --- platforms ---------------------------------------------------------------------------------
_platform_cache: dict[tuple, pygame.Surface] = {}


def _platform_surface(w: int, h: int, theme: str, thin: bool) -> pygame.Surface:
    s = pygame.Surface((w, h + 6), pygame.SRCALPHA)
    rng = random.Random(w * 31 + h)
    if theme == "nodepool":
        grass_h = 7 if not thin else 5
        for y in range(grass_h, h):
            t = (y - grass_h) / max(1, h - grass_h)
            pygame.draw.line(s, _lerp((196, 128, 70), (112, 66, 44), t), (0, y), (w, y))
        for _ in range(w * max(1, h - grass_h) // 40):
            s.set_at((rng.randrange(w), rng.randrange(grass_h + 2, max(grass_h + 3, h))), (150, 92, 54))
        pygame.draw.rect(s, (94, 54, 40), (0, grass_h, w, h - grass_h), 1)
        pygame.draw.rect(s, (56, 170, 70), (0, 0, w, grass_h))
        pygame.draw.rect(s, (130, 224, 100), (0, 0, w, 2))
        for x in range(0, w, 6):  # scalloped lower edge of the grass
            pygame.draw.circle(s, (40, 140, 62), (x + 3, grass_h), 3)
        pygame.draw.rect(s, (28, 90, 44), (0, 0, w, grass_h + 2), 1)
        if not thin:
            pygame.draw.polygon(s, (112, 66, 44), [(0, h - 1), (w, h - 1), (w - 14, h + 5), (14, h + 5)])
    elif theme == "controlplane":
        top, bottom = ((246, 250, 255), (150, 172, 222)) if not thin else ((200, 240, 255), (120, 190, 230))
        for y in range(h):
            pygame.draw.line(s, _lerp(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
        if not thin:
            for x in range(0, w, 40):
                pygame.draw.line(s, (170, 190, 230), (x, 6), (x, h))
            pygame.draw.line(s, (255, 226, 150), (0, 4), (w, 4))
            for x in range(20, w, 80):
                pygame.draw.rect(s, (255, 226, 150), (x - 3, 12, 6, 6), border_radius=2)
        pygame.draw.rect(s, (255, 255, 255), (0, 0, w, 2))
        pygame.draw.rect(s, (70, 90, 150), (0, 0, w, h), 1, border_radius=2)
        if thin:
            pygame.draw.rect(s, (255, 255, 255), (1, 1, w - 2, h - 2), 1)
    else:  # datacenter: riveted steel deck with hazard striping
        top, bottom = ((110, 134, 196), (46, 58, 112)) if not thin else ((140, 164, 220), (80, 100, 160))
        for y in range(h):
            pygame.draw.line(s, _lerp(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
        if not thin:
            for x in range(0, w, 40):
                pygame.draw.line(s, (36, 46, 96), (x, 8), (x, h))
                pygame.draw.line(s, (130, 150, 210), (x + 1, 8), (x + 1, h))
                for ry in (12, h - 8):
                    pygame.draw.circle(s, (170, 188, 235), (x + 5, ry), 1)
            for x in range(0, w, 16):
                pygame.draw.polygon(s, (255, 205, 70) if (x // 16) % 2 == 0 else (30, 30, 50),
                                    [(x, 6), (x + 8, 6), (x + 4, 11), (x - 4, 11)])
        pygame.draw.rect(s, (190, 210, 255), (0, 0, w, 3))
        pygame.draw.rect(s, (20, 26, 60), (0, 0, w, h), 1, border_radius=2)
    return s


def draw_platform(canvas: pygame.Surface, plat: Platform, theme: str) -> None:
    r = plat.rect
    key = (r.w, r.h, theme, plat.dropthrough)
    surf = _platform_cache.get(key)
    if surf is None:
        surf = _platform_cache[key] = _platform_surface(r.w, r.h, theme, plat.dropthrough)
    canvas.blit(surf, r.topleft)

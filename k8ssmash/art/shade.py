"""Turns flat silhouettes into SNES-style shaded pixel art: height-map lighting quantized to a
hue-shifted color ramp, ordered dithering on band edges, specular glints and colored outlines."""
from __future__ import annotations

import colorsys

import numpy as np
import pygame

from k8ssmash.art.draw import SS, Layer

Color = tuple[int, int, int]
LEVELS = 6
LIGHT = np.array([-0.48, -0.66, 0.58])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
HALF = (LIGHT + np.array([0.0, 0.0, 1.0]))
HALF = HALF / np.linalg.norm(HALF)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5
DITHER = 0.38  # tone-levels of ordered-dither jitter: enough to blend band edges, not to speckle
SHINY = ("steel", "metal", "screen", "bone", "leaf", "armor", "gold")


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def make_ramp(base: Color) -> np.ndarray:
    """Six tones from shadow to highlight. Shadows drift cool and purple, highlights drift warm."""
    c = tuple(float(v) for v in base)
    ramp = [
        _mix(tuple(v * 0.30 for v in c), (28, 18, 78), 0.40),
        _mix(tuple(v * 0.52 for v in c), (44, 32, 110), 0.20),
        tuple(v * 0.78 for v in c),
        c,
        _mix(c, (255, 244, 208), 0.32),
        _mix(c, (255, 252, 238), 0.72),
    ]
    return np.clip(np.array(ramp), 0, 255).astype(np.uint8)


def shift(m: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Like np.roll but zero-filled: nothing wraps around the frame edge."""
    out = np.zeros_like(m)
    h, w = m.shape
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = m[ys, xs]
    return out


def _erode(m: np.ndarray) -> np.ndarray:
    return m & shift(m, 1, 0) & shift(m, -1, 0) & shift(m, 0, 1) & shift(m, 0, -1)


def layer_mask(layer: Layer, size: int) -> np.ndarray:
    a = pygame.surfarray.array_alpha(layer).T > 0  # (y, x), supersampled
    cover = a.reshape(size, SS, size, SS).mean(axis=(1, 3))
    return cover >= 0.5


def shade(mask: np.ndarray, shiny: bool, flat: bool = False) -> np.ndarray:
    """Tone index (0..LEVELS-1) for every pixel of the part, -1 outside it."""
    size = mask.shape[0]
    depth = np.zeros(mask.shape)
    cur = mask.copy()
    for _ in range(12):
        if not cur.any():
            break
        depth += cur
        cur = _erode(cur)
    dmax = max(depth.max(), 1.0)
    height = (depth / dmax) ** 0.55 * min(dmax, 5.0) * (0.35 if flat else 1.0)
    # smooth the height a touch so bands follow the form instead of the pixel grid
    k = np.array([1, 2, 1]) / 4.0
    for axis in (0, 1):
        height = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, height)
    gy, gx = np.gradient(height)
    normal = np.dstack([-gx * 1.1, -gy * 1.1, np.ones_like(height)])
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    diffuse = np.clip(normal @ LIGHT, 0, 1)
    ys = np.arange(size)[:, None] * np.ones((1, size))
    rows = np.where(mask.any(axis=1))[0]
    y0, y1 = (rows.min(), rows.max()) if len(rows) else (0, 1)
    vertical = 0.5 - (ys - y0) / max(1, y1 - y0)  # +0.5 at the top of the part, -0.5 at the bottom
    t = 0.22 + 0.74 * diffuse + 0.16 * vertical
    bayer = np.tile(BAYER, (size // 4 + 1, size // 4 + 1))[:size, :size]
    idx = np.floor(np.clip(t * LEVELS + bayer * DITHER, 0, LEVELS - 0.001)).astype(int)
    if shiny:
        spec = np.clip(normal @ HALF, 0, 1) ** 28
        idx = np.where(spec > 0.55, LEVELS - 1, idx)
    # bounce light: the bottom-right rim catches a little light from the ground
    rim = mask & ~shift(mask, -1, -1)
    idx = np.where(rim & (idx < 2), 2, idx)
    return np.where(mask, idx, -1)


def paint_part(frame: np.ndarray, mask: np.ndarray, ramp: np.ndarray, shiny: bool, flat: bool = False) -> None:
    """Composite one shaded part (with a colored outline) onto the RGBA frame array."""
    idx = shade(mask, shiny, flat)
    ring = np.zeros_like(mask)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ring |= shift(mask, dy, dx)
    ring &= ~mask
    outline = tuple(int(v * 0.55) for v in _mix(ramp[0], (10, 6, 34), 0.35))
    frame[ring, :3] = outline
    frame[ring, 3] = 255
    sel = mask
    frame[sel, :3] = ramp[np.clip(idx[sel], 0, LEVELS - 1)]
    frame[sel, 3] = 255

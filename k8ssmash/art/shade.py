"""Turns flat silhouettes into SNES-style shaded pixel art: height-map lighting quantized to a
hue-shifted color ramp, ordered dithering on band edges, specular glints and colored outlines."""
from __future__ import annotations

import colorsys

import numpy as np
import pygame

from k8ssmash.art.draw import SS, Layer
from k8ssmash.config import RS

Color = tuple[int, int, int]
LEVELS = 9  # tonal steps per material: a 16-bit sprite has far smoother form shading than an 8-bit one
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
    keys = [
        _mix(tuple(v * 0.30 for v in c), (28, 18, 78), 0.40),
        _mix(tuple(v * 0.52 for v in c), (44, 32, 110), 0.20),
        tuple(v * 0.78 for v in c),
        c,
        _mix(c, (255, 244, 208), 0.32),
        _mix(c, (255, 252, 238), 0.72),
    ]
    keys = np.array(keys)
    at = np.linspace(0, len(keys) - 1, LEVELS)  # resample the six key tones into nine smooth steps
    ramp = np.stack([np.interp(at, np.arange(len(keys)), keys[:, ch]) for ch in range(3)], axis=1)
    return np.clip(ramp, 0, 255).astype(np.uint8)


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
    k = SS // RS  # supersamples per output pixel (4)
    cover = a.reshape(size, k, size, k).mean(axis=(1, 3))
    return cover >= 0.5


def _cel(mask: np.ndarray) -> np.ndarray:
    """Hand-painted look: one flat base tone, a deliberate shadow shape along the lower-right edge (with a darker line
    at the very rim), a bright rim on the upper-left and a slightly deeper foot, like cel animation. The bands shrink on
    thin parts (a hat brim, a strap) so they keep their colour instead of turning into shadow."""
    k = RS
    cur, depth = mask.copy(), 0
    while cur.any() and depth < 14 * k:
        depth += 1
        cur = _erode(cur)
    band_w = max(1, round(min(4 * k, depth * 0.55)))
    core_w = max(1, round(min(2 * k, depth * 0.28)))
    rim_w = max(1, round(min(3 * k, depth * 0.42)))
    idx = np.full(mask.shape, 5)
    band = mask & ~shift(mask, -band_w, -band_w)
    core = mask & ~shift(mask, -core_w, -core_w)
    rim = mask & ~shift(mask, rim_w, rim_w)
    rows = np.where(mask.any(axis=1))[0]
    if len(rows) and depth > 3 * k:
        y0, y1 = rows.min(), rows.max()
        ys = np.arange(mask.shape[0])[:, None] * np.ones((1, mask.shape[1]))
        idx = np.where(ys > y0 + 0.78 * (y1 - y0), 4, idx)
    idx = np.where(band, 3, idx)
    idx = np.where(core, 2, idx)
    idx = np.where(rim & ~band, 7, idx)
    return np.where(mask, idx, -1)


def shade(mask: np.ndarray, shiny: bool, flat: bool = False, texture: str = "", cel: bool = False,
          plain: bool = False) -> np.ndarray:
    """Tone index (0..LEVELS-1) for every pixel of the part, -1 outside it."""
    if plain:
        return np.where(mask, 5, -1)
    if cel:
        return _cel(mask)
    h_, w_ = mask.shape
    depth = np.zeros(mask.shape)
    cur = mask.copy()
    for _ in range(12 * RS):
        if not cur.any():
            break
        depth += cur
        cur = _erode(cur)
    dmax = max(depth.max(), 1.0)
    height = (depth / dmax) ** 0.55 * min(dmax, 5.0 * RS) * (0.35 if flat else 1.0)
    # smooth the height a touch so bands follow the form instead of the pixel grid
    k = np.array([1, 2, 1]) / 4.0
    for axis in (0, 1):
        for _ in range(RS):
            height = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, height)
    gy, gx = np.gradient(height)
    normal = np.dstack([-gx * 1.1, -gy * 1.1, np.ones_like(height)])
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    diffuse = np.clip(normal @ LIGHT, 0, 1)
    ys = np.arange(h_)[:, None] * np.ones((1, w_))
    rows = np.where(mask.any(axis=1))[0]
    y0, y1 = (rows.min(), rows.max()) if len(rows) else (0, 1)
    vertical = 0.5 - (ys - y0) / max(1, y1 - y0)  # +0.5 at the top of the part, -0.5 at the bottom
    t = 0.22 + 0.74 * diffuse + 0.16 * vertical
    bayer = np.tile(BAYER, (h_ // 4 + 1, w_ // 4 + 1))[:h_, :w_]
    idx = np.floor(np.clip(t * LEVELS + bayer * DITHER, 0, LEVELS - 0.001)).astype(int)
    if shiny:
        spec = np.clip(normal @ HALF, 0, 1) ** 28
        idx = np.where(spec > 0.55, LEVELS - 1, idx)
    if texture:
        idx = _texture(idx, mask, texture)
    # bounce light: the bottom-right rim catches a little light from the ground
    rim = mask & ~shift(mask, -RS, -RS)
    idx = np.where(rim & (idx < 3), 3, idx)
    return np.where(mask, idx, -1)


def _texture(idx: np.ndarray, mask: np.ndarray, kind: str) -> np.ndarray:
    """Surface detail on top of the lighting: fur strokes, cloth folds, metal banding, panel seams."""
    h, w = mask.shape
    ys, xs = np.mgrid[0:h, 0:w]
    out = idx.copy()
    noise = ((xs * 73856093) ^ (ys * 19349663)) % 100  # a stable per-pixel hash, so frames don't shimmer
    if kind == "fur":  # short vertical strokes, some dark and some light
        stroke = (noise < 15) | (np.roll(noise, 1, 0) < 15) & (noise % 2 == 0)
        out = np.where(stroke & mask & (idx > 0), np.where(noise % 3 == 0, idx + 1, idx - 1), out)
    elif kind == "cloth":  # diagonal folds
        fold = ((xs + 2 * ys) % (11 * RS) < RS) & (idx >= 2)
        out = np.where(fold & mask, idx - 1, out)
        crest = (((xs + 2 * ys) % (11 * RS) >= RS) & ((xs + 2 * ys) % (11 * RS) < 2 * RS)) & (idx >= 2)
        out = np.where(crest & mask, idx + 1, out)
    elif kind == "metal":  # brushed horizontal banding with a bright edge
        band = (ys % (6 * RS) < RS) & mask
        out = np.where(band, idx + 1, out)
    elif kind == "panel":  # plate seams
        seam = ((xs % (7 * RS) < RS) | (ys % (8 * RS) < RS)) & mask & (idx > 0)
        out = np.where(seam, idx - 1, out)
    return np.clip(out, 0, LEVELS - 1)


def paint_part(frame: np.ndarray, mask: np.ndarray, ramp: np.ndarray, shiny: bool, flat: bool = False,
               texture: str = "", cel: bool = False, plain: bool = False) -> None:
    """Composite one shaded part (with a colored outline) onto the RGBA frame array."""
    idx = shade(mask, shiny, flat, texture, cel, plain)
    grown = mask.copy()
    for _ in range(RS):  # the outline is one rig unit thick: RS output pixels
        step = grown.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            step |= shift(grown, dy, dx)
        grown = step
    ring = grown & ~mask
    outline = tuple(int(v * 0.42) for v in _mix(tuple(float(x) for x in ramp[0]), (8, 4, 28), 0.5))  # a bolder, inkier outline
    frame[ring, :3] = outline
    frame[ring, 3] = 255
    sel = mask
    frame[sel, :3] = ramp[np.clip(idx[sel], 0, LEVELS - 1)]
    frame[sel, 3] = 255
    # cool rim light from the backlight on the shadow-side edge, and a touch of ambient occlusion where parts curl under
    edge_r = mask & ~shift(mask, -RS, 0) & (idx >= 2)
    edge_b = mask & ~shift(mask, 0, -RS)
    rimc = np.array([120, 175, 255], dtype=float)
    frame[edge_r, :3] = (frame[edge_r, :3] * 0.62 + rimc * 0.38).astype(np.uint8)
    frame[edge_b, :3] = (frame[edge_b, :3] * 0.80).astype(np.uint8)

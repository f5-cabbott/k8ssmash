"""How busy is each stage backdrop? Reports bright-pixel share and fast-motion share (the 'looks like a projectile' measure)."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import numpy as np
import pygame

pygame.init()
pygame.display.set_mode((1, 1))
from k8ssmash import backdrops
from k8ssmash.config import WORLD_H, WORLD_W


def luma(surf: pygame.Surface) -> np.ndarray:
    a = pygame.surfarray.array3d(surf).astype(float)
    return 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]


def blob(a: np.ndarray, b: np.ndarray) -> float:
    changed = np.abs(b - a) > 45
    changed[:, changed.sum(axis=0) > a.shape[0] * 0.4] = False
    return float(changed.mean())


def measure(theme: str) -> dict:
    bd = backdrops.get_backdrop(theme)
    canvas = pygame.Surface((WORLD_W, WORLD_H))
    frames = []
    for f in (300, 301, 302, 360):
        bd.draw(canvas, f, 0)
        frames.append(luma(canvas))
    a, b, _, c = frames
    n = a.size
    return {
        "bright": float((a > 150).sum() / n),            # share of strongly lit pixels
        "very_bright": float((a > 215).sum() / n),       # near-white specks: what reads as a projectile
        "fast_motion": blob(a, b),  # small sharp changes between consecutive frames (full-width floor lines excluded)
        "slow_motion": float((np.abs(c - a) > 45).sum() / n),
        "mean_luma": float(a.mean()),
    }


if __name__ == "__main__":
    print(f"{'stage':14s} {'bright>150':>10s} {'white>215':>10s} {'fast-move':>10s} {'slow-move':>10s} {'mean':>6s}")
    for theme in ("datacenter", "controlplane", "nodepool"):
        m = measure(theme)
        print(f"{theme:14s} {m['bright'] * 100:9.2f}% {m['very_bright'] * 100:9.3f}% {m['fast_motion'] * 100:9.3f}% "
              f"{m['slow_motion'] * 100:9.2f}% {m['mean_luma']:6.1f}")

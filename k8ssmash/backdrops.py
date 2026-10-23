"""Procedural stage backdrops and platform art, one look per stage theme."""
from __future__ import annotations

import math
import random

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W
from k8ssmash.stage import Platform

THEMES = {
    "datacenter": {"sky": ((14, 18, 36), (30, 38, 70)), "top": (130, 160, 225), "body": (62, 80, 130), "line": (46, 60, 100)},
    "controlplane": {"sky": ((12, 24, 52), (24, 56, 110)), "top": (110, 190, 255), "body": (36, 70, 140), "line": (28, 54, 112)},
    "nodepool": {"sky": ((20, 14, 40), (62, 36, 92)), "top": (200, 160, 255), "body": (84, 58, 128), "line": (66, 44, 104)},
}

_cache: dict[str, pygame.Surface] = {}


def _gradient(top: tuple, bottom: tuple) -> pygame.Surface:
    surf = pygame.Surface((CANVAS_W, CANVAS_H))
    for y in range(0, CANVAS_H, 4):
        t = y / CANVAS_H
        color = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        pygame.draw.rect(surf, color, (0, y, CANVAS_W, 4))
    return surf


def _helm(canvas: pygame.Surface, cx: int, cy: int, r: int, angle: float, color) -> None:
    pygame.draw.circle(canvas, color, (cx, cy), r, 3)
    for i in range(7):
        a = angle + i * 2 * math.pi / 7
        pygame.draw.line(canvas, color, (cx, cy), (cx + math.cos(a) * (r + 6), cy + math.sin(a) * (r + 6)), 3)


def draw_backdrop(canvas: pygame.Surface, theme: str, frame: int) -> None:
    pal = THEMES.get(theme, THEMES["datacenter"])
    if theme not in _cache:
        _cache[theme] = _gradient(*pal["sky"])
    canvas.blit(_cache[theme], (0, 0))
    if theme == "datacenter":
        rng = random.Random(7)
        for i in range(9):  # server racks with blinking LEDs
            x = 10 + i * 72
            h = 150 + (i * 37) % 60
            pygame.draw.rect(canvas, (20, 26, 50), (x, 290 - h, 56, h))
            pygame.draw.rect(canvas, (30, 38, 70), (x, 290 - h, 56, h), 2)
            for row in range(h // 14):
                y = 290 - h + 6 + row * 14
                pygame.draw.rect(canvas, (26, 34, 62), (x + 5, y, 46, 9))
                on = (frame // (20 + (row * 7 + i * 3) % 30) + row + i) % 3 == 0
                led = (90, 255, 140) if on else ((255, 190, 70) if rng.random() < 0.15 else (36, 52, 90))
                pygame.draw.rect(canvas, led, (x + 8, y + 3, 3, 3))
    elif theme == "controlplane":
        for gx in range(0, CANVAS_W, 40):
            pygame.draw.line(canvas, (28, 56, 112), (gx, 0), (gx, CANVAS_H))
        for gy in range(0, CANVAS_H, 40):
            pygame.draw.line(canvas, (28, 56, 112), (0, gy), (CANVAS_W, gy))
        _helm(canvas, CANVAS_W // 2, 120, 70, frame * 0.004, (34, 74, 150))
        for i in range(6):  # nodes pulsing around the wheel
            a = frame * 0.01 + i * math.pi / 3
            pygame.draw.circle(canvas, (90, 170, 255), (CANVAS_W // 2 + int(math.cos(a) * 120), 120 + int(math.sin(a) * 70)), 4)
    else:  # nodepool: drifting nodes joined by links
        rng = random.Random(11)
        pts = [(rng.randrange(CANVAS_W), rng.randrange(40, 230)) for _ in range(14)]
        pts = [(x + math.sin(frame * 0.01 + i) * 10, y + math.cos(frame * 0.012 + i) * 8) for i, (x, y) in enumerate(pts)]
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                if math.dist(a, b) < 120:
                    pygame.draw.line(canvas, (70, 48, 110), a, b)
        for x, y in pts:
            pygame.draw.circle(canvas, (150, 110, 220), (round(x), round(y)), 4)
        canvas_h = CANVAS_H
        pygame.draw.rect(canvas, (14, 8, 28), (0, canvas_h - 40, CANVAS_W, 40))


def draw_platform(canvas: pygame.Surface, plat: Platform, theme: str) -> None:
    pal = THEMES.get(theme, THEMES["datacenter"])
    r = plat.rect
    pygame.draw.rect(canvas, pal["body"], r)
    if r.height > 12:
        for y in range(r.top + 12, r.bottom, 12):
            pygame.draw.line(canvas, pal["line"], (r.left, y), (r.right - 1, y))
        for row, y in enumerate(range(r.top, r.bottom, 12)):
            for x in range(r.left + (row % 2) * 20, r.right, 40):
                pygame.draw.line(canvas, pal["line"], (x, y), (x, min(y + 12, r.bottom)))
    pygame.draw.rect(canvas, pal["top"], (r.x, r.y, r.w, 3))
    pygame.draw.rect(canvas, tuple(int(c * 0.6) for c in pal["body"]), (r.x, r.bottom - 2, r.w, 2))
    if plat.dropthrough:
        pygame.draw.rect(canvas, pal["top"], r, 1)

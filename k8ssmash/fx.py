"""Procedural drawing for projectiles and combat effects (kept out of battle.py for readability)."""
from __future__ import annotations

import math

import pygame

from k8ssmash.fighter import Projectile

OUTLINE = (16, 12, 28)


def _dark(c, k=0.45):
    return tuple(int(v * k) for v in c)


def draw_projectile(canvas: pygame.Surface, p: Projectile) -> None:
    d = p.defn
    x, y = round(p.x), round(p.y)
    c = d.color
    shape = d.shape
    t = p.age
    if shape == "bolt":
        ang = math.atan2(p.vy, p.vx) if (p.vx or p.vy) else 0.0
        tail = (x - math.cos(ang) * d.width, y - math.sin(ang) * d.width)
        pygame.draw.line(canvas, _dark(c), tail, (x, y), d.height + 2)
        pygame.draw.line(canvas, c, tail, (x, y), d.height - 1)
        pygame.draw.circle(canvas, (255, 255, 255), (x, y), max(2, d.height // 2 - 1))
    elif shape == "drum":  # a storage drum rolling through the air: banded barrel, hoops that scroll with the spin
        w, h = d.width, d.height
        body = pygame.Rect(x - w // 2, y - h // 2 + 3, w, h - 6)
        pygame.draw.rect(canvas, OUTLINE, body.inflate(2, 2), border_radius=3)
        pygame.draw.rect(canvas, c, body, border_radius=3)
        pygame.draw.rect(canvas, tuple(min(255, v + 60) for v in c), (body.x + 2, body.y + 1, body.w - 4, 3), border_radius=2)
        for k in range(3):
            hx = body.x + (k * 7 + t * 2) % (body.w - 2) + 1
            pygame.draw.line(canvas, _dark(c, 0.55), (hx, body.y + 1), (hx, body.bottom - 2), 2)
        pygame.draw.ellipse(canvas, tuple(min(255, v + 80) for v in c), (body.x - 2, body.y - 1, 6, body.h + 2))
        pygame.draw.ellipse(canvas, OUTLINE, (body.x - 2, body.y - 1, 6, body.h + 2), 1)
    elif shape == "wheel":
        r = d.width // 2
        pygame.draw.circle(canvas, _dark(c), (x, y), r + 1, 4)
        pygame.draw.circle(canvas, c, (x, y), r, 2)
        for i in range(6):
            a = t * 0.3 + i * math.pi / 3
            pygame.draw.line(canvas, c, (x, y), (x + math.cos(a) * r, y + math.sin(a) * r), 2)
    elif shape == "banana":
        pygame.draw.arc(canvas, OUTLINE, (x - 8, y - 7, 16, 14), 3.4, 6.0, 5)
        pygame.draw.arc(canvas, c, (x - 8, y - 7, 16, 14), 3.4, 6.0, 3)
    elif shape == "bomb":
        flash = d.explode_radius and p.life < 30 and (t // 3) % 2 == 0
        body = (255, 255, 255) if flash else _dark(c, 0.7)
        pygame.draw.circle(canvas, OUTLINE, (x, y), 8)
        pygame.draw.circle(canvas, body, (x, y), 7)
        pygame.draw.circle(canvas, c, (x - 2, y - 2), 3)
        pygame.draw.line(canvas, (255, 220, 120), (x + 3, y - 6), (x + 6, y - 10 - (t // 2) % 2), 2)
    elif shape == "drone":
        bob = round(math.sin(t * 0.3) * 1.5)
        pygame.draw.circle(canvas, OUTLINE, (x, y + bob), 8)
        pygame.draw.circle(canvas, c, (x, y + bob), 7)
        pygame.draw.circle(canvas, (255, 255, 255), (x + 2, y + bob - 1), 2)
        pygame.draw.line(canvas, OUTLINE, (x - 9, y + bob - 5), (x + 9, y + bob - 5), 2)
    elif shape == "wall":
        r = p.rect
        glow = 150 + int(60 * math.sin(t * 0.4))
        pygame.draw.rect(canvas, _dark(c), r.inflate(4, 2))
        pygame.draw.rect(canvas, (255, glow, 70), r)
        pygame.draw.line(canvas, (255, 240, 180), (r.centerx, r.top), (r.centerx, r.bottom), 1)
    elif shape == "skull":
        pygame.draw.circle(canvas, c, (x, y), 11, 1)
        pygame.draw.ellipse(canvas, OUTLINE, (x - 8, y - 8, 16, 14))
        pygame.draw.ellipse(canvas, (238, 232, 215), (x - 7, y - 7, 14, 12))
        pygame.draw.rect(canvas, (50, 20, 40), (x - 5, y - 3, 3, 3))
        pygame.draw.rect(canvas, (50, 20, 40), (x + 2, y - 3, 3, 3))
    elif shape == "ring":
        r = d.width // 2
        for i, k in enumerate((1.0, 0.7, 0.4)):
            pygame.draw.circle(canvas, c if i != 1 else (255, 255, 255), (x, y), round(r * k), 2)
    else:  # orb
        pygame.draw.ellipse(canvas, _dark(c), p.rect.inflate(2, 2))
        pygame.draw.ellipse(canvas, c, p.rect)
        pygame.draw.circle(canvas, (255, 255, 255), (x - 1, y - 1), 2)


def draw_effect(canvas: pygame.Surface, kind: str, x: float, y: float, left: int) -> None:
    x, y = round(x), round(y)
    if kind == "hit":
        r = 4 + (10 - left) * 2
        for i in range(8):
            a = i * math.pi / 4 + 0.3
            pygame.draw.line(canvas, (255, 245, 170),
                             (x + math.cos(a) * r * 0.4, y + math.sin(a) * r * 0.4),
                             (x + math.cos(a) * r, y + math.sin(a) * r), 2)
    elif kind == "boom":
        r = 8 + (20 - left) * 3
        pygame.draw.circle(canvas, (255, 150, 60), (x, y), r, 4)
        pygame.draw.circle(canvas, (255, 240, 150), (x, y), max(2, r - 8), 2)
    elif kind == "counter":
        r = 6 + (18 - left) * 2
        pygame.draw.circle(canvas, (255, 255, 255), (x, y), r, 2)
        pygame.draw.line(canvas, (255, 220, 90), (x - r, y - r), (x + r, y + r), 2)
        pygame.draw.line(canvas, (255, 220, 90), (x - r, y + r), (x + r, y - r), 2)
    elif kind == "pickup":
        r = 6 + (24 - left)
        for i in range(6):
            a = i * math.pi / 3 + left * 0.15
            pygame.draw.circle(canvas, (255, 245, 170), (x + math.cos(a) * r, y + math.sin(a) * r * 1.3), 2)

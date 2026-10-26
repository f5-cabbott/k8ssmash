"""Procedural drawing for projectiles and combat effects (kept out of battle.py for readability)."""
from __future__ import annotations

import math

import pygame

from k8ssmash.fighter import Projectile
from k8ssmash.ui import wd

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
        wd.line(canvas, _dark(c), tail, (x, y), d.height + 2)
        wd.line(canvas, c, tail, (x, y), d.height - 1)
        wd.circle(canvas, (255, 255, 255), (x, y), max(2, d.height // 2 - 1))
    elif shape == "drum":  # a storage drum rolling through the air: banded barrel, hoops that scroll with the spin
        w, h = d.width, d.height
        body = pygame.Rect(x - w // 2, y - h // 2 + 3, w, h - 6)
        wd.rect(canvas, OUTLINE, body.inflate(2, 2), border_radius=3)
        wd.rect(canvas, c, body, border_radius=3)
        wd.rect(canvas, tuple(min(255, v + 60) for v in c), (body.x + 2, body.y + 1, body.w - 4, 3), border_radius=2)
        for k in range(3):
            hx = body.x + (k * 7 + t * 2) % (body.w - 2) + 1
            wd.line(canvas, _dark(c, 0.55), (hx, body.y + 1), (hx, body.bottom - 2), 2)
        wd.ellipse(canvas, tuple(min(255, v + 80) for v in c), (body.x - 2, body.y - 1, 6, body.h + 2))
        wd.ellipse(canvas, OUTLINE, (body.x - 2, body.y - 1, 6, body.h + 2), 1)
    elif shape == "wheel":
        r = d.width // 2
        wd.circle(canvas, _dark(c), (x, y), r + 1, 4)
        wd.circle(canvas, c, (x, y), r, 2)
        for i in range(6):
            a = t * 0.3 + i * math.pi / 3
            wd.line(canvas, c, (x, y), (x + math.cos(a) * r, y + math.sin(a) * r), 2)
    elif shape == "clock":  # a little alarm clock: ringing bells, a face and hands that sweep as it flies
        shake = (t // 2) % 2
        wd.circle(canvas, OUTLINE, (x - 5, y - 8 + shake), 3)
        wd.circle(canvas, OUTLINE, (x + 5, y - 8 + shake), 3)
        wd.circle(canvas, c, (x - 5, y - 8 + shake), 2)
        wd.circle(canvas, c, (x + 5, y - 8 + shake), 2)
        wd.circle(canvas, OUTLINE, (x, y), 9)
        wd.circle(canvas, c, (x, y), 8)
        wd.circle(canvas, (252, 250, 240), (x, y), 6)
        a = t * 0.35
        wd.line(canvas, OUTLINE, (x, y), (x + math.cos(a) * 5, y + math.sin(a) * 5), 1)
        wd.line(canvas, (200, 50, 50), (x, y), (x + math.cos(a * 0.12) * 3, y + math.sin(a * 0.12) * 3), 1)
    elif shape == "bird":  # a little canary flapping down the lane
        flap = round(math.sin(t * 0.8) * 3)
        wd.circle(canvas, OUTLINE, (x, y), 5)
        wd.circle(canvas, c, (x, y), 4)
        wd.polygon(canvas, (255, 150, 50), [(x + 3 * p.facing, y - 1), (x + 7 * p.facing, y), (x + 3 * p.facing, y + 1)])
        wd.polygon(canvas, tuple(max(0, v - 40) for v in c), [(x - 1, y), (x - 5 * p.facing, y - 4 - flap), (x - 7 * p.facing, y - 1)])
        wd.circle(canvas, (30, 20, 40), (x + 1.5 * p.facing, y - 1), 0.9)
    elif shape == "well":  # a swirling gravity well: rings contract toward a dark core, with a faint reach ring
        reach = d.pull_radius or 80
        wd.circle(canvas, _dark(c, 0.35), (x, y), reach, 1)
        for i in range(4):
            u = (t * 0.035 + i / 4) % 1.0
            rr = max(2, round(reach * 0.62 * (1 - u)))
            wd.circle(canvas, tuple(int(v * (0.35 + 0.65 * (1 - u))) for v in c), (x, y), rr, 2)
        for i in range(5):
            a = t * 0.12 + i * 2 * math.pi / 5
            wd.circle(canvas, (255, 255, 255), (x + math.cos(a) * 15, y + math.sin(a) * 15), 1)
        wd.circle(canvas, (14, 8, 34), (x, y), 8)
        wd.circle(canvas, c, (x, y), 8, 1)
        hand = t * 0.2
        wd.line(canvas, (255, 255, 255), (x, y), (x + math.cos(hand) * 6, y + math.sin(hand) * 6), 1)
    elif shape == "bubble":  # a wobbling soap bubble with a bright glint
        r = d.width // 2
        wob = round(math.sin(t * 0.3) * 1.2)
        wd.circle(canvas, _dark(c, 0.5), (x, y), r + 1, 2)
        wd.circle(canvas, c, (x, y), r, 2)
        wd.circle(canvas, tuple(min(255, v + 70) for v in c), (x - r // 3, y - r // 3 + wob), max(2, r // 4))
        wd.circle(canvas, (255, 255, 255), (x + r // 3, y + r // 4), 1)
    elif shape == "spark":  # a crackling zig-zag of current
        ang = math.atan2(p.vy, p.vx) if (p.vx or p.vy) else 0.0
        pts = []
        for i in range(7):
            u = i / 6
            off = ((i % 2) * 2 - 1) * (d.height * 0.5) * (0.4 + 0.6 * math.sin(t * 0.7 + i))
            px = x - math.cos(ang) * d.width * (0.5 - u) * 1.6 - math.sin(ang) * off
            py = y - math.sin(ang) * d.width * (0.5 - u) * 1.6 + math.cos(ang) * off
            pts.append((px, py))
        wd.lines(canvas, _dark(c, 0.5), False, pts, 5)
        wd.lines(canvas, c, False, pts, 3)
        wd.lines(canvas, (255, 255, 255), False, pts, 1)
    elif shape == "bomb":
        flash = d.explode_radius and p.life < 30 and (t // 3) % 2 == 0
        body = (255, 255, 255) if flash else _dark(c, 0.7)
        wd.circle(canvas, OUTLINE, (x, y), 8)
        wd.circle(canvas, body, (x, y), 7)
        wd.circle(canvas, c, (x - 2, y - 2), 3)
        wd.line(canvas, (255, 220, 120), (x + 3, y - 6), (x + 6, y - 10 - (t // 2) % 2), 2)
    elif shape == "drone":
        bob = round(math.sin(t * 0.3) * 1.5)
        wd.circle(canvas, OUTLINE, (x, y + bob), 8)
        wd.circle(canvas, c, (x, y + bob), 7)
        wd.circle(canvas, (255, 255, 255), (x + 2, y + bob - 1), 2)
        wd.line(canvas, OUTLINE, (x - 9, y + bob - 5), (x + 9, y + bob - 5), 2)
    elif shape == "wall":
        r = p.rect
        glow = 150 + int(60 * math.sin(t * 0.4))
        wd.rect(canvas, _dark(c), r.inflate(4, 2))
        wd.rect(canvas, (255, glow, 70), r)
        wd.line(canvas, (255, 240, 180), (r.centerx, r.top), (r.centerx, r.bottom), 1)
    elif shape == "skull":
        wd.circle(canvas, c, (x, y), 11, 1)
        wd.ellipse(canvas, OUTLINE, (x - 8, y - 8, 16, 14))
        wd.ellipse(canvas, (238, 232, 215), (x - 7, y - 7, 14, 12))
        wd.rect(canvas, (50, 20, 40), (x - 5, y - 3, 3, 3))
        wd.rect(canvas, (50, 20, 40), (x + 2, y - 3, 3, 3))
    elif shape == "ring":
        r = d.width // 2
        for i, k in enumerate((1.0, 0.7, 0.4)):
            wd.circle(canvas, c if i != 1 else (255, 255, 255), (x, y), round(r * k), 2)
    else:  # orb
        wd.ellipse(canvas, _dark(c), p.rect.inflate(2, 2))
        wd.ellipse(canvas, c, p.rect)
        wd.circle(canvas, (255, 255, 255), (x - 1, y - 1), 2)


def draw_effect(canvas: pygame.Surface, kind: str, x: float, y: float, left: int) -> None:
    x, y = round(x), round(y)
    if kind == "hit":
        r = 4 + (10 - left) * 2
        for i in range(8):
            a = i * math.pi / 4 + 0.3
            wd.line(canvas, (255, 245, 170),
                             (x + math.cos(a) * r * 0.4, y + math.sin(a) * r * 0.4),
                             (x + math.cos(a) * r, y + math.sin(a) * r), 2)
    elif kind == "hit_heavy":  # the big Street Fighter impact star: a jagged burst that pops out and settles
        total = 14
        k = min(1.0, (total - left) / 4.0) * (1.0 if left > 5 else left / 5.0)
        for scale, color in ((1.0, (255, 120, 50)), (0.78, (255, 230, 120)), (0.42, (255, 255, 255))):
            pts = []
            for i in range(20):
                a = i * math.pi / 10 + 0.25
                rad = (30 if i % 2 == 0 else 12) * scale * k * (1.0 + 0.25 * ((i * 7) % 3 == 0))
                pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad * 0.9))
            if k > 0.1:
                wd.polygon(canvas, color, pts)
    elif kind == "boom":
        r = 8 + (20 - left) * 3
        wd.circle(canvas, (255, 150, 60), (x, y), r, 4)
        wd.circle(canvas, (255, 240, 150), (x, y), max(2, r - 8), 2)
    elif kind == "counter":
        r = 6 + (18 - left) * 2
        wd.circle(canvas, (255, 255, 255), (x, y), r, 2)
        wd.line(canvas, (255, 220, 90), (x - r, y - r), (x + r, y + r), 2)
        wd.line(canvas, (255, 220, 90), (x - r, y + r), (x + r, y - r), 2)
    elif kind == "pickup":
        r = 6 + (24 - left)
        for i in range(6):
            a = i * math.pi / 3 + left * 0.15
            wd.circle(canvas, (255, 245, 170), (x + math.cos(a) * r, y + math.sin(a) * r * 1.3), 2)

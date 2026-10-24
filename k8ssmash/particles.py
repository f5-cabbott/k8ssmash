"""A small particle system for game-feel: dust, sparks, rings, stars and confetti.

Everything is drawn with plain shapes that fade by shrinking or shifting colour, never with translucent surfaces
and never with flashing, so it stays cheap on a Pi and easy on the eyes."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

Color = tuple[int, int, int]
MAX_PARTICLES = 400


def _mix(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


@dataclass
class Particle:
    kind: str  # dust | spark | square | ring | star | confetti
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: Color
    size: float = 3.0
    gravity: float = 0.0
    drag: float = 1.0
    age: int = 0
    phase: float = 0.0

    @property
    def t(self) -> float:
        return self.age / self.life


class Particles:
    def __init__(self, seed: int | None = None, scale: float = 1.0):
        self.scale = scale  # menus author positions in design units; battles draw 1:1
        self.items: list[Particle] = []
        self.rng = random.Random(seed)

    def __len__(self) -> int:
        return len(self.items)

    def _add(self, p: Particle) -> None:
        if len(self.items) < MAX_PARTICLES:
            self.items.append(p)

    # --- emitters ----------------------------------------------------------------------------
    def dust(self, x: float, y: float, strength: float = 1.0, color: Color = (190, 205, 235)) -> None:
        """Puffs kicked out sideways along the ground."""
        for i in range(2 + int(5 * strength)):
            side = -1 if i % 2 else 1
            self._add(Particle("dust", x + side * self.rng.uniform(2, 8), y - 1, side * self.rng.uniform(0.4, 1.6) * (0.5 + strength),
                               -self.rng.uniform(0.1, 0.7), self.rng.randint(16, 26), color, self.rng.uniform(2.0, 3.6) * (0.7 + 0.5 * strength),
                               gravity=-0.01, drag=0.93))

    def ring(self, x: float, y: float, color: Color = (255, 255, 255), size: float = 18.0, life: int = 18) -> None:
        self._add(Particle("ring", x, y, 0, 0, life, color, size))

    def burst(self, x: float, y: float, color: Color, count: int = 10, speed: float = 3.0, angle: float | None = None,
              spread: float = math.tau, kind: str = "spark", life: tuple[int, int] = (10, 20)) -> None:
        """Sparks radiating from a point; `angle` (radians) aims the burst and `spread` is its width."""
        for _ in range(count):
            a = (angle if angle is not None else self.rng.uniform(0, math.tau)) + self.rng.uniform(-spread / 2, spread / 2)
            v = speed * self.rng.uniform(0.45, 1.15)
            self._add(Particle(kind, x, y, math.cos(a) * v, math.sin(a) * v, self.rng.randint(*life), color,
                               self.rng.uniform(2.0, 3.4), gravity=0.07, drag=0.94))

    def sparkle(self, x: float, y: float, color: Color = (255, 245, 170), count: int = 3, spread: float = 14.0) -> None:
        for _ in range(count):
            self._add(Particle("square", x + self.rng.uniform(-spread, spread), y + self.rng.uniform(-spread, spread),
                               self.rng.uniform(-0.2, 0.2), -self.rng.uniform(0.3, 0.9), self.rng.randint(18, 32), color,
                               self.rng.uniform(1.5, 2.6)))

    def streak(self, x: float, y: float, vx: float, vy: float, color: Color = (255, 255, 255)) -> None:
        """A speed line trailing a hard launch: it stays put while the fighter moves on."""
        self._add(Particle("spark", x, y, -vx * 0.05, -vy * 0.05, 9, color, 2.0, drag=0.9))

    def star(self, x: float, y: float, color: Color, size: float = 26.0) -> None:
        self._add(Particle("star", x, y, 0, 0, 44, color, size))

    def confetti(self, x: float, y: float, count: int = 1, width: float = 0.0) -> None:
        palette = [(255, 90, 110), (255, 214, 90), (90, 220, 255), (130, 255, 150), (200, 140, 255), (255, 255, 255)]
        for _ in range(count):
            self._add(Particle("confetti", x + self.rng.uniform(-width, width), y, self.rng.uniform(-0.5, 0.5),
                               self.rng.uniform(0.4, 1.4), self.rng.randint(70, 130), self.rng.choice(palette),
                               self.rng.uniform(2.0, 3.2), gravity=0.012, drag=0.995, phase=self.rng.uniform(0, math.tau)))

    # --- simulation ----------------------------------------------------------------------------
    def update(self) -> None:
        alive = []
        for p in self.items:
            p.age += 1
            if p.age >= p.life:
                continue
            p.vy += p.gravity
            p.vx *= p.drag
            p.vy *= p.drag
            p.x += p.vx
            p.y += p.vy
            alive.append(p)
        self.items = alive

    def draw(self, canvas: pygame.Surface) -> None:
        k = self.scale
        for p in self.items:
            t = p.t
            x, y = int(p.x * k), int(p.y * k)
            if p.kind == "dust":
                pygame.draw.circle(canvas, _mix(p.color, (24, 30, 60), t * 0.9), (x, y), max(1, int(p.size * k * (1 + t * 1.4))))
            elif p.kind == "spark":
                tail = (x - p.vx * 2.2 * k, y - p.vy * 2.2 * k)
                pygame.draw.line(canvas, _mix((255, 255, 255), p.color, t * 1.6), (x, y), tail, 2 if t < 0.6 else 1)
            elif p.kind == "square":
                s = max(1, int(p.size * k * (1 - t)))
                pygame.draw.rect(canvas, _mix(p.color, (255, 255, 255), 0.4 * (1 - t)), (x - s // 2, y - s // 2, s, s))
            elif p.kind == "ring":
                r = int(p.size * k * (0.25 + 0.75 * t ** 0.6))
                pygame.draw.ellipse(canvas, _mix(p.color, (30, 40, 90), t), (x - r, y - r // 3, 2 * r, max(2, 2 * r // 3)),
                                    2 if t < 0.6 else 1)
            elif p.kind == "star":
                grow = math.sin(min(1.0, t * 1.6) * math.pi / 2)
                r = p.size * k * grow * (1 - max(0.0, t - 0.55) / 0.45)
                pts = []
                for i in range(16):
                    a = i * math.pi / 8 + t * 0.6
                    rad = r if i % 2 == 0 else r * 0.38
                    pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
                if r > 2:
                    pygame.draw.polygon(canvas, (255, 255, 255), pts)
                    pygame.draw.polygon(canvas, p.color, pts, 3)
                    pygame.draw.circle(canvas, p.color, (x, y), max(1, int(r * 0.3)))
            elif p.kind == "confetti":
                flutter = math.sin(p.age * 0.35 + p.phase)
                w, h = max(1, int(p.size * k * (0.5 + abs(flutter)))), max(1, int(p.size * k * 1.6))
                p.x += flutter * 0.4
                pygame.draw.rect(canvas, p.color, (x, y, w, h))

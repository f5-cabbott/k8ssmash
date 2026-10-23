from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W


@dataclass
class Platform:
    rect: pygame.Rect
    dropthrough: bool = False
    # Optional back-and-forth motion: (axis 'x'|'y', amplitude px, period frames).
    motion: tuple[str, float, int] | None = None
    dx: float = 0.0  # how far the platform moved this frame, used to carry riders
    dy: float = 0.0
    _origin: tuple[int, int] | None = None

    def tick(self, frame: int) -> None:
        if self.motion is None:
            return
        if self._origin is None:
            self._origin = (self.rect.x, self.rect.y)
        axis, amp, period = self.motion
        offset = math.sin(frame * 2 * math.pi / period) * amp
        ox, oy = self._origin
        new = (round(ox + offset), oy) if axis == "x" else (ox, round(oy + offset))
        self.dx, self.dy = new[0] - self.rect.x, new[1] - self.rect.y
        self.rect.topleft = new

    @property
    def top(self) -> int:
        return self.rect.top


@dataclass
class Stage:
    name: str
    platforms: list[Platform]
    spawns: list[tuple[float, float]]
    blast: pygame.Rect = field(
        default_factory=lambda: pygame.Rect(-100, -140, CANVAS_W + 200, CANVAS_H + 240))
    theme: str = "datacenter"

    def tick(self, frame: int) -> None:
        for plat in self.platforms:
            plat.tick(frame)


def datacenter_stage() -> Stage:
    return Stage(
        name="Datacenter",
        platforms=[
            Platform(pygame.Rect(120, 250, 400, 40)),
            Platform(pygame.Rect(170, 185, 120, 8), dropthrough=True),
            Platform(pygame.Rect(350, 185, 120, 8), dropthrough=True),
        ],
        spawns=[(200, 250), (440, 250)],
    )

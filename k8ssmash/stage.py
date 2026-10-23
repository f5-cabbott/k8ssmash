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


def control_plane_stage() -> Stage:
    return Stage(
        name="Control Plane",
        platforms=[
            Platform(pygame.Rect(100, 255, 440, 36)),
            Platform(pygame.Rect(140, 196, 100, 8), dropthrough=True),
            Platform(pygame.Rect(400, 196, 100, 8), dropthrough=True),
            Platform(pygame.Rect(270, 140, 100, 8), dropthrough=True),
        ],
        spawns=[(190, 255), (450, 255)],
        theme="controlplane",
    )


def node_pool_stage() -> Stage:
    return Stage(
        name="Node Pool",
        platforms=[
            Platform(pygame.Rect(50, 255, 200, 34)),
            Platform(pygame.Rect(390, 255, 200, 34)),
            Platform(pygame.Rect(270, 235, 100, 8), dropthrough=True, motion=("y", 22, 300)),
            Platform(pygame.Rect(245, 170, 150, 8), dropthrough=True),
        ],
        spawns=[(150, 255), (490, 255)],
        theme="nodepool",
    )


STAGES = [datacenter_stage, control_plane_stage, node_pool_stage]

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from k8ssmash.config import WORLD_H, WORLD_W


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
        default_factory=lambda: pygame.Rect(-220, -280, WORLD_W + 440, WORLD_H + 400))
    theme: str = "datacenter"

    def tick(self, frame: int) -> None:
        for plat in self.platforms:
            plat.tick(frame)


def datacenter_stage() -> Stage:
    """Server hall: a main floor with three tiers of planks above it, a body's-jump apart."""
    return Stage(
        name="Datacenter",
        platforms=[
            Platform(pygame.Rect(190, 400, 580, 40)),
            Platform(pygame.Rect(215, 330, 150, 8), dropthrough=True),
            Platform(pygame.Rect(595, 330, 150, 8), dropthrough=True),
            Platform(pygame.Rect(385, 260, 190, 8), dropthrough=True, motion=("x", 55, 560)),
            Platform(pygame.Rect(255, 190, 120, 8), dropthrough=True),
            Platform(pygame.Rect(585, 190, 120, 8), dropthrough=True),
        ],
        spawns=[(330, 400), (630, 400)],
    )


def control_plane_stage() -> Stage:
    """Core chamber: a wide floor and a pyramid of planks rising to a single high perch."""
    return Stage(
        name="Control Plane",
        platforms=[
            Platform(pygame.Rect(150, 400, 660, 40)),
            Platform(pygame.Rect(185, 330, 130, 8), dropthrough=True),
            Platform(pygame.Rect(415, 330, 130, 8), dropthrough=True, motion=("x", 40, 600)),
            Platform(pygame.Rect(645, 330, 130, 8), dropthrough=True),
            Platform(pygame.Rect(290, 260, 130, 8), dropthrough=True),
            Platform(pygame.Rect(540, 260, 130, 8), dropthrough=True),
            Platform(pygame.Rect(415, 190, 130, 8), dropthrough=True, motion=("y", 22, 420)),
        ],
        spawns=[(300, 400), (660, 400)],
        theme="controlplane",
    )


def node_pool_stage() -> Stage:
    """Pod bay: two floors split by a gap, a lift between them, and a drifting platform up high."""
    return Stage(
        name="Node Pool",
        platforms=[
            Platform(pygame.Rect(60, 400, 300, 40)),
            Platform(pygame.Rect(600, 400, 300, 40)),
            Platform(pygame.Rect(420, 370, 120, 8), dropthrough=True, motion=("y", 30, 300)),
            Platform(pygame.Rect(140, 330, 120, 8), dropthrough=True),
            Platform(pygame.Rect(700, 330, 120, 8), dropthrough=True),
            Platform(pygame.Rect(330, 260, 300, 8), dropthrough=True),
            Platform(pygame.Rect(420, 190, 120, 8), dropthrough=True, motion=("x", 70, 420)),
        ],
        spawns=[(210, 400), (750, 400)],
        theme="nodepool",
    )


STAGES = [datacenter_stage, control_plane_stage, node_pool_stage]

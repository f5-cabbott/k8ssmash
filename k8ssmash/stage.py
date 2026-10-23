from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W


@dataclass
class Platform:
    rect: pygame.Rect
    dropthrough: bool = False

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

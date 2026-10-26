from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from k8ssmash.config import WORLD_H, WORLD_W


WARN, FADE = 150, 150  # frames a set-piece platform shows as a ghost before it is solid, and dims before it goes


@dataclass
class Platform:
    rect: pygame.Rect
    dropthrough: bool = False
    # Optional back-and-forth motion: (axis 'x'|'y', amplitude px, period frames).
    motion: tuple[str, float, int] | None = None
    # Optional set piece: (period, solid frames, offset). The platform fades in as a ghost (warning), is solid for the
    # solid frames, dims for its last two seconds, then vanishes until the next period.
    schedule: tuple[int, int, int] | None = None
    solid: bool = True
    glow: float = 1.0  # how strongly it is drawn: a ghost while warning, fading as it is about to retract
    dx: float = 0.0  # how far the platform moved this frame, used to carry riders
    dy: float = 0.0
    _origin: tuple[int, int] | None = None

    def tick(self, frame: int) -> None:
        if self.schedule is not None:
            period, on, offset = self.schedule
            cycle = (frame + offset) % period
            self.solid = WARN <= cycle < WARN + on
            if cycle < WARN:  # a steady ghost with a slow breath, so it is clearly "coming"
                self.glow = 0.22 + 0.12 * math.sin(frame * 0.07) + 0.2 * cycle / WARN
            elif cycle < WARN + on:
                left = WARN + on - cycle
                self.glow = 1.0 if left > FADE else 0.5 + 0.5 * left / FADE
            else:
                self.glow = 0.0
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

    @property
    def live(self) -> list[Platform]:
        """The platforms that can be stood on right now (set-piece platforms come and go)."""
        return [p for p in self.platforms if p.solid]


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
            # set piece: a hot-swapped server rack slides into the middle of the hall
            Platform(pygame.Rect(375, 330, 210, 8), dropthrough=True, schedule=(1800, 780, 900)),
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
            # set piece: a leader election hands the crown from one outer perch to the other
            Platform(pygame.Rect(30, 255, 120, 8), dropthrough=True, schedule=(2400, 1000, 700)),
            Platform(pygame.Rect(810, 255, 120, 8), dropthrough=True, schedule=(2400, 1000, 1900)),
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
            # set piece: the scheduler lays a bridge across the gap between the two floors
            Platform(pygame.Rect(360, 400, 240, 40), schedule=(2100, 720, 1100)),
        ],
        spawns=[(210, 400), (750, 400)],
        theme="nodepool",
    )


def etcd_stage() -> Stage:
    """Crystal vault: a wide floor, two side ledges and a throne above; the high platforms appear one after another, like a vote."""
    return Stage(
        name="Etcd Vault",
        platforms=[
            Platform(pygame.Rect(200, 410, 560, 38)),
            Platform(pygame.Rect(70, 338, 130, 8), dropthrough=True),
            Platform(pygame.Rect(760, 338, 130, 8), dropthrough=True),
            Platform(pygame.Rect(390, 300, 180, 8), dropthrough=True, motion=("x", 45, 640)),
            Platform(pygame.Rect(280, 225, 110, 8), dropthrough=True),
            Platform(pygame.Rect(570, 225, 110, 8), dropthrough=True),
            # set piece: consensus. Three perches take turns appearing across the top, left to right
            Platform(pygame.Rect(120, 170, 100, 8), dropthrough=True, schedule=(2250, 800, 0)),
            Platform(pygame.Rect(430, 140, 100, 8), dropthrough=True, schedule=(2250, 800, 750)),
            Platform(pygame.Rect(740, 170, 100, 8), dropthrough=True, schedule=(2250, 800, 1500)),
        ],
        spawns=[(330, 410), (630, 410)],
        theme="etcd",
    )


def mesh_stage() -> Stage:
    """Floating islands: two drifting landmasses, a bridge-high span and a perch that comes and goes."""
    return Stage(
        name="Service Mesh",
        platforms=[
            Platform(pygame.Rect(130, 410, 300, 36), motion=("x", 28, 780)),
            Platform(pygame.Rect(530, 410, 300, 36), motion=("x", -28, 780)),
            Platform(pygame.Rect(345, 330, 270, 8), dropthrough=True, motion=("y", 22, 540)),
            Platform(pygame.Rect(110, 270, 130, 8), dropthrough=True),
            Platform(pygame.Rect(720, 270, 130, 8), dropthrough=True),
            Platform(pygame.Rect(430, 215, 100, 8), dropthrough=True),
            # set piece: an extra node joins the mesh up high, then drains away
            Platform(pygame.Rect(400, 130, 160, 8), dropthrough=True, schedule=(2100, 750, 600)),
        ],
        spawns=[(280, 410), (680, 410)],
        theme="mesh",
    )


def cloud_stage() -> Stage:
    """Cloud Native: a big cloud with bobbing side clouds and a drifting top cloud; autoscaling spins replicas up in pairs."""
    return Stage(
        name="Cloud Native",
        platforms=[
            Platform(pygame.Rect(250, 410, 460, 40)),
            Platform(pygame.Rect(90, 360, 130, 10), dropthrough=True, motion=("y", 20, 540)),
            Platform(pygame.Rect(740, 360, 130, 10), dropthrough=True, motion=("y", -20, 540)),
            Platform(pygame.Rect(375, 295, 210, 10), dropthrough=True, motion=("x", 70, 820)),
            Platform(pygame.Rect(430, 190, 100, 10), dropthrough=True),
            # set piece: autoscaling. Replica clouds spin up in pairs (low pair, then high pair), then scale back in
            Platform(pygame.Rect(110, 260, 110, 10), dropthrough=True, schedule=(2400, 760, 0)),
            Platform(pygame.Rect(740, 260, 110, 10), dropthrough=True, schedule=(2400, 760, 0)),
            Platform(pygame.Rect(210, 170, 110, 10), dropthrough=True, schedule=(2400, 760, 1200)),
            Platform(pygame.Rect(640, 170, 110, 10), dropthrough=True, schedule=(2400, 760, 1200)),
        ],
        spawns=[(340, 410), (620, 410)],
        theme="cloud",
    )


STAGES = [datacenter_stage, control_plane_stage, node_pool_stage, etcd_stage, mesh_stage, cloud_stage]

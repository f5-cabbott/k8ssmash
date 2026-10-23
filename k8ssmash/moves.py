"""Frame-based move data. All distances are canvas pixels, all durations are 60 fps frames."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProjectileDef:
    speed: float
    width: int
    height: int
    damage: float
    base_kb: float
    kb_growth: float
    angle: float
    life: int = 90
    gravity: float = 0.0
    spawn_dx: float = 14  # forward offset from fighter centre
    spawn_dy: float = -22  # offset from feet
    color: tuple[int, int, int] = (120, 200, 255)


@dataclass(frozen=True)
class Move:
    name: str
    startup: int
    active: int
    recovery: int
    # Hitbox relative to fighter: ox = forward offset of the box's near edge from centre,
    # oy = box top relative to feet (negative = above feet).
    hitbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    damage: float = 0.0
    base_kb: float = 0.0
    kb_growth: float = 0.0
    angle: float = 45.0  # degrees; 0 = straight forward, 90 = straight up
    lunge: float = 0.0  # forward speed applied on the first active frame
    rise: float = 0.0  # upward speed applied on the first active frame
    projectile: ProjectileDef | None = None
    sfx: str = ""
    extra: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def total(self) -> int:
        return self.startup + self.active + self.recovery


def default_moveset() -> dict[str, Move]:
    return {
        "jab": Move("jab", 3, 3, 9, (6, -30, 22, 14), 3, 2.2, 0.018, 35),
        "side": Move("side", 8, 4, 16, (6, -34, 30, 18), 9, 3.6, 0.055, 32, lunge=1.5),
        "up": Move("up", 6, 5, 15, (-12, -66, 26, 30), 7, 3.2, 0.050, 85),
        "down": Move("down", 5, 4, 14, (4, -14, 32, 14), 6, 2.8, 0.040, 22),
        "special": Move(
            "apply", 10, 1, 18, damage=0, projectile=ProjectileDef(
                speed=4.5, width=10, height=8, damage=5, base_kb=2.6, kb_growth=0.03, angle=30),
        ),
    }

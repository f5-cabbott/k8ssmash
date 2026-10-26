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
    vy: float = 0.0  # initial vertical speed (negative = up), for lobbed shots
    spawn_dx: float = 14  # forward offset from fighter centre
    spawn_dy: float = -30  # offset from feet (chest height: a duck passes underneath)
    color: tuple[int, int, int] = (120, 200, 255)
    shape: str = "orb"  # sprite flavour: orb, bolt, wheel, clock, bomb, drone, wall, skull, drum, ring, bubble, spark, well, bird
    count: int = 1
    spread: float = 0.0  # total fan angle in degrees when count > 1
    boomerang: bool = False  # reverses at half life and returns to the owner
    pierce: bool = False  # survives hits; each target is hit once per hit_interval
    hit_interval: int = 0  # frames before the same target can be hit again (0 = once only)
    orbit: bool = False  # circles its owner instead of flying off
    stick: bool = False  # stops dead on the first platform it lands on
    explode_radius: int = 0  # detonates at end of life, hitting everyone in range
    explode_damage: float = 0.0
    harmless_to_owner: bool = True
    replace_existing: bool = False  # a new copy removes the owner's previous one (drones, walls)
    pull: float = 0.0  # a gravity well: opponents inside pull_radius are drawn toward it by this much speed per frame
    pull_radius: int = 0
    wave: float = 0.0  # sways up and down as it flies (bubbles, sparks); the amount is pixels per frame


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
    dash: float = 0.0  # forward speed held through the active frames
    blink: float = 0.0  # instant forward teleport on the first active frame; intangible while active
    counter: bool = False  # active frames counter incoming hits; damage/kb describe the retaliation
    heal: float = 0.0  # percent removed on the first active frame
    buff: tuple[str, int] | None = None  # (buff name, frames) applied on the first active frame
    once_per_air: bool = False  # recovery moves: usable once until the fighter lands
    grab: bool = False  # connects through shields; the direction held when it lands picks the throw
    rehit: int = 0  # >0: a multi-hit move; the same target can be hit again every this many frames while it is active
    projectile: ProjectileDef | None = None
    anim: str = ""  # sprite animation style; falls back to the move key
    announce: str = ""  # k8s-flavoured callout shown when the move is used
    extra: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def total(self) -> int:
        return self.startup + self.active + self.recovery


def default_moveset() -> dict[str, Move]:
    """Shared normals. Characters override whatever they want to feel different."""
    return {
        "jab": Move("jab", 3, 3, 9, (6, -32, 22, 14), 3, 2.2, 0.018, 35, anim="jab"),
        "side": Move("side", 8, 4, 16, (6, -36, 30, 18), 9, 3.6, 0.055, 32, lunge=1.5, anim="side"),
        "up": Move("up", 6, 5, 15, (-12, -70, 26, 30), 7, 3.2, 0.050, 85, anim="up"),
        "down": Move("down", 5, 4, 14, (4, -14, 32, 14), 6, 2.8, 0.040, 22, anim="down"),
        "grab": Move("grab", 6, 3, 24, (2, -34, 26, 24), anim="jab", announce="kubectl drain", grab=True),
        "special": Move(
            "apply", 10, 1, 18, projectile=ProjectileDef(
                speed=4.5, width=10, height=8, damage=5, base_kb=2.6, kb_growth=0.03, angle=30),
            anim="cast", announce="kubectl apply"),
    }

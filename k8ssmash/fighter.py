"""Fighter physics and attack state machine. Pure logic: no drawing, no pygame display needed."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from k8ssmash.input import PlayerInput
from k8ssmash.moves import Move, ProjectileDef, default_moveset
from k8ssmash.stage import Stage

GROUND_FRICTION = 0.6
SHIELD_MAX = 60.0
KO_DELAY = 50
RESPAWN_INVULN = 120


@dataclass
class FighterStats:
    name: str
    color: tuple[int, int, int]
    width: int = 22
    height: int = 40
    run_speed: float = 2.6
    air_speed: float = 2.3
    air_accel: float = 0.22
    jump_vel: float = -7.6
    djump_vel: float = -7.0
    gravity: float = 0.38
    max_fall: float = 7.5
    fast_fall: float = 11.0
    weight: float = 100.0
    moves: dict[str, Move] = field(default_factory=default_moveset)


@dataclass
class Projectile:
    owner: "Fighter"
    defn: ProjectileDef
    x: float
    y: float
    vx: float
    vy: float
    facing: int
    life: int

    @property
    def rect(self) -> pygame.Rect:
        d = self.defn
        return pygame.Rect(int(self.x - d.width / 2), int(self.y - d.height / 2), d.width, d.height)

    def update(self) -> None:
        self.vy += self.defn.gravity
        self.x += self.vx
        self.y += self.vy
        self.life -= 1


class Fighter:
    def __init__(self, stats: FighterStats, slot: int, stocks: int = 3):
        self.stats = stats
        self.slot = slot
        self.stocks = stocks
        self.percent = 0.0
        self.x = self.y = 0.0  # y is the feet
        self.vx = self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.aerial_jumps = 1
        self.drop_timer = 0
        self.invuln = 0
        self.hitstun = 0
        self.ko_timer = 0
        self.eliminated = False
        self.shield_hp = SHIELD_MAX
        self.shield_break = 0
        self.shielding = False
        self.move: Move | None = None
        self.move_frame = 0
        self.hit_targets: set[int] = set()
        self.spawn_queue: list[Projectile] = []
        self.kos = 0
        self.last_hit_by: Fighter | None = None
        self.dealt_damage = 0.0
        self.state = "idle"
        self.spawn_point = (0.0, 0.0)

    # --- geometry ------------------------------------------------------------------------
    @property
    def hurtbox(self) -> pygame.Rect:
        s = self.stats
        return pygame.Rect(int(self.x - s.width / 2), int(self.y - s.height), s.width, s.height)

    @property
    def alive(self) -> bool:
        return self.ko_timer == 0 and not self.eliminated

    def active_hitbox(self) -> pygame.Rect | None:
        m = self.move
        if m is None or m.projectile is not None or m.hitbox[2] == 0:
            return None
        if not (m.startup <= self.move_frame < m.startup + m.active):
            return None
        ox, oy, w, h = m.hitbox
        left = self.x + ox if self.facing > 0 else self.x - ox - w
        return pygame.Rect(int(left), int(self.y + oy), w, h)

    # --- lifecycle -----------------------------------------------------------------------
    def spawn(self, point: tuple[float, float], facing: int, invuln: int = 0) -> None:
        self.spawn_point = point
        self.x, self.y = point
        self.vx = self.vy = 0.0
        self.facing = facing
        self.percent = 0.0 if invuln else self.percent
        self.invuln = invuln
        self.hitstun = 0
        self.move = None
        self.shield_hp = SHIELD_MAX
        self.shield_break = 0
        self.aerial_jumps = 1
        self.on_ground = False

    def knock_out(self) -> None:
        self.stocks -= 1
        self.ko_timer = KO_DELAY
        self.move = None
        self.vx = self.vy = 0.0
        if self.stocks <= 0:
            self.eliminated = True

    # --- combat --------------------------------------------------------------------------
    def apply_hit(self, damage: float, base_kb: float, growth: float, angle: float, direction: int) -> str:
        """Returns 'hit', 'shield' or 'ignored'."""
        if self.invuln > 0 or not self.alive:
            return "ignored"
        if self.shielding:
            self.shield_hp -= damage * 2.0
            self.vx += direction * 0.8
            if self.shield_hp <= 0:
                self.shield_break = 90
                self.hitstun = 90
                self.shielding = False
                self.vy = -5.0
            return "shield"
        self.percent += damage
        speed = (base_kb + self.percent * growth) * (100.0 / self.stats.weight)
        rad = math.radians(angle)
        self.vx = math.cos(rad) * speed * direction
        self.vy = -math.sin(rad) * speed
        self.hitstun = int(speed * 3.5) + 4
        self.move = None
        self.shielding = False
        if self.vy < -0.1:
            self.on_ground = False
        return "hit"

    # --- per-frame update ----------------------------------------------------------------
    def update(self, inp: PlayerInput, stage: Stage) -> None:
        if self.eliminated:
            return
        if self.ko_timer > 0:
            self.ko_timer -= 1
            if self.ko_timer == 0:
                self.spawn(stage.spawns[self.slot % len(stage.spawns)], 1 if self.slot == 0 else -1,
                           RESPAWN_INVULN)
                self.percent = 0.0
            return
        for name in ("invuln", "hitstun", "drop_timer", "shield_break"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)

        s = self.stats
        stunned = self.hitstun > 0
        self.shielding = False

        if stunned:
            self.state = "hurt"
        elif self.move is not None:
            self._advance_move(inp)
        else:
            self._control(inp)

        # gravity
        if not self.on_ground:
            fast = inp.axis_y > 0 and self.vy > 0 and not stunned and self.move is None
            self.vy = min(self.vy + s.gravity, s.fast_fall if fast else s.max_fall)
        self._move_and_collide(stage)

        if self.on_ground:
            self.aerial_jumps = 1
        elif self.state in ("idle", "run", "shield"):
            self.state = "fall" if self.vy > 0 else "jump"

        if self.shield_hp < SHIELD_MAX and not self.shielding:
            self.shield_hp = min(SHIELD_MAX, self.shield_hp + 0.25)

    def _control(self, inp: PlayerInput) -> None:
        s = self.stats
        ax = inp.axis_x

        if self.on_ground and "SHIELD" in inp and self.shield_break == 0:
            self.shielding = True
            self.vx = 0.0
            self.state = "shield"
            return

        if "ATTACK" in inp.pressed:
            self._start_attack(inp)
            if self.move is not None:
                return
        elif "SPECIAL" in inp.pressed:
            self._start_special(inp)
            if self.move is not None:
                return

        if "JUMP" in inp.pressed:
            if self.on_ground:
                self.vy = s.jump_vel
                self.on_ground = False
                self.state = "jump"
            elif self.aerial_jumps > 0:
                self.aerial_jumps -= 1
                self.vy = s.djump_vel
                self.vx *= 0.5
                self.state = "jump"
        if "DOWN" in inp and self.on_ground:
            self.drop_timer = 10

        if ax:
            self.facing = ax
        if self.on_ground:
            if ax:
                self.vx = ax * s.run_speed
                self.state = "run"
            else:
                self.vx = _approach(self.vx, 0.0, GROUND_FRICTION)
                self.state = "idle"
        else:
            if ax:
                self.vx = max(-s.air_speed, min(s.air_speed, self.vx + ax * s.air_accel))
            else:
                self.vx = _approach(self.vx, 0.0, 0.04)

    def _pick(self, key: str) -> Move | None:
        moves = self.stats.moves
        return moves.get(key) or moves.get(key.split("_")[0])

    def _start_attack(self, inp: PlayerInput) -> None:
        if inp.axis_y < 0:
            key = "up"
        elif inp.axis_y > 0:
            key = "down"
        elif inp.axis_x:
            key = "side"
            self.facing = inp.axis_x
        else:
            key = "jab"
        self._begin(self._pick(key))

    def _start_special(self, inp: PlayerInput) -> None:
        if inp.axis_y < 0:
            key = "special_up"
        elif inp.axis_y > 0:
            key = "special_down"
        elif inp.axis_x:
            key = "special_side"
            self.facing = inp.axis_x
        else:
            key = "special"
        self._begin(self._pick(key))

    def _begin(self, move: Move | None) -> None:
        if move is None:
            return
        self.move = move
        self.move_frame = 0
        self.hit_targets = set()
        self.state = "attack"

    def _advance_move(self, inp: PlayerInput) -> None:
        m = self.move
        assert m is not None
        if self.move_frame == m.startup:
            if m.lunge:
                self.vx = self.facing * m.lunge
            if m.rise:
                self.vy = -m.rise
                self.on_ground = False
            if m.projectile is not None:
                self._fire(m.projectile)
        if self.on_ground:
            self.vx = _approach(self.vx, 0.0, GROUND_FRICTION * 0.5)
        else:
            self.vx = _approach(self.vx, 0.0, 0.02)
        self.move_frame += 1
        if self.move_frame >= m.total:
            self.move = None
            self.state = "idle"

    def _fire(self, d: ProjectileDef) -> None:
        self.spawn_queue.append(Projectile(
            owner=self, defn=d,
            x=self.x + self.facing * d.spawn_dx, y=self.y + d.spawn_dy,
            vx=self.facing * d.speed, vy=0.0, facing=self.facing, life=d.life))

    # --- movement ------------------------------------------------------------------------
    def _move_and_collide(self, stage: Stage) -> None:
        self.x += self.vx
        prev_y = self.y
        self.y += self.vy
        self.on_ground = False
        if self.vy < 0:
            return
        half = self.stats.width / 2
        for plat in stage.platforms:
            if plat.dropthrough and self.drop_timer > 0:
                continue
            r = plat.rect
            if self.x + half > r.left and self.x - half < r.right and prev_y <= r.top + 0.01 <= self.y + 0.01:
                self.y = float(r.top)
                self.vy = 0.0
                self.on_ground = True
                break


def _approach(value: float, target: float, step: float) -> float:
    if value < target:
        return min(value + step, target)
    return max(value - step, target)

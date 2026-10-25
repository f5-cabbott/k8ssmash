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
CALLOUT_FRAMES = 50
DUCK_HEIGHT = 0.55
LEDGE_REACH = 30  # how far below a platform's top you can be and still be pulled up onto it
LEDGE_GRAB = 12  # how far out from the edge counts as 'at the ledge'
BUFFER = 6  # frames a button press is remembered, so mashing a hair early still counts
COYOTE = 5  # frames after walking off an edge in which you can still make a ground jump
HANG_MAX = 170  # frames you can hold a ledge before you drop

# Buff names -> what they do. Durations are in frames and live in Fighter.buffs.
BUFF_HASTE = "haste"  # +35% move speed
BUFF_POWER = "power"  # +30% damage dealt
BUFF_SCALED = "scaled"  # drawn larger (HPA scale-up)
BUFF_GUARD = "guard"  # half damage taken
BUFF_ARMOR = "armor"  # hits don't flinch or launch


@dataclass
class FighterStats:
    name: str
    color: tuple[int, int, int]
    width: int = 24
    height: int = 46
    run_speed: float = 3.4
    air_speed: float = 3.0
    air_accel: float = 0.3
    jump_vel: float = -9.0
    djump_ratio: float = 0.65  # the double jump reaches this fraction of the first jump's height
    air_jumps: int = 3  # extra mid-air jumps (Kirby-style recovery); each is a little weaker than the one before
    glide_fall: float = 3.4  # holding JUMP while falling floats down at this speed instead of plunging
    air_drive: float = 1.7  # how hard a mid-air jump pushes you sideways toward the stage
    gravity: float = 0.38
    max_fall: float = 8.6
    fast_fall: float = 12.5
    weight: float = 100.0
    blurb: str = ""
    moves: dict[str, Move] = field(default_factory=default_moveset)

    @property
    def djump_vel(self) -> float:
        """Height goes with velocity squared, so a 65%-height second jump needs sqrt(0.65) of the launch speed."""
        return self.jump_vel * math.sqrt(self.djump_ratio)


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
    age: int = 0
    orbit_angle: float = 0.0
    stuck: bool = False
    hit_at: dict[int, int] = field(default_factory=dict)  # victim slot -> frame it may be hit again

    @property
    def rect(self) -> pygame.Rect:
        d = self.defn
        return pygame.Rect(int(self.x - d.width / 2), int(self.y - d.height / 2), d.width, d.height)

    def can_hit(self, slot: int) -> bool:
        return self.age >= self.hit_at.get(slot, 0)

    def mark_hit(self, slot: int) -> None:
        self.hit_at[slot] = self.age + (self.defn.hit_interval or 10**9)

    def update(self, stage: Stage) -> None:
        d = self.defn
        self.age += 1
        if d.orbit:
            self.orbit_angle += 0.11
            o = self.owner
            self.x = o.x + math.cos(self.orbit_angle) * 30
            self.y = o.y - 26 + math.sin(self.orbit_angle) * 12
        elif d.boomerang and self.age > d.life // 2:
            o = self.owner
            dx, dy = o.x - self.x, (o.y - 24) - self.y
            dist = math.hypot(dx, dy) or 1.0
            self.vx, self.vy = dx / dist * d.speed * 1.1, dy / dist * d.speed * 1.1
            self.x += self.vx
            self.y += self.vy
            if dist < 12:
                self.life = 0
        elif not self.stuck:
            prev = self.y
            self.vy += d.gravity
            self.x += self.vx
            self.y += self.vy
            if d.stick and self.vy >= 0:
                for plat in stage.platforms:
                    r = plat.rect
                    if r.left <= self.x <= r.right and prev <= r.top <= self.y:
                        self.y, self.vx, self.vy, self.stuck = float(r.top - d.height / 2), 0.0, 0.0, True
                        break
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
        self.standing_on = None  # the Platform underfoot, so moving platforms can carry us
        self.aerial_jumps = self.stats.air_jumps
        self.used_recovery = False
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
        self.events: list[str] = []  # sound cues for the battle scene to play
        self.fx: list[tuple[str, float]] = []  # visual cues (landing dust, jump rings) for the battle scene
        self.land_timer = 0  # frames of landing squash remaining
        self.buffs: dict[str, int] = {}
        self.comeback = False  # last-stock second wind, set by the battle
        self.last_axis = (0, 0)  # the stick on the latest frame: a grab reads it to choose the throw
        self.hanging: tuple | None = None  # (platform, inward) while holding a ledge
        self.hang_timer = 0
        self.regrab_timer = 0
        self.buf = {"ATTACK": 0, "SPECIAL": 0, "JUMP": 0}  # input buffer: frames each press is still live
        self.coyote = 0
        self.kos = 0
        self.dealt_damage = 0.0
        self.last_hit_by: Fighter | None = None
        self.state = "idle"
        self.spawn_point = (0.0, 0.0)
        self.callout = ""
        self.callout_timer = 0
        self.anim_frame = 0  # frames spent in the current state, for sprite animation
        self._anim_state = "idle"

    # --- derived stats ---------------------------------------------------------------------
    def has(self, buff: str) -> bool:
        return self.buffs.get(buff, 0) > 0

    @property
    def speed_mult(self) -> float:
        return (1.35 if self.has(BUFF_HASTE) else 1.0) * (1.06 if self.comeback else 1.0)

    @property
    def damage_mult(self) -> float:
        return (1.3 if self.has(BUFF_POWER) else 1.0) * (1.15 if self.comeback else 1.0)

    @property
    def taken_mult(self) -> float:
        return 0.5 if self.has(BUFF_GUARD) else 1.0

    @property
    def armored(self) -> bool:
        return self.has(BUFF_ARMOR)

    @property
    def scale(self) -> float:
        return 1.2 if self.has(BUFF_SCALED) else 1.0

    def add_buff(self, name: str, frames: int) -> None:
        self.buffs[name] = max(self.buffs.get(name, 0), frames)

    def say(self, text: str) -> None:
        self.callout, self.callout_timer = text, CALLOUT_FRAMES

    # --- geometry --------------------------------------------------------------------------
    @property
    def hurtbox(self) -> pygame.Rect:
        s = self.stats
        w, h = int(s.width * self.scale), int(s.height * self.scale)
        if self.ducking:
            h = int(h * DUCK_HEIGHT)
        return pygame.Rect(int(self.x - w / 2), int(self.y - h), w, h)

    @property
    def ducking(self) -> bool:
        """Crouching (or in a low attack): a shorter hurtbox that high attacks and shots pass over."""
        return self.state == "duck" or (self.move is not None and self.move.anim == "down")

    @property
    def alive(self) -> bool:
        return self.ko_timer == 0 and not self.eliminated

    def _in_active_window(self) -> bool:
        m = self.move
        return m is not None and m.startup <= self.move_frame < m.startup + m.active

    @property
    def countering(self) -> bool:
        return self.move is not None and self.move.counter and self._in_active_window()

    @property
    def intangible(self) -> bool:
        return self.move is not None and self.move.blink != 0 and self._in_active_window()

    def active_hitbox(self) -> pygame.Rect | None:
        m = self.move
        if m is None or m.hitbox[2] == 0 or m.counter or not self._in_active_window():
            return None
        ox, oy, w, h = m.hitbox
        s = self.scale
        ox, oy, w, h = ox * s, oy * s, w * s, h * s
        left = self.x + ox if self.facing > 0 else self.x - ox - w
        return pygame.Rect(int(left), int(self.y + oy), int(w), int(h))

    # --- lifecycle -------------------------------------------------------------------------
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
        self.aerial_jumps = self.stats.air_jumps
        self.used_recovery = False
        self.on_ground = False
        self.standing_on = None
        self.hanging = None
        self.coyote = 0
        self.buf = dict.fromkeys(self.buf, 0)
        self.buffs.clear()

    def knock_out(self) -> None:
        self.stocks -= 1
        self.ko_timer = KO_DELAY
        self.move = None
        self.hanging = None
        self.vx = self.vy = 0.0
        self.buffs.clear()
        if self.stocks <= 0:
            self.eliminated = True

    # --- combat ----------------------------------------------------------------------------
    def apply_hit(self, damage: float, base_kb: float, growth: float, angle: float, direction: int) -> str:
        """Returns 'hit', 'shield' or 'ignored'."""
        if self.invuln > 0 or self.intangible or not self.alive:
            return "ignored"
        if self.shielding:
            self.shield_hp -= damage * 2.0
            self.vx += direction * 0.8
            if self.shield_hp <= 0:
                self.shield_break = 90
                self.hitstun = 90
                self.shielding = False
                self.vy = -5.0
                self.events.append("shield_break")
            return "shield"
        self.hanging = None
        self.percent += damage * self.taken_mult
        if self.armored:
            return "hit"  # damage lands, but no flinch or launch
        speed = (base_kb + self.percent * growth) * (100.0 / self.stats.weight)
        rad = math.radians(angle)
        self.vx = math.cos(rad) * speed * direction
        self.vy = -math.sin(rad) * speed
        self.hitstun = int(speed * 3.5) + 4
        self.move = None
        self.shielding = False
        if self.vy < -0.1:
            self.on_ground = False
            self.standing_on = None
        return "hit"

    # --- per-frame update ------------------------------------------------------------------
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
        self.last_axis = (inp.axis_x, inp.axis_y)
        for name in self.buf:
            self.buf[name] = BUFFER if name in inp.pressed else max(0, self.buf[name] - 1)
        for name in ("invuln", "hitstun", "drop_timer", "shield_break", "callout_timer", "land_timer", "regrab_timer"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)
        for name in list(self.buffs):
            self.buffs[name] -= 1
            if self.buffs[name] <= 0:
                del self.buffs[name]

        s = self.stats
        stunned = self.hitstun > 0
        self.shielding = False

        if self.hanging is not None and not stunned and self.move is None:
            self._hang(inp)
            self._finish_frame()
            return
        if stunned:
            self.state = "hurt"
        elif self.move is not None:
            self._advance_move(inp)
        else:
            self._control(inp)

        # carry along with a moving platform
        if self.on_ground and self.standing_on is not None:
            self.x += self.standing_on.dx
            self.y += self.standing_on.dy

        if not self.on_ground:
            fast = inp.axis_y > 0 and self.vy > 0 and not stunned and self.move is None
            glide = "JUMP" in inp and self.vy > 0 and not fast and self.move is None
            self.vy = min(self.vy + s.gravity, s.fast_fall if fast else (s.glide_fall if glide else s.max_fall))
        was_airborne, impact = not self.on_ground, self.vy
        self._move_and_collide(stage)
        if not stunned:
            self._ledge_assist(stage, inp)
        if self.on_ground and was_airborne and impact > 2.0:  # touchdown: squash and kick up dust
            self.land_timer = 6 if impact > 4.5 else 4
            self.fx.append(("land", min(1.0, impact / 8.0)))

        self.coyote = COYOTE if self.on_ground else max(0, self.coyote - 1)
        if self.on_ground:
            self.aerial_jumps = self.stats.air_jumps
            self.used_recovery = False
        elif self.state in ("idle", "run", "shield", "duck"):
            self.state = "fall" if self.vy > 0 else "jump"

        if self.shield_hp < SHIELD_MAX and not self.shielding:
            self.shield_hp = min(SHIELD_MAX, self.shield_hp + 0.25)

        self._finish_frame()

    def _finish_frame(self) -> None:
        key = self.move.anim if self.move is not None and self.state == "attack" else self.state
        self.anim_frame = self.anim_frame + 1 if key == self._anim_state else 0
        self._anim_state = key

    def _hang(self, inp: PlayerInput) -> None:
        """Holding a ledge: safe for a moment, then climb (up, jump or toward the stage), or let go (down)."""
        plat, inward = self.hanging
        self.vx = self.vy = 0.0
        self.state = "jump"
        self.hang_timer -= 1
        held_for = HANG_MAX - self.hang_timer
        half = self.stats.width * self.scale / 2
        if held_for > 8 and (inp.pressed & {"UP", "JUMP"} or inp.axis_x == inward and held_for > 14):
            r = plat.rect
            self.x = (r.left if inward > 0 else r.right) + inward * half * 0.5
            self.y = float(r.top)
            self.on_ground, self.standing_on, self.hanging = True, plat, None
            self.facing = inward
            self.events.append("land")
            self.fx.append(("land", 0.6))
        elif "DOWN" in inp.pressed or self.hang_timer <= 0:
            self.hanging, self.regrab_timer = None, 30

    def _control(self, inp: PlayerInput) -> None:
        s = self.stats
        ax = inp.axis_x
        run = s.run_speed * self.speed_mult
        air = s.air_speed * self.speed_mult

        if self.on_ground and "SHIELD" in inp and self.shield_break == 0:
            if "ATTACK" in inp.pressed:  # shield + attack: grab
                self._begin(self._pick("grab"))
                if self.move is not None:
                    return
            self.shielding = True
            self.vx = 0.0
            self.state = "shield"
            return

        if self.buf["ATTACK"]:
            self._start_attack(inp)
            self.buf["ATTACK"] = 0  # the press is spent whether or not the move was allowed
            if self.move is not None:
                return
        elif self.buf["SPECIAL"]:
            self._start_special(inp)
            self.buf["SPECIAL"] = 0
            if self.move is not None:
                return

        if self.buf["JUMP"]:
            if self.on_ground or self.coyote > 0:
                self.buf["JUMP"] = self.coyote = 0
                self.vy = s.jump_vel
                self.on_ground = False
                self.standing_on = None
                self.state = "jump"
                self.events.append("jump")
                self.fx.append(("jump", 0.5))
            elif self.aerial_jumps > 0:
                self.buf["JUMP"] = 0
                used = s.air_jumps - self.aerial_jumps
                self.aerial_jumps -= 1
                self.vy = s.djump_vel * (0.93 ** used)
                # steer the jump: pushing a direction launches you that way, which is what gets you back to the stage
                self.vx = ax * air * s.air_drive if ax else self.vx * 0.5
                self.state = "djump"
                self.events.append("djump")
                self.fx.append(("djump", 1.0))
        if "DOWN" in inp.pressed and self.on_ground and self.standing_on is not None \
                and self.standing_on.dropthrough:
            self.drop_timer = 10  # a tap drops through a thin platform; holding just ducks

        if self.on_ground and "DOWN" in inp and self.drop_timer == 0:
            if ax:
                self.facing = ax
            self.vx = _approach(self.vx, 0.0, GROUND_FRICTION)
            self.state = "duck"
            return

        if ax:
            self.facing = ax
        if self.on_ground:
            if ax:
                self.vx = ax * run
                self.state = "run"
            else:
                self.vx = _approach(self.vx, 0.0, GROUND_FRICTION)
                self.state = "idle"
        else:
            if ax:
                self.vx = max(-air, min(air, self.vx + ax * s.air_accel))
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
        self._begin(self._pick(key), special=True)

    def _begin(self, move: Move | None, special: bool = False) -> None:
        if move is None:
            return
        if move.once_per_air and not self.on_ground:
            if self.used_recovery:
                return
            self.used_recovery = True
        self.move = move
        self.move_frame = 0
        self.hit_targets = set()
        self.state = "attack"
        if move.announce:
            self.say(move.announce)
        # a swing and a shout: light normals grunt, heavy ones bark, specials yell
        self.events.append("special" if special else ("attack_heavy" if move.damage >= 8 else "attack_light"))

    def _advance_move(self, inp: PlayerInput) -> None:
        m = self.move
        assert m is not None
        if self.move_frame == m.startup:
            if m.lunge:
                self.vx = self.facing * m.lunge
            if m.rise:
                self.vy = -m.rise
                self.on_ground = False
                self.standing_on = None
            if m.blink:
                self.x += self.facing * m.blink
            if m.heal:
                self.percent = max(0.0, self.percent - m.heal)
            if m.buff:
                self.add_buff(*m.buff)
            if m.projectile is not None:
                self._fire(m.projectile)
        if m.dash and self._in_active_window():
            self.vx = self.facing * m.dash
        elif self.on_ground:
            self.vx = _approach(self.vx, 0.0, GROUND_FRICTION * 0.5)
        else:
            self.vx = _approach(self.vx, 0.0, 0.02)
        self.move_frame += 1
        if self.move_frame >= m.total:
            self.move = None
            self.state = "idle"

    def _fire(self, d: ProjectileDef) -> None:
        for i in range(d.count):
            a = 0.0 if d.count == 1 else math.radians((i / (d.count - 1) - 0.5) * d.spread)
            self.spawn_queue.append(Projectile(
                owner=self, defn=d,
                x=self.x + self.facing * d.spawn_dx, y=self.y + d.spawn_dy,
                vx=math.cos(a) * d.speed * self.facing, vy=math.sin(a) * d.speed + d.vy,
                facing=self.facing, life=d.life, orbit_angle=self.slot * math.pi))

    def _ledge_assist(self, stage: Stage, inp: PlayerInput) -> None:
        """Smash-style ledge grab: fall beside a solid platform's edge, push toward it (or up), and you catch hold and
        hang there, briefly invincible. Thin planks are left alone."""
        if self.on_ground or self.move is not None or self.vy < -3.0 or self.regrab_timer > 0 or self.hanging is not None:
            return
        half = self.stats.width * self.scale / 2
        for plat in stage.platforms:
            if plat.dropthrough:
                continue
            r = plat.rect
            if not (0 < self.y - r.top <= LEDGE_REACH):
                continue
            for edge, inward in ((r.left, 1), (r.right, -1)):  # inward: the direction that points onto the platform
                gap = (edge - self.x) * inward  # positive while still outside the edge
                if -half * 0.5 <= gap <= half + LEDGE_GRAB and (inp.axis_x == inward or "UP" in inp):
                    self.x = edge - inward * half * 0.6
                    self.y = float(r.top + 30)
                    self.vx = self.vy = 0.0
                    self.hanging, self.hang_timer = (plat, inward), HANG_MAX
                    self.facing = inward
                    self.invuln = max(self.invuln, 45)
                    self.aerial_jumps = self.stats.air_jumps
                    self.events.append("shield")
                    return

    # --- movement --------------------------------------------------------------------------
    def _move_and_collide(self, stage: Stage) -> None:
        self.x += self.vx
        prev_y = self.y
        self.y += self.vy
        self.on_ground = False
        self.standing_on = None
        if self.vy < 0:
            return
        half = self.stats.width * self.scale / 2
        for plat in stage.platforms:
            if plat.dropthrough and self.drop_timer > 0:
                continue
            r = plat.rect
            # prev_y is compared against the platform's previous top so riders on moving platforms land.
            top_before = r.top - plat.dy
            if (self.x + half > r.left and self.x - half < r.right
                    and prev_y <= top_before + 0.01 and r.top - 0.01 <= self.y + 0.01):
                self.y = float(r.top)
                self.vy = 0.0
                self.on_ground = True
                self.standing_on = plat
                break


def _approach(value: float, target: float, step: float) -> float:
    if value < target:
        return min(value + step, target)
    return max(value - step, target)

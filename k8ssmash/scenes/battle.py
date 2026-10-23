from __future__ import annotations

import math

import pygame

from k8ssmash.ai import SimpleAI
from k8ssmash.audio_manager import MUSIC_FOR_THEME
from k8ssmash.backdrops import draw_backdrop, draw_platform
from k8ssmash.config import CANVAS_H, CANVAS_W, FPS
from k8ssmash.fighter import (BUFF_ARMOR, BUFF_GUARD, BUFF_HASTE, BUFF_POWER, CALLOUT_FRAMES, Fighter,
                              FighterStats, Projectile)
from k8ssmash.fx import draw_effect, draw_projectile
from k8ssmash.items import ItemSpawner, draw_item
from k8ssmash.input import PlayerInput
from k8ssmash.scenes.base import Scene
from k8ssmash.sprites import pick_frame, sprite_set
from k8ssmash.stage import Stage, datacenter_stage

READY_FRAMES = 90
MATCH_SECONDS = 120
GAME_FRAMES = 150  # 'GAME!' banner before the results screen
IDLE_ABORT = 45 * FPS

P_COLORS = [(80, 160, 255), (255, 110, 90)]


class Battle(Scene):
    def __init__(self, app, stats: list[FighterStats], stage: Stage | None = None, stocks: int = 3,
                 human: list[bool] | None = None, demo: bool = False, items: bool | None = None):
        super().__init__(app)
        self.spawner = ItemSpawner(enabled=app.cfg.items if items is None else items)
        self.stage = stage or datacenter_stage()
        self.human = human or [True, True]
        self.demo = demo
        self.fighters = [Fighter(st, i, stocks) for i, st in enumerate(stats)]
        for i, f in enumerate(self.fighters):
            f.spawn(self.stage.spawns[i], 1 if i == 0 else -1)
        # Human slots read the shared pads; CPU slots get their own PlayerInput driven by an AI.
        self.cpu_inputs = {i: PlayerInput() for i, h in enumerate(self.human) if not h}
        self.ais = {i: SimpleAI(self.fighters[i], self.fighters[1 - i], self.stage) for i in self.cpu_inputs}
        self.projectiles: list[Projectile] = []
        self.effects: list[tuple[str, float, float, int]] = []  # (kind, x, y, frames left)
        self.frame = 0
        self.time_left = MATCH_SECONDS * FPS
        self.hitstop = 0
        self.winner: int | None = None  # fighter slot, -1 for a draw
        self.finished_frames = 0
        self.debug = False
        app.audio.music(MUSIC_FOR_THEME.get(self.stage.theme, "datacenter"))
        self.font = pygame.font.Font(None, 22)
        self.big = pygame.font.Font(None, 44)
        self.huge = pygame.font.Font(None, 80)

    # --- logic ---------------------------------------------------------------------------
    @property
    def phase(self) -> str:
        if self.winner is not None:
            return "finished"
        return "ready" if self.frame < READY_FRAMES else "fight"

    @property
    def paused_for_pad(self) -> bool:
        return any(self.human[s] for s in self.app.input.lost if s < len(self.human)) and not self.demo

    def _inputs(self) -> list[PlayerInput]:
        for slot, ai in self.ais.items():
            self.cpu_inputs[slot].update(ai.decide())
        return [self.cpu_inputs[i] if i in self.cpu_inputs else self.app.input.players[i]
                for i in range(len(self.fighters))]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            self.debug = not self.debug

    def update(self) -> None:
        if self.paused_for_pad:
            return
        inputs = self._inputs()
        self.frame += 1
        if self.phase == "finished":
            self.finished_frames += 1
            if self.finished_frames >= GAME_FRAMES and not self.demo:
                from k8ssmash.scenes.results import Results
                summary = [{"name": f.stats.name, "kos": f.kos, "damage": f.dealt_damage,
                            "stocks": max(f.stocks, 0)} for f in self.fighters]
                self.app.set_scene(Results(self.app, self.winner, summary))
            return
        if not self.demo and self.app.idle_frames >= IDLE_ABORT and any(self.human):
            self.app.go_title()
            return
        if self.phase == "ready":
            if self.frame in (1, 31, 61):
                self.app.audio.play("countdown")
            return
        if self.frame == READY_FRAMES:
            self.app.audio.play("go")
        if self.hitstop > 0:
            self.hitstop -= 1
            return

        self.time_left -= 1
        self.stage.tick(self.frame)
        for f, inp in zip(self.fighters, inputs):
            f.update(inp, self.stage)
            for ev in f.events:
                self.app.audio.play(ev, 0.7 if ev in ("jump", "djump") else 1.0)
            f.events.clear()
            for proj in f.spawn_queue:
                if proj.defn.replace_existing:
                    self.projectiles = [q for q in self.projectiles
                                        if not (q.owner is f and q.defn.shape == proj.defn.shape)]
                self.projectiles.append(proj)
            f.spawn_queue.clear()
        self.effects = [(k, x, y, t - 1) for k, x, y, t in self.effects if t > 1]
        for f, item in self.spawner.update(self.stage, self.fighters):
            self.effects.append(("pickup", f.x, f.y - f.stats.height / 2, 24))
            self.app.audio.play("pickup")

        self._update_projectiles()
        self._resolve_melee()
        for f in self.fighters:
            if f.alive and not self.stage.blast.collidepoint(f.x, f.y - f.stats.height / 2):
                if f.last_hit_by is not None:
                    f.last_hit_by.kos += 1
                f.last_hit_by = None
                f.knock_out()
                self.app.audio.play("ko")
        self._check_end()

    def _hit(self, victim: Fighter, attacker: Fighter, damage: float, base: float, growth: float,
             angle: float, direction: int) -> bool:
        """Resolve one hit. Returns True if the attack connected (hit, shield or counter)."""
        damage *= attacker.damage_mult
        if victim.countering:
            m = victim.move
            assert m is not None
            attacker.apply_hit(m.damage * victim.damage_mult, m.base_kb, m.kb_growth, m.angle, victim.facing)
            victim.dealt_damage += m.damage * victim.damage_mult
            attacker.last_hit_by = victim
            victim.say("COUNTER!")
            self.hitstop = 8
            self.effects.append(("counter", victim.x, victim.y - 24, 18))
            self.app.audio.play("counter")
            return True
        result = victim.apply_hit(damage, base, growth, angle, direction)
        if result == "ignored":
            return False
        if result == "shield":
            self.app.audio.play("shield")
        if result == "hit":
            self.app.audio.play("hit_heavy" if damage >= 7 else "hit_light")
            attacker.dealt_damage += damage
            victim.last_hit_by = attacker
            self.hitstop = 3 + int(damage // 4)
            self.effects.append(("hit", victim.x, victim.y - victim.stats.height / 2, 10))
        return True

    def _resolve_melee(self) -> None:
        for atk in self.fighters:
            box = atk.active_hitbox()
            if box is None or atk.move is None:
                continue
            for vic in self.fighters:
                if vic is atk or vic.slot in atk.hit_targets or not vic.alive:
                    continue
                if box.colliderect(vic.hurtbox):
                    m = atk.move
                    if self._hit(vic, atk, m.damage, m.base_kb, m.kb_growth, m.angle, atk.facing):
                        atk.hit_targets.add(vic.slot)

    def _explode(self, p: Projectile) -> None:
        d = p.defn
        self.effects.append(("boom", p.x, p.y, 20))
        self.app.audio.play("explosion")
        for vic in self.fighters:
            if not vic.alive or (vic is p.owner and d.harmless_to_owner):
                continue
            cx, cy = vic.hurtbox.center
            if math.hypot(cx - p.x, cy - p.y) <= d.explode_radius:
                direction = 1 if cx >= p.x else -1
                self._hit(vic, p.owner, d.explode_damage, 4.0, 0.06, 60, direction)

    def _update_projectiles(self) -> None:
        alive: list[Projectile] = []
        for p in self.projectiles:
            p.update(self.stage)
            d = p.defn
            if p.life <= 0 or not self.stage.blast.collidepoint(p.x, p.y):
                if p.life <= 0 and d.explode_radius:
                    self._explode(p)
                continue
            consumed = False
            for vic in self.fighters:
                if (vic is p.owner and d.harmless_to_owner) or not vic.alive or not p.can_hit(vic.slot):
                    continue
                if not p.rect.colliderect(vic.hurtbox):
                    continue
                if vic.countering and not d.orbit:
                    # Reflect: the projectile now belongs to the countering fighter.
                    p.owner, p.vx, p.facing = vic, -p.vx, -p.facing
                    p.age = 0
                    p.hit_at.clear()
                    vic.say("REFLECT!")
                    break
                direction = p.facing if p.vx else (1 if vic.x >= p.x else -1)
                if self._hit(vic, p.owner, d.damage, d.base_kb, d.kb_growth, d.angle, direction):
                    p.mark_hit(vic.slot)
                    consumed = not (d.pierce or d.hit_interval or d.orbit)
                    if consumed and d.explode_radius:
                        self._explode(p)
                    break
            if not consumed:
                alive.append(p)
        self.projectiles = alive

    def _check_end(self) -> None:
        alive = [f for f in self.fighters if not f.eliminated]
        if len(alive) == 1:
            self.winner = alive[0].slot
        elif not alive:
            self.winner = -1
        elif self.time_left <= 0:
            a, b = self.fighters
            if a.stocks != b.stocks:
                self.winner = 0 if a.stocks > b.stocks else 1
            elif a.percent != b.percent:
                self.winner = 0 if a.percent < b.percent else 1
            else:
                self.winner = -1

    # --- drawing -------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        draw_backdrop(canvas, self.stage.theme, self.frame)
        for plat in self.stage.platforms:
            draw_platform(canvas, plat, self.stage.theme)
        for item in self.spawner.items:
            draw_item(canvas, item, self.font, self.frame)
        for f in self.fighters:
            self._draw_fighter(canvas, f)
        for p in self.projectiles:
            draw_projectile(canvas, p)
        for kind, x, y, left in self.effects:
            draw_effect(canvas, kind, x, y, left)
        self._draw_hud(canvas)
        if self.paused_for_pad:
            shade = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 180))
            canvas.blit(shade, (0, 0))
            who = " & ".join(f"P{s + 1}" for s in sorted(self.app.input.lost))
            self._center(canvas, "CONTROLLER DISCONNECTED", self.big, 130)
            self._center(canvas, f"Reconnect {who} controller to resume", self.font, 175)
            return
        if self.phase == "ready":
            n = 3 - self.frame * 3 // READY_FRAMES
            self._center(canvas, str(n) if n > 0 else "GO!", self.huge, 140)
        elif self.phase == "finished":
            self._center(canvas, "GAME!", self.huge, 120)

    def _center(self, canvas: pygame.Surface, text: str, font: pygame.font.Font, y: int) -> None:
        surf = font.render(text, False, (255, 255, 255))
        canvas.blit(surf, ((CANVAS_W - surf.get_width()) // 2, y))

    def _draw_fighter(self, canvas: pygame.Surface, f: Fighter) -> None:
        if not f.alive:
            return
        if f.invuln > 0 and (f.invuln // 4) % 2 == 0:
            return
        box = f.hurtbox
        sprites = sprite_set(f.stats.name)
        if sprites is not None:
            anim, idx = pick_frame(f)
            img = sprites.get(anim, idx, f.facing, f.scale)
            if f.state == "hurt" and f.hitstun % 4 < 2:
                img = img.copy()
                img.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_ADD)
            fx, fy = sprites.feet
            canvas.blit(img, (round(f.x - fx * f.scale), round(f.y - fy * f.scale)))
        else:
            pygame.draw.rect(canvas, f.stats.color, box)
        if f.shielding:
            r = int(18 + 12 * f.shield_hp / 60)
            bubble = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (120, 220, 255, 70), (r, r), r)
            pygame.draw.circle(bubble, (180, 240, 255, 200), (r, r), r, 2)
            canvas.blit(bubble, (box.centerx - r, box.centery - r))
        for buff, color in ((BUFF_ARMOR, (255, 170, 60)), (BUFF_GUARD, (120, 255, 150)),
                            (BUFF_POWER, (255, 120, 90)), (BUFF_HASTE, (255, 240, 120))):
            if f.has(buff) and (self.frame // 6) % 2 == 0:
                pygame.draw.ellipse(canvas, color, box.inflate(6, 4), 1)
        hb = f.active_hitbox()
        if hb is not None and self.debug:
            pygame.draw.rect(canvas, (255, 240, 120), hb, 1)
        if self.debug:
            pygame.draw.rect(canvas, (0, 255, 0), box, 1)
            label = self.font.render(f"{f.state} {f.move_frame}", False, (255, 255, 255))
            canvas.blit(label, (box.x - 10, box.y - 16))
        if f.callout_timer > 0:
            text = self.font.render(f.callout, False, (255, 255, 255))
            shadow = self.font.render(f.callout, False, (16, 12, 28))
            pos = (box.centerx - text.get_width() // 2, box.top - 26 - (CALLOUT_FRAMES - f.callout_timer) // 8)
            canvas.blit(shadow, (pos[0] + 1, pos[1] + 1))
            canvas.blit(text, pos)

    def _draw_hud(self, canvas: pygame.Surface) -> None:
        for f in self.fighters:
            x = 90 + f.slot * 300
            color = P_COLORS[f.slot]
            pct = self.big.render(f"{int(f.percent)}%", False, color)
            canvas.blit(pct, (x, 310))
            tag = self.font.render(f"P{f.slot + 1} {f.stats.name}", False, (200, 200, 220))
            canvas.blit(tag, (x, 296))
            for i in range(max(f.stocks, 0)):
                pygame.draw.circle(canvas, color, (x + 100 + i * 14, 326), 5)
        secs = max(self.time_left // FPS, 0)
        t = self.big.render(f"{secs // 60}:{secs % 60:02d}", False, (230, 230, 240))
        canvas.blit(t, ((CANVAS_W - t.get_width()) // 2, 10))

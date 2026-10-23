from __future__ import annotations

import pygame

from k8ssmash.config import CANVAS_H, CANVAS_W, FPS
from k8ssmash.fighter import Fighter, FighterStats, Projectile
from k8ssmash.scenes.base import Scene
from k8ssmash.stage import Stage, datacenter_stage

READY_FRAMES = 90
MATCH_SECONDS = 180
RESULT_LOCK = 90

BG = (18, 22, 38)
PLATFORM = (70, 90, 140)
PLATFORM_TOP = (140, 170, 230)
P_COLORS = [(80, 160, 255), (255, 110, 90)]


class Battle(Scene):
    def __init__(self, app, stats: list[FighterStats], stage: Stage | None = None, stocks: int = 3):
        super().__init__(app)
        self.stage = stage or datacenter_stage()
        self.fighters = [Fighter(st, i, stocks) for i, st in enumerate(stats)]
        for i, f in enumerate(self.fighters):
            f.spawn(self.stage.spawns[i], 1 if i == 0 else -1)
        self.projectiles: list[Projectile] = []
        self.frame = 0
        self.time_left = MATCH_SECONDS * FPS
        self.hitstop = 0
        self.winner: int | None = None  # fighter slot, -1 for a draw
        self.finished_frames = 0
        self.debug = False
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
        return bool(self.app.input.lost)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            self.debug = not self.debug

    def update(self) -> None:
        inputs = self.app.input.players
        if self.paused_for_pad:
            return
        self.frame += 1
        if self.phase == "finished":
            self.finished_frames += 1
            if self.finished_frames > RESULT_LOCK and self.app.input.any_pressed("START"):
                self.app.set_scene(Battle(self.app, [f.stats for f in self.fighters]))
            return
        if self.phase == "ready":
            return
        if self.hitstop > 0:
            self.hitstop -= 1
            return

        self.time_left -= 1
        for f, inp in zip(self.fighters, inputs):
            f.update(inp, self.stage)
            self.projectiles.extend(f.spawn_queue)
            f.spawn_queue.clear()

        self._update_projectiles()
        self._resolve_melee()
        for f in self.fighters:
            if f.alive and not self.stage.blast.collidepoint(f.x, f.y - f.stats.height / 2):
                f.knock_out()
        self._check_end()

    def _hit(self, victim: Fighter, attacker: Fighter, damage: float, base: float, growth: float,
             angle: float, direction: int) -> bool:
        result = victim.apply_hit(damage, base, growth, angle, direction)
        if result == "ignored":
            return False
        if result == "hit":
            attacker.dealt_damage += damage
            self.hitstop = 3 + int(damage // 4)
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
                        if vic.ko_timer == 0 and vic.percent and False:
                            pass

    def _update_projectiles(self) -> None:
        alive: list[Projectile] = []
        for p in self.projectiles:
            p.update()
            if p.life <= 0 or not self.stage.blast.collidepoint(p.x, p.y):
                continue
            consumed = False
            for vic in self.fighters:
                if vic is p.owner or not vic.alive:
                    continue
                if p.rect.colliderect(vic.hurtbox):
                    d = p.defn
                    consumed = self._hit(vic, p.owner, d.damage, d.base_kb, d.kb_growth, d.angle, p.facing)
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
        canvas.fill(BG)
        for plat in self.stage.platforms:
            pygame.draw.rect(canvas, PLATFORM, plat.rect)
            pygame.draw.rect(canvas, PLATFORM_TOP, (plat.rect.x, plat.rect.y, plat.rect.w, 3))
        for p in self.projectiles:
            pygame.draw.ellipse(canvas, p.defn.color, p.rect)
        for f in self.fighters:
            self._draw_fighter(canvas, f)
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
            text = "DRAW" if self.winner == -1 else f"P{self.winner + 1} WINS"
            self._center(canvas, text, self.huge, 120)
            if self.finished_frames > RESULT_LOCK:
                self._center(canvas, "Press START for rematch", self.big, 190)

    def _center(self, canvas: pygame.Surface, text: str, font: pygame.font.Font, y: int) -> None:
        surf = font.render(text, False, (255, 255, 255))
        canvas.blit(surf, ((CANVAS_W - surf.get_width()) // 2, y))

    def _draw_fighter(self, canvas: pygame.Surface, f: Fighter) -> None:
        if not f.alive:
            return
        if f.invuln > 0 and (f.invuln // 4) % 2 == 0:
            return
        box = f.hurtbox
        color = f.stats.color
        if f.state == "hurt":
            color = (255, 255, 255) if f.hitstun % 4 < 2 else color
        pygame.draw.rect(canvas, color, box)
        eye_x = box.centerx + f.facing * 5 - 2
        pygame.draw.rect(canvas, (20, 20, 30), (eye_x, box.top + 8, 4, 5))
        if f.shielding:
            r = int(16 + 12 * f.shield_hp / 60)
            pygame.draw.circle(canvas, (120, 220, 255), box.center, r, 2)
        hb = f.active_hitbox()
        if hb is not None:
            pygame.draw.rect(canvas, (255, 240, 120), hb, 0 if self.debug else 1)
        if self.debug:
            pygame.draw.rect(canvas, (0, 255, 0), box, 1)
            label = self.font.render(f"{f.state} {f.move_frame}", False, (255, 255, 255))
            canvas.blit(label, (box.x - 10, box.y - 16))

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

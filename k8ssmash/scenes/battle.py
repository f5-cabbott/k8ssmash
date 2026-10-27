from __future__ import annotations

import math
import random

import pygame

from k8ssmash import backdrops, ui
from k8ssmash.ui import wd
from k8ssmash.ai import SimpleAI
from k8ssmash.audio_manager import MUSIC_FOR_THEME
from k8ssmash.backdrops import draw_backdrop, draw_platform
from k8ssmash.config import FPS, PIX_H, PIX_W, RS, WORLD_H, WORLD_W
from k8ssmash.flair import INTRO
from k8ssmash.fighter import (BUFF_ARMOR, BUFF_CANARY, BUFF_GUARD, BUFF_HASTE, BUFF_POWER, BUFF_THROTTLED, CALLOUT_FRAMES, Fighter,
                              FighterStats, Projectile)
from k8ssmash.fx import draw_effect, draw_projectile
from k8ssmash.items import BUFF_ITEM, ItemSpawner, draw_icon, draw_item
from k8ssmash.metrics import METRICS
from k8ssmash.particles import Particles
from k8ssmash.input import PlayerInput
from k8ssmash.palette import damage_color, player_colors
from k8ssmash.scenes.base import Scene
from k8ssmash.sprites import pick_frame, resolve_variants, sprite_set
from k8ssmash.stage import Stage, datacenter_stage

READY_FRAMES = 90
MATCH_SECONDS = 120
GAME_FRAMES = 150  # 'GAME!' banner before the results screen
IDLE_ABORT = 45 * FPS

SLOWMO_FRAMES = 110  # real frames of slow motion after the final KO (runs at quarter speed)
BANNER_FRAMES = 80
KO_REASONS = ["OOMKilled", "Evicted", "CrashLoopBackOff", "ImagePullBackOff", "Terminated", "NodeNotReady",
              "Preempted"]
READY_STATUS = ["Pending...", "ContainerCreating...", "RUNNING!"]


COMBO_SHOW = 70  # frames the combo counter stays up after the last hit
_VIGNETTES: dict[int, pygame.Surface] = {}


def vignette(width: int = PIX_W) -> pygame.Surface:
    """A soft dark-edged overlay, built once per canvas width from a tiny gradient and smooth-scaled up."""
    if width not in _VIGNETTES:
        w, h = 64, 36
        small = pygame.Surface((w, h), pygame.SRCALPHA)
        for yy in range(h):
            for xx in range(w):
                d = math.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
                a = max(0.0, min(1.0, (d - 0.55) / 0.8)) ** 1.4
                small.set_at((xx, yy), (0, 0, 8, int(255 * a)))
        _VIGNETTES[width] = pygame.transform.smoothscale(small, (width, PIX_H))
    return _VIGNETTES[width]


class Battle(Scene):
    native = (PIX_W, PIX_H)
    wide = True  # takes the whole (possibly ultrawide) canvas: scenery fills it, the arena sits in the middle
    metrics_mode: str | None = None  # None: derived from who is human
    can_pause = True  # START opens the pause menu (training has its own use for START)

    def __init__(self, app, stats: list[FighterStats], stage: Stage | None = None, stocks: int | None = None,
                 human: list[bool] | None = None, demo: bool = False, items: bool | None = None,
                 variants: list[int] | None = None):
        super().__init__(app)
        self.spawner = ItemSpawner(enabled=app.cfg.items if items is None else items)
        self.stage = stage or datacenter_stage()
        self.human = human or [True, True]
        self.demo = demo
        self.fighters = [Fighter(st, i, app.cfg.stocks if stocks is None else stocks) for i, st in enumerate(stats)]
        for i, f in enumerate(self.fighters):
            f.spawn(self.stage.spawns[i], 1 if i == 0 else -1)
        # Human slots read the shared pads; CPU slots get their own PlayerInput driven by an AI.
        self.cpu_inputs = {i: PlayerInput() for i, h in enumerate(self.human) if not h}
        self.ais = {i: SimpleAI(self.fighters[i], self.fighters[1 - i], self.stage) for i in self.cpu_inputs}
        self.projectiles: list[Projectile] = []
        self.effects: list[tuple[str, float, float, int]] = []  # (kind, x, y, frames left)
        self.frame = 0
        self.time_left = (app.cfg.match_seconds or MATCH_SECONDS) * FPS
        self.hitstop = 0
        self.combos: dict[int, tuple[int, int, int]] = {}  # attacker slot -> (hits, frames to show, victim slot)
        self.winner: int | None = None  # fighter slot, -1 for a draw
        self.finished_frames = 0
        self.debug = False
        self._reported = False
        if not self.demo:
            METRICS.inc("matches_started_total", mode=self.mode_label)
            for f in self.fighters:
                METRICS.inc("fighter_picks_total", fighter=f.stats.name)
        self.cam = 0.0
        backdrops.REACT["ripples"].clear()
        self.variants = resolve_variants([f.stats.name for f in self.fighters],
                                         list(variants if variants is not None else app.last_variants))
        self.paused = False
        self.stem_level = 0.0
        self.pause_row = 0
        self.best_combos = [0] * len(self.fighters)
        self.kill_focus: tuple[float, float] | None = None
        self.hot = False  # the final-stock version of the music is playing
        self.motif_ready = [0] * len(self.fighters)  # frame when each fighter's leitmotif may play again
        self.fx = Particles()
        self.ghosts: list[list] = [[] for _ in self.fighters]  # dash afterimages: [surface, x, y, logic frame]
        self.slowmo = 0
        self._slow_tick = 0
        self.banners: list[list] = []  # [text, color, frames left]
        self.hud_pulse = [0] * len(self.fighters)
        self.rng = random.Random()
        song = MUSIC_FOR_THEME.get(self.stage.theme, "datacenter")
        app.audio.music(song, stem=None if self.demo else f"{song}_stem")  # percussion layer that rises with the damage
        self.font = ui.Font(22 * RS)
        self.big = ui.Font(44 * RS)
        self.huge = ui.Font(80 * RS)
        self.callout_font = ui.Font(15 * RS)
        self.tag_font = ui.Font(13 * RS)
        self.finale_font = ui.Font(30 * RS)
        self.pct_font = ui.Font(58 * RS)
        self.pct_pulse = ui.Font(72 * RS)
        self.colors = player_colors(app.cfg)

    # --- logic ---------------------------------------------------------------------------
    @property
    def mode_label(self) -> str:
        return self.metrics_mode or ("versus" if all(self.human) else "vs_cpu")

    def _report_result(self) -> None:
        if self._reported or self.winner is None:
            return
        if self.demo:
            return
        self._reported = True
        self.app.audio.play("ann_game")
        self.app.audio.fade_out(900)  # the arena song dies away; the victory theme takes over on the results screen
        METRICS.inc("matches_finished_total", mode=self.mode_label)
        METRICS.observe("match_duration_seconds", (self.frame - READY_FRAMES) / FPS)
        if self.winner in (0, 1):
            METRICS.inc("fighter_wins_total", fighter=self.fighters[self.winner].stats.name)

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
        if self.can_pause and not self.demo and self.phase != "finished":
            if any("START" in p.pressed and "SELECT" not in p.held for p in self.app.input.players):
                self._set_paused(not self.paused)
        if self.paused:
            self._pause_input()
            return
        inputs = self._inputs()
        self.frame += 1
        if self.phase == "finished":
            self.finished_frames += 1
            if self.finished_frames >= GAME_FRAMES and not self.demo:
                from k8ssmash.scenes.results import Results
                summary = [{"name": f.stats.name, "kos": f.kos, "damage": f.dealt_damage,
                            "stocks": max(f.stocks, 0), "combo": self.best_combos[f.slot]} for f in self.fighters]
                self.app.set_scene(Results(self.app, self.winner, summary, self.human))
            return
        if not self.demo and self.app.idle_frames >= IDLE_ABORT and any(self.human):
            self.app.go_title()
            return
        if not self.demo:  # the percussion layer of the music builds as the fight heats up
            avg = sum(f.percent for f in self.fighters) / max(1, len(self.fighters))
            target = max(0.0, min(1.0, (avg / 120.0 - 0.18) / 0.62))
            self.stem_level += (target - self.stem_level) * 0.02
            self.app.audio.set_stem_level(self.stem_level)
        if self.phase == "ready":
            if self.frame == 4 and not self.demo:  # everybody gets a line walking in
                for f in self.fighters:
                    f.say(INTRO.get(f.stats.name, ""))
            if self.frame in (1, 31, 61):
                self.app.audio.play("countdown")
            if self.frame == 6 and not self.demo:
                self.app.audio.play("ann_ready")
            return
        if self.frame == READY_FRAMES:
            self.app.audio.play("go")
            if not self.demo:
                self.app.audio.play("ann_fight")
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        if self.slowmo > 0:
            self.slowmo -= 1
            self._slow_tick = (self._slow_tick + 1) % 4
            if self._slow_tick:
                return  # the final KO plays out at quarter speed

        self.hud_pulse = [max(0, p - 1) for p in self.hud_pulse]
        self.fx.update()
        self.banners = [[t, c, n - 1] for t, c, n in self.banners if n > 1]
        self.time_left -= 1
        self.stage.tick(self.frame)
        for f, inp in zip(self.fighters, inputs):
            f.update(inp, self.stage)
            for ev in f.events:
                self.app.audio.play(ev, 0.7 if ev in ("jump", "djump") else 1.0, pan=self.pan_of(f), fighter=f.stats.name)
                if ev == "special" and f.move is not None and not self.demo:
                    METRICS.inc("specials_used_total", fighter=f.stats.name, move=f.move.name)
            f.events.clear()
            self._fighter_fx(f)
            for proj in f.spawn_queue:
                if proj.defn.replace_existing:
                    self.projectiles = [q for q in self.projectiles
                                        if not (q.owner is f and q.defn.shape == proj.defn.shape)]
                self.projectiles.append(proj)
            f.spawn_queue.clear()
        self.effects = [(k, x, y, t - 1) for k, x, y, t in self.effects if t > 1]
        self.combos = {s: (n, t - 1, v) for s, (n, t, v) in self.combos.items() if t > 1}
        for f, item in self.spawner.update(self.stage, self.fighters):
            self.effects.append(("pickup", f.x, f.y - f.stats.height / 2, 24))
            self.fx.sparkle(f.x, f.y - 24, (255, 245, 170), 9, 16)
            self.fx.ring(f.x, f.y - 22, item.defn.color, 26, 24)
            self.app.audio.play("pickup", pan=self.pan_of(f))
            if not self.demo:
                METRICS.inc("items_picked_total", item=item.defn.key)

        self._update_projectiles()
        self._resolve_melee()
        for f in self.fighters:
            if f.alive and not self.stage.blast.collidepoint(f.x, f.y - f.stats.height / 2):
                if f.last_hit_by is not None:
                    f.last_hit_by.kos += 1
                    if not self.demo:
                        METRICS.inc("fighter_kos_total", fighter=f.last_hit_by.stats.name)
                f.last_hit_by = None
                self._ko_burst(f)
                f.knock_out()
                self._second_wind(f)
                self.app.audio.play("ko", pan=self.pan_of(f), fighter=f.stats.name)
                self.announce(f"{f.stats.name}: {self.rng.choice(KO_REASONS)}", self.colors[f.slot])
                if f.eliminated and not self.demo:
                    self.slowmo = SLOWMO_FRAMES
                    self.kill_focus = (max(40.0, min(WORLD_W - 40.0, f.x)), max(40.0, min(WORLD_H - 120.0, f.y)))
        if self.slowmo == 0:
            self._check_end()
            self._report_result()

    # --- pause menu ----------------------------------------------------------------------
    PAUSE_ROWS = ("Resume", "Restart match", "Quit to title")

    def _set_paused(self, on: bool) -> None:
        self.paused, self.pause_row = on, 0
        self.app.audio.play("menu_select" if on else "menu_move")
        self.app.audio.pause_music(on)

    def _pause_input(self) -> None:
        players = self.app.input.players
        for inp in players:
            if "UP" in inp.pressed:
                self.pause_row = (self.pause_row - 1) % len(self.PAUSE_ROWS)
                self.app.audio.play("menu_move")
            if "DOWN" in inp.pressed:
                self.pause_row = (self.pause_row + 1) % len(self.PAUSE_ROWS)
                self.app.audio.play("menu_move")
        if any(inp.pressed & {"ATTACK"} for inp in players):
            self._set_paused(False)
        elif any("SPECIAL" in inp.pressed for inp in players):
            choice = self.pause_row
            self._set_paused(False)
            if choice == 1:
                self._restart()
            elif choice == 2:
                self.app.go_title()

    def _restart(self) -> None:
        from k8ssmash.stage import STAGES

        stage = next((make() for make in STAGES if make().name == self.stage.name), None)
        self.app.set_scene(Battle(self.app, [f.stats for f in self.fighters], stage=stage, human=self.human))

    def _draw_pause(self, canvas: pygame.Surface) -> None:
        from k8ssmash.ui import pd

        shade = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 8, 170))
        canvas.blit(shade, (0, 0))
        if not hasattr(self, "_pause_fonts"):
            self._pause_fonts = (ui.UIFont(34), ui.UIFont(22), ui.UIFont(13))
        big, font, small = self._pause_fonts
        panel = pygame.Rect(210, 100, 220, 150)
        ui.window_d(canvas, panel, accent=(255, 224, 90))
        title = big.render("PAUSED", False, (255, 224, 90))
        pd.blit(canvas, title, (panel.centerx - title.get_width() // 2, panel.y + 8))
        for i, label in enumerate(self.PAUSE_ROWS):
            y = panel.y + 56 + i * 26
            if i == self.pause_row:
                pd.rect(canvas, (60, 90, 200), (panel.x + 10, y - 3, panel.w - 20, 24), border_radius=4)
            t = font.render(label, False, (255, 255, 255) if i == self.pause_row else (180, 192, 232))
            pd.blit(canvas, t, (panel.centerx - t.get_width() // 2, y))
        hint = small.render("UP / DOWN choose     A select     START resume", False, (150, 166, 220))
        pd.blit(canvas, hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 20))

    def _punch_in(self, canvas: pygame.Surface, k: float) -> None:
        """Kill cam: ease the picture in toward where the last fighter was launched (a smooth zoom, never a flash)."""
        if self.kill_focus is None or k <= 0.01:
            return
        z = 1.0 + 0.30 * k
        w, h = int(PIX_W / z), int(PIX_H / z)
        fx, fy = self.kill_focus[0] * RS, self.kill_focus[1] * RS
        x = int(max(0, min(PIX_W - w, fx - w / 2)))
        y = int(max(0, min(PIX_H - h, fy - h / 2)))
        src = canvas.copy()
        pygame.transform.smoothscale(src.subsurface((x, y, w, h)), canvas.get_size(), canvas)

    def _fighter_fx(self, f: Fighter) -> None:
        """Visual juice from what a fighter just did: landing dust, jump rings, run puffs, buff sparkles, launch streaks."""
        for kind, k in f.fx:
            if kind == "land":
                self.fx.dust(f.x, f.y, k)
            elif kind == "jump":
                self.fx.dust(f.x, f.y, 0.25)
            elif kind == "djump":
                self.fx.ring(f.x, f.y - 6, (210, 238, 255), 24, 18)
                self.fx.burst(f.x, f.y - 4, (225, 242, 255), 4, 1.8, angle=math.pi / 2, spread=1.5)
        f.fx.clear()
        if f.state == "run" and f.on_ground and f.anim_frame % 9 == 0:
            self.fx.dust(f.x - f.facing * 9, f.y, 0.12)
        if f.buffs and self.frame % 8 == 0:
            color = (255, 130, 90) if f.has("power") else (120, 255, 160) if f.has("guard") else (255, 190, 80) if f.has("armor") else (255, 240, 120)
            self.fx.sparkle(f.x, f.y - 22, color, 1, 12)
        if f.state == "hurt" and math.hypot(f.vx, f.vy) > 7 and self.frame % 2 == 0:
            self.fx.streak(f.x, f.y - 22, f.vx, f.vy, self.colors[f.slot])

    def _feed_backdrop(self) -> None:
        """Tell the scenery how the fight is going so it can respond: heat, who is leading, how many KOs."""
        avg = sum(f.percent for f in self.fighters) / max(1, len(self.fighters))
        target = min(1.0, avg / 120.0)
        backdrops.REACT["energy"] += (target - backdrops.REACT["energy"]) * 0.02
        dealt = [f.dealt_damage for f in self.fighters]
        lead = (dealt[0] - dealt[1]) / max(30.0, dealt[0] + dealt[1]) if len(dealt) > 1 else 0.0
        backdrops.REACT["leader"] = max(-1.0, min(1.0, lead * 2.0))
        backdrops.REACT["kos"] = sum(f.kos for f in self.fighters)
        backdrops.tick_ripples()

    def _count_combo(self, attacker: Fighter, victim: Fighter, chained: bool) -> None:
        """Hits that land while the victim is still reeling from the last one build a combo."""
        count, _, vslot = self.combos.get(attacker.slot, (0, 0, -1))
        count = count + 1 if chained and vslot == victim.slot and count else 1
        self.combos[attacker.slot] = (count, COMBO_SHOW, victim.slot)
        self.best_combos[attacker.slot] = max(self.best_combos[attacker.slot], count)
        if count >= 3:
            self.fx.ring(victim.x, victim.y - victim.stats.height - 8, (255, 214, 90), 20 + count * 3, 16)
            self.app.audio.play("counter", pan=self.pan_of(victim))
            self._leitmotif(attacker)

    def _leitmotif(self, f: Fighter) -> None:
        """A fighter on a roll gets their own tune over the stage music, in the song's key, at most every ten seconds."""
        if self.demo or self.frame < self.motif_ready[f.slot]:
            return
        self.motif_ready[f.slot] = self.frame + 10 * FPS
        shift = {"controlplane": 2}.get(self.stage.theme, 0) + (2 if self.hot else 0)
        self.app.audio.play(f"motif{shift}", 0.55, pan=self.pan_of(f), fighter=f.stats.name)

    def _second_wind(self, f: Fighter) -> None:
        """Down to the last stock while the other fighter still has spare ones: a modest comeback boost."""
        others = [o for o in self.fighters if o is not f and not o.eliminated]
        if f.stocks == 1 and not f.eliminated and not f.comeback and others and max(o.stocks for o in others) >= 2:
            f.comeback = True
            self.announce("LAST STOCK: SECOND WIND!", self.colors[f.slot])
            self.app.audio.play("ann_final_stock")
            self.hot = True
            if not self.demo:  # the stage music lifts: faster and higher for the final stretch
                hot = MUSIC_FOR_THEME.get(self.stage.theme, "datacenter") + "_hot"
                self.app.audio.music(hot, stem=hot + "_stem")

    def _hit_burst(self, victim: Fighter, attacker: Fighter, damage: float, angle: float, direction: int) -> None:
        cx, cy = victim.hurtbox.center
        rad = math.radians(angle)
        aim = math.atan2(-math.sin(rad), math.cos(rad) * direction)  # the way the victim is being launched
        warm = tuple(int(a * 0.5 + b * 0.5) for a, b in zip(self.colors[attacker.slot], (255, 240, 170)))
        self.fx.burst(cx, cy, warm, 5 + int(damage * 1.2), 3.0 + damage * 0.18, angle=aim, spread=1.5)
        self.fx.ring(cx, cy, (255, 250, 220), min(42, 14 + damage * 2.0), 14)
        if damage >= 9:  # heavy hits get a second, wider ring and a shower of embers
            self.fx.ring(cx, cy, warm, min(54, 22 + damage * 2.4), 20)
            self.fx.burst(cx, cy, (255, 200, 100), 8, 2.4, kind="square", life=(16, 28))

    def _ko_burst(self, f: Fighter) -> None:
        """The KO star: it bursts at the screen edge where the fighter flew out, with sparks fanning back inward."""
        x = max(26.0, min(WORLD_W - 26.0, f.x))
        y = max(26.0, min(WORLD_H - 100.0, f.y - f.stats.height / 2))
        color = self.colors[f.slot]
        self.fx.star(x, y, color, 38)
        self.fx.ring(x, y, (255, 255, 255), 56, 30)
        self.fx.burst(x, y, color, 18, 4.2, angle=math.atan2(WORLD_H / 2 - y, WORLD_W / 2 - x), spread=2.2, life=(18, 34))

    @staticmethod
    def pan_of(f: Fighter) -> float:
        """Stereo position from where the fighter is on screen, kept gentle so it never hard-pans."""
        return max(-0.8, min(0.8, (f.x - WORLD_W / 2) / WORLD_W * 1.8))

    def announce(self, text: str, color=(255, 255, 255)) -> None:
        self.banners = (self.banners + [[text, color, BANNER_FRAMES]])[-2:]

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
            self.app.audio.play("counter", pan=self.pan_of(victim))
            self.fx.ring(victim.x, victim.y - 24, (255, 224, 120), 34, 22)
            self.fx.burst(victim.x, victim.y - 24, (255, 224, 120), 12, 3.6)
            return True
        was_stunned = victim.hitstun > 0
        result = victim.apply_hit(damage, base, growth, angle, direction)
        if result == "ignored":
            return False
        if result == "hit":
            self._count_combo(attacker, victim, was_stunned)
        if result == "shield":
            self.app.audio.play("shield", pan=self.pan_of(victim))
            self.fx.ring(victim.hurtbox.centerx, victim.hurtbox.centery, (150, 235, 255), 26, 14)
            self.fx.burst(victim.hurtbox.centerx + direction * 10, victim.hurtbox.centery, (190, 240, 255), 5, 2.2,
                          angle=0.0 if direction > 0 else math.pi, spread=1.2)
        if result == "hit":
            # the attacker's own impact sound, placed where the victim is
            self.app.audio.play("hit_heavy" if damage >= 7 else "hit_light", pan=self.pan_of(victim),
                                fighter=attacker.stats.name)
            attacker.dealt_damage += damage
            victim.last_hit_by = attacker
            self.hud_pulse[victim.slot] = 12
            self.hitstop = 3 + int(damage // 3)  # a longer freeze on big hits sells the weight
            heavy = damage >= 7
            if heavy:
                        backdrops.hit_ripple(victim.x)
            self.effects.append(("hit_heavy" if heavy else "hit", victim.x, victim.y - victim.stats.height / 2,
                                 14 if heavy else 10))
            self._hit_burst(victim, attacker, damage, angle, direction)
        return True

    def _resolve_melee(self) -> None:
        for atk in self.fighters:
            box = atk.active_hitbox()
            m = atk.move
            if box is None or m is None:
                continue
            for vic in self.fighters:
                if atk.move is not m:  # cancelled mid-loop, e.g. the attacker ran into a counter and was bounced back
                    break
                again = m.rehit and atk.move_frame >= atk.rehit_at.get(vic.slot, 0)  # a multi-hit move may strike again
                if vic is atk or (vic.slot in atk.hit_targets and not again) or not vic.alive:
                    continue
                if box.colliderect(vic.hurtbox):
                    if m.grab:
                        if self._throw(atk, vic):
                            atk.hit_targets.add(vic.slot)
                    elif self._hit(vic, atk, m.damage, m.base_kb, m.kb_growth, m.angle, atk.facing):
                        atk.hit_targets.add(vic.slot)
                        if m.rehit:
                            atk.rehit_at[vic.slot] = atk.move_frame + m.rehit

    def _throw(self, atk: Fighter, vic: Fighter) -> bool:
        """A grab beats a shield. The way the stick is held when it connects picks the throw."""
        if vic.invuln > 0 or vic.intangible:
            return False
        vic.shielding = False
        ax, ay = atk.last_axis
        rel = ax * atk.facing
        if ay < 0:  # up throw: a high launch
            args, direction = (6, 4.6, 0.055, 88), atk.facing
        elif ay > 0:  # down throw: a low pop-up that sets up a follow-up
            args, direction = (5, 3.0, 0.03, 80), atk.facing
        elif rel < 0:  # back throw: the strongest
            args, direction = (8, 4.4, 0.075, 35), -atk.facing
            atk.facing = -atk.facing
        else:  # forward throw
            args, direction = (7, 4.0, 0.06, 32), atk.facing
        vic.x = atk.x + atk.facing * 18  # the victim is held right in front of the thrower
        return self._hit(vic, atk, *args, direction)

    def _explode(self, p: Projectile) -> None:
        d = p.defn
        self.effects.append(("boom", p.x, p.y, 20))
        self.app.audio.play("explosion", pan=max(-0.8, min(0.8, (p.x - WORLD_W / 2) / WORLD_W * 1.8)))
        for vic in self.fighters:
            if not vic.alive or (vic is p.owner and d.harmless_to_owner):
                continue
            cx, cy = vic.hurtbox.center
            if math.hypot(cx - p.x, cy - p.y) <= d.explode_radius:
                direction = 1 if cx >= p.x else -1
                self._hit(vic, p.owner, d.explode_damage, 4.0, 0.06, 60, direction)

    def _pull_toward(self, p: Projectile) -> None:
        """A gravity well drags every opponent in range toward its centre (it never touches its owner)."""
        d = p.defn
        for vic in self.fighters:
            if vic is p.owner or not vic.alive or vic.invuln > 0:
                continue
            cx, cy = vic.hurtbox.center
            dx, dy = p.x - cx, p.y - cy
            dist = math.hypot(dx, dy)
            if 6 < dist <= d.pull_radius:
                k = d.pull * (1.0 - 0.45 * dist / d.pull_radius)
                vic.vx += dx / dist * k
                vic.vy += dy / dist * k * 1.4  # a little extra to beat gravity, so they are held in the well rather than dropped
                vic.vx = max(-7.0, min(7.0, vic.vx))
                vic.vy = max(-6.0, min(6.0, vic.vy))
                if self.frame % 6 == 0:
                    self.fx.burst(cx, cy, d.color, 1, 1.2, angle=math.atan2(dy, dx), spread=0.4, life=(8, 14))

    def _update_projectiles(self) -> None:
        alive: list[Projectile] = []
        for p in self.projectiles:
            p.update(self.stage)
            d = p.defn
            if d.pull:
                self._pull_toward(p)
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
            self.announce("Timeout!", (255, 235, 120))
            a, b = self.fighters
            if a.stocks != b.stocks:
                self.winner = 0 if a.stocks > b.stocks else 1
            elif a.percent != b.percent:
                self.winner = 0 if a.percent < b.percent else 1
            else:
                self.winner = -1

    # --- drawing -------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        full = canvas
        off = (full.get_width() - PIX_W) // 2
        canvas = full.subsurface((off, 0, PIX_W, PIX_H)) if off > 0 else full  # the arena area
        live = [f for f in self.fighters if f.alive]
        cam = (sum(f.x for f in live) / len(live) - WORLD_W / 2) if live else 0.0
        self.cam += (cam - self.cam) * 0.05  # ease, so the scenery drifts rather than snaps
        self._feed_backdrop()
        draw_backdrop(full, self.stage.theme, self.frame, self.cam)
        backdrops.draw_ripples(canvas, self.stage.theme, self.stage.platforms[0].rect.top)
        for plat in self.stage.platforms:
            draw_platform(canvas, plat, self.stage.theme)
        for item in self.spawner.items:
            draw_item(canvas, item, self.tag_font, self.frame)
        for f in self.fighters:
            self._draw_fighter(canvas, f)
        for p in self.projectiles:
            draw_projectile(canvas, p)
        for kind, x, y, left in self.effects:
            draw_effect(canvas, kind, x, y, left)
        self.fx.draw(canvas)
        self._draw_offscreen(canvas)
        self._draw_hud(canvas)
        if self.paused_for_pad:
            shade = pygame.Surface(full.get_size(), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 180))
            full.blit(shade, (0, 0))
            who = " & ".join(f"P{s + 1}" for s in sorted(self.app.input.lost))
            self._center(canvas, "CONTROLLER DISCONNECTED", self.big, WORLD_H // 2 - 50)
            self._center(canvas, f"Reconnect {who} controller to resume", self.font, WORLD_H // 2 - 4)
            return
        if self.paused:
            self._draw_pause(canvas)
            return
        if self.phase == "ready":
            text = READY_STATUS[min(2, self.frame * 3 // READY_FRAMES)]
            self._center(canvas, text, self.huge if len(text) < 12 else self.big, int(WORLD_H * 0.36), shadow=True)
        elif self.phase == "finished":
            self._center(canvas, "GAME!", self.huge, int(WORLD_H * 0.32), shadow=True)
        elif self.slowmo > 0:
            t = 1 - self.slowmo / SLOWMO_FRAMES
            zk = min(1.0, t * 4) * min(1.0, self.slowmo / 24)
            self._punch_in(canvas, zk * zk * (3 - 2 * zk))
            self._draw_finale(canvas, full)
        for i, (text, color, left) in enumerate(self.banners):
            slide = min(1.0, (BANNER_FRAMES - left) / 8)
            y = int(-30 + (84 + i * 34) * slide)
            self._center(canvas, text, self.big, y, color=color, shadow=True)

    def _draw_finale(self, canvas: pygame.Surface, full: pygame.Surface) -> None:
        """Final-KO beat: a soft vignette, cinematic bars and a fading title. Nothing flashes."""
        t = 1 - self.slowmo / SLOWMO_FRAMES
        k = min(1.0, t * 4) * min(1.0, self.slowmo / 24)  # ease in quickly, ease out gently
        k = k * k * (3 - 2 * k)  # smoothstep
        veil = vignette(full.get_width())
        veil.set_alpha(int(200 * k))
        full.blit(veil, (0, 0))
        bar = int(20 * k) * RS
        pygame.draw.rect(full, (6, 6, 14), (0, 0, full.get_width(), bar))
        pygame.draw.rect(full, (6, 6, 14), (0, PIX_H - bar, full.get_width(), bar))
        text = "TERMINATED"
        glyphs = [self.finale_font.render(c, False, (255, 232, 176)) for c in text]
        gap = 5 * RS
        width = sum(g.get_width() for g in glyphs) + gap * (len(text) - 1)
        x, y = (PIX_W - width) // 2, int(PIX_H * 0.42) - int((1 - k) * 8 * RS)
        for g in glyphs:
            g.set_alpha(int(235 * k))
            canvas.blit(g, (x, y))
            x += g.get_width() + gap

    def _center(self, canvas: pygame.Surface, text: str, font: pygame.font.Font, y: int,
                color=(255, 255, 255), shadow: bool = False) -> None:
        """Centred text; y is in world units."""
        surf = font.render(text, False, color)
        x = (PIX_W - surf.get_width()) // 2
        y = int(y * RS)
        if shadow:
            canvas.blit(font.render(text, False, (16, 12, 28)), (x + 2 * RS, y + 2 * RS))
        canvas.blit(surf, (x, y))

    def _draw_offscreen(self, canvas: pygame.Surface) -> None:
        """A fighter knocked past the edge of the picture gets a bubble on the screen edge: their face, their damage and an
        arrow toward where they are. It shrinks the farther they fly, so you can see when they are coming back."""
        for f in self.fighters:
            if not f.alive:
                continue
            cy = f.y - f.stats.height / 2
            if -6 <= f.x <= WORLD_W + 6 and -6 <= cy <= WORLD_H + 6:
                continue
            ix = max(30.0, min(WORLD_W - 30.0, f.x))
            iy = max(30.0, min(WORLD_H - 96.0, cy))  # stay above the damage panels
            over = max(0.0, -f.x, f.x - WORLD_W, -cy, cy - WORLD_H)
            k = max(0.55, 1.0 - over / 520.0)
            r = int(25 * k * RS)
            px, py = int(ix * RS), int(iy * RS)
            color = self.colors[f.slot]
            bubble = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (10, 14, 40, 215), (r, r), r)
            sprites = sprite_set(f.stats.name, self.variants[f.slot])
            if sprites is not None:
                img = sprites.get("idle", 0, f.facing)
                fx, fy = sprites.feet
                bubble.blit(img, (r - fx, r - (fy - int(f.stats.height * 0.78 * RS))))
            mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r - RS)
            bubble.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            pygame.draw.circle(bubble, color, (r, r), r, 2 * RS)
            canvas.blit(bubble, (px - r, py - r))
            dx, dy = f.x - ix, cy - iy
            d = math.hypot(dx, dy) or 1.0
            ux, uy = dx / d, dy / d
            tip = (px + ux * (r + 9 * RS * k), py + uy * (r + 9 * RS * k))
            base = (px + ux * (r + 1 * RS), py + uy * (r + 1 * RS))
            nx, ny = -uy, ux
            w = 6 * RS * k
            pygame.draw.polygon(canvas, color, [tip, (base[0] + nx * w, base[1] + ny * w), (base[0] - nx * w, base[1] - ny * w)])
            label = self.tag_font.render(f"{int(f.percent)}%", False, damage_color(f.percent))
            canvas.blit(label, (px - label.get_width() // 2, py + r + 2 * RS))

    def _draw_buffs(self, canvas: pygame.Surface, f: Fighter) -> None:
        """Steady auras for each running power-up (smooth, never blinking) and a timer ring over the head for each."""
        box = f.hurtbox
        cx, cy = box.centerx, box.centery
        t = self.frame
        R = max(box.w, box.h) * 0.62

        def glow(color, radius, alpha, outline=2):
            r = int(radius * RS)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, alpha), (r, r), r)
            pygame.draw.circle(surf, (*color, min(255, alpha * 4)), (r, r), r, outline * RS)
            canvas.blit(surf, (cx * RS - r, cy * RS - r))
        if f.has(BUFF_ARMOR):  # an amber hex shell turning slowly
            pts = [(cx + math.cos(t * 0.02 + i * math.pi / 3) * R * 1.05, cy + math.sin(t * 0.02 + i * math.pi / 3) * R * 1.05) for i in range(6)]
            wd.polygon(canvas, (255, 170, 60), pts, 2)
            wd.polygon(canvas, (255, 214, 120), [(cx + (x - cx) * 0.8, cy + (y - cy) * 0.8) for x, y in pts], 1)
        if f.has(BUFF_GUARD):  # a green bubble with a bright highlight
            glow((110, 255, 160), R * 1.05, 34)
            wd.arc(canvas, (230, 255, 240), (cx - R * 0.8, cy - R * 0.8, R * 1.6, R * 1.6), 2.4, 3.6, 2)
        if f.has(BUFF_POWER):  # a pulsing orange glow with embers rising off the shoulders
            glow((255, 120, 70), R * (1.0 + 0.06 * math.sin(t * 0.12)), 28, 1)
            if t % 5 == 0:
                self.fx.burst(cx + self.rng.uniform(-8, 8), box.top + 6, (255, 170, 80), 1, 1.0, angle=-math.pi / 2, spread=0.6, life=(14, 24))
        if f.has(BUFF_HASTE):  # speed lines trailing behind
            for i, dy in enumerate((-14, -2, 10)):
                ln = 12 + 6 * ((t // 4 + i) % 3)
                wd.line(canvas, (255, 240, 130), (cx - f.facing * (10 + ln), cy + dy), (cx - f.facing * 10, cy + dy), 1)
        if f.has(BUFF_CANARY):  # three little yellow birds circling
            for i in range(3):
                a = t * 0.07 + i * 2.09
                wd.circle(canvas, (255, 224, 70), (cx + math.cos(a) * R * 0.95, cy + math.sin(a) * R * 0.5 - 6), 2.2)
                wd.circle(canvas, (255, 150, 50), (cx + math.cos(a) * R * 0.95 + 2, cy + math.sin(a) * R * 0.5 - 6), 1)
        if f.has(BUFF_THROTTLED):  # a grey-blue slowdown ring and chain links sagging at the feet
            wd.ellipse(canvas, (150, 160, 200), (cx - R, f.y - 6, R * 2, 12), 2)
            for i in range(6):
                a = t * 0.02 + i * math.pi / 3
                wd.circle(canvas, (200, 206, 230), (cx + math.cos(a) * R, f.y + math.sin(a) * 3), 1.6)
        # one icon per running power-up above the head, each with a ring that drains as it runs out
        active = [(b, k) for b, k in BUFF_ITEM.items() if f.has(b)]
        for i, (buff, key) in enumerate(active):
            x = cx + (i - (len(active) - 1) / 2) * 17
            y = box.top - 34
            frac = f.buffs[buff] / max(1, f.buff_total.get(buff, f.buffs[buff]))
            draw_icon(canvas, key, x, y, 6.5)
            wd.arc(canvas, (255, 255, 255), (x - 8.5, y - 8.5, 17, 17), -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, 2)

    def _draw_fighter(self, canvas: pygame.Surface, f: Fighter) -> None:
        if not f.alive:
            return
        box = f.hurtbox
        sprites = sprite_set(f.stats.name, self.variants[f.slot])  # mirror matches already got distinct schemes
        if sprites is not None:
            anim, idx = pick_frame(f)
            img = sprites.get(anim, idx, f.facing, f.scale)
            fx, fy = sprites.feet
            pos = (round(f.x * RS - fx * f.scale), round(f.y * RS - fy * f.scale))
            self._draw_ghosts(canvas, f, img, pos)
            if f.state == "hurt" and f.anim_frame < 6:  # a brief steady brightening on impact that fades out (no flicker)
                img = img.copy()
                lift = max(0, 120 - f.anim_frame * 22)
                img.fill((lift, lift, lift), special_flags=pygame.BLEND_RGB_ADD)
            if f.invuln > 0:  # respawn protection: a slow shimmer rather than blinking out
                img = img.copy()
                img.set_alpha(int(200 + 55 * math.sin(self.frame * 0.18)))
            canvas.blit(img, pos)
        else:
            wd.rect(canvas, f.stats.color, box)
        if f.shielding:
            r = int((18 + 12 * f.shield_hp / 60) * RS)
            bubble = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (120, 220, 255, 70), (r, r), r)
            pygame.draw.circle(bubble, (180, 240, 255, 200), (r, r), r, 2 * RS)
            canvas.blit(bubble, (box.centerx * RS - r, box.centery * RS - r))
        self._draw_buffs(canvas, f)
        hb = f.active_hitbox()
        if hb is not None and self.debug:
            wd.rect(canvas, (255, 240, 120), hb, 1)
        if self.debug:
            wd.rect(canvas, (0, 255, 0), box, 1)
            label = self.font.render(f"{f.state} {f.move_frame}", False, (255, 255, 255))
            canvas.blit(label, ((box.x - 10) * RS, (box.y - 16) * RS))
        self._draw_tag(canvas, f)
        if f.callout_timer > 0:
            alpha = min(255, f.callout_timer * 14)  # fades out over the last ~18 frames
            text = self.callout_font.render(f.callout, False, (255, 255, 255))
            shadow = self.callout_font.render(f.callout, False, (16, 12, 28))
            text.set_alpha(alpha)
            shadow.set_alpha(alpha)
            pos = (box.centerx * RS - text.get_width() // 2, (box.top - 30 - (CALLOUT_FRAMES - f.callout_timer) // 10) * RS)
            canvas.blit(shadow, (pos[0] + RS, pos[1] + RS))
            canvas.blit(text, pos)

    def _draw_ghosts(self, canvas: pygame.Surface, f: Fighter, img: pygame.Surface, pos: tuple[int, int]) -> None:
        """Fading afterimages behind a fighter who is dashing, blinking, rising or flying: smooth, not strobing."""
        ghosts = self.ghosts[f.slot]
        m = f.move
        fast = (m is not None and (m.dash or m.blink or m.rise) and f.state == "attack") or \
            (f.state == "hurt" and math.hypot(f.vx, f.vy) > 9)
        if fast and self.frame % 2 == 0 and (not ghosts or ghosts[-1][3] != self.frame):
            tint = img.copy()
            c = self.colors[f.slot]
            tint.fill((c[0] // 3, c[1] // 3, c[2] // 3), special_flags=pygame.BLEND_RGB_ADD)
            ghosts.append([tint, pos[0], pos[1], self.frame])
            del ghosts[:-4]
        ghosts[:] = [g for g in ghosts if self.frame - g[3] < 14]
        for surf, gx, gy, born in ghosts:
            surf.set_alpha(max(0, 120 - (self.frame - born) * 9))
            canvas.blit(surf, (gx, gy))

    def _draw_tag(self, canvas: pygame.Surface, f: Fighter) -> None:
        """A small marker over the fighter; its shape differs per player so color is never the only cue."""
        color = self.colors[f.slot]
        label = "CPU" if not self.human[f.slot] else f"P{f.slot + 1}"
        text = self.tag_font.render(label, False, color)
        total = text.get_width() + 10 * RS
        x = f.hurtbox.centerx * RS - total // 2
        y = (f.hurtbox.top - 12) * RS
        canvas.blit(text, (x, y))
        mx, my = x + text.get_width() + 3 * RS, y + 3 * RS
        if f.slot == 0:
            pygame.draw.polygon(canvas, color, [(mx, my), (mx + 7 * RS, my), (mx + 3 * RS, my + 6 * RS)])
        else:
            pygame.draw.rect(canvas, color, (mx, my, 6 * RS, 6 * RS))

    def _draw_combo(self, canvas: pygame.Surface) -> None:
        for slot, (n, t, _) in self.combos.items():
            if n < 2:
                continue
            x = 26 if slot == 0 else WORLD_W - 26 - 250
            pop = 1.0 + 0.25 * max(0, t - (COMBO_SHOW - 6)) / 6  # a quick pop when the count goes up, then steady
            text = ui.scale_surface(self.big.render(f"{n} HITS", False, (255, 214, 90)), pop)
            canvas.blit(text, (x * RS, (WORLD_H - 110) * RS - pygame.Surface.get_height(text) // 2))

    def _draw_hud(self, canvas: pygame.Surface) -> None:
        self._draw_combo(canvas)
        for f in self.fighters:
            color = self.colors[f.slot]
            x = 26 if f.slot == 0 else WORLD_W - 26 - 250
            panel = pygame.Rect(x * RS, (WORLD_H - 82) * RS, 250 * RS, 66 * RS)
            ui.window(canvas, panel, accent=color)
            # portrait: head and shoulders from the idle frame
            sprites = sprite_set(f.stats.name)
            box = pygame.Rect(panel.x + 4 * RS, panel.y + 4 * RS, 56 * RS, 58 * RS)
            pygame.draw.rect(canvas, (24, 30, 56), box)
            if sprites is not None:
                img = sprites.get("idle", 0, 1 if f.slot == 0 else -1)
                canvas.set_clip(box)
                fx, fy = sprites.feet
                canvas.blit(img, (box.x + box.w // 2 - fx, box.y - (fy - 62 * RS)))
                canvas.set_clip(None)
            # damage meter, severity-colored, pulses when hit
            font = self.pct_pulse if self.hud_pulse[f.slot] else self.pct_font
            num = font.render(str(int(f.percent)), False, damage_color(f.percent))
            canvas.blit(font.render(str(int(f.percent)), False, (16, 12, 28)), (panel.x + 68 * RS, panel.y + 5 * RS))
            canvas.blit(num, (panel.x + 66 * RS, panel.y + 3 * RS))
            canvas.blit(self.font.render("%", False, damage_color(f.percent)),
                        (panel.x + 66 * RS + num.get_width() + 2 * RS, panel.y + 30 * RS))
            name = self.font.render(f.stats.name, False, (210, 214, 235))
            canvas.blit(name, (panel.right - name.get_width() - 8 * RS, panel.y + 6 * RS))
            for i in range(min(max(f.stocks, 0), 5)):  # (training keeps 99 stocks; never draw more than five icons)
                cx, cy = panel.x + (150 + i * 22) * RS, panel.bottom - 14 * RS
                if f.slot == 0:
                    pygame.draw.polygon(canvas, color, [(cx - 6 * RS, cy + 5 * RS), (cx + 6 * RS, cy + 5 * RS), (cx, cy - 6 * RS)])
                else:
                    pygame.draw.rect(canvas, color, (cx - 5 * RS, cy - 5 * RS, 10 * RS, 10 * RS))
        secs = max(self.time_left // FPS, 0)
        t = self.big.render(f"{secs // 60}:{secs % 60:02d}", False, (230, 230, 240))
        canvas.blit(t, ((PIX_W - t.get_width()) // 2, 14 * RS))

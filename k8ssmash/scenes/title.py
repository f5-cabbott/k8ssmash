from __future__ import annotations

import math
import random

import pygame

from k8ssmash import logo, ui
from k8ssmash.ui import pd
from k8ssmash.backdrops import dither_gradient
from k8ssmash.config import CANVAS_H, CANVAS_W, FPS, PIX_H, PIX_W, RS
from k8ssmash.particles import Particles
from k8ssmash.roster import roster
from k8ssmash.scenes.base import Scene
from k8ssmash.sprites import sprite_set

KUBE_BLUE = (50, 108, 229)
CYAN = (0, 226, 255)
ATTRACT_AFTER = 45 * FPS
HORIZON = 226
FLOOR_Y = 318  # where the parade's feet land

_sky: pygame.Surface | None = None


def draw_helm(canvas: pygame.Surface, cx: int, cy: int, r: int, angle: float, color) -> None:
    """Seven-spoke wheel (the Kubernetes logo shape) with a soft neon glow."""
    for k, w in ((8, 1), (5, 2), (2, 4)):  # glow rings, dim to bright
        pd.circle(canvas, tuple(int(c * (0.18 + 0.12 * (8 - k))) for c in color), (cx, cy), r + k, w)
    pd.circle(canvas, color, (cx, cy), r, 3)
    pd.circle(canvas, (255, 255, 255), (cx, cy), r // 4)
    pd.circle(canvas, color, (cx, cy), r // 4, 2)
    for i in range(7):
        a = angle + i * 2 * math.pi / 7
        ex, ey = cx + math.cos(a) * (r + 7), cy + math.sin(a) * (r + 7)
        pd.line(canvas, color, (cx + math.cos(a) * r // 4, cy + math.sin(a) * r // 4), (ex, ey), 3)
        pd.circle(canvas, (255, 255, 255), (int(ex), int(ey)), 3)
        pd.circle(canvas, color, (int(ex), int(ey)), 3, 1)


class Runner:
    """One fighter in the parade: runs along the floor, leaps now and then, and turns around at the edges."""

    def __init__(self, name: str, rng: random.Random, index: int):
        self.name = name
        self.sprites = sprite_set(name)
        self.direction = 1 if index % 2 == 0 else -1
        self.x = rng.uniform(-40, CANVAS_W + 40)
        self.speed = rng.uniform(1.5, 2.5)
        self.phase = rng.randint(0, 7)
        self.next_jump = rng.randint(40, 200)
        self.jump_t = -1
        self.rng = rng

    def update(self, frame: int, fx: Particles) -> None:
        self.x += self.direction * self.speed
        if self.x > CANVAS_W + 70:
            self.direction = -1
        elif self.x < -70:
            self.direction = 1
        if self.jump_t >= 0:
            self.jump_t += 1
            if self.jump_t >= 42:
                self.jump_t = -1
                fx.dust(self.x, FLOOR_Y, 0.6)
                self.next_jump = frame + self.rng.randint(90, 260)
        elif frame >= self.next_jump:
            self.jump_t = 0
            fx.dust(self.x, FLOOR_Y, 0.3)
        elif frame % 10 == self.phase % 10:
            fx.dust(self.x - self.direction * 10, FLOOR_Y, 0.1)

    def draw(self, canvas: pygame.Surface, frame: int) -> None:
        if self.sprites is None:
            return
        lift = 0.0
        if self.jump_t >= 0:
            u = self.jump_t / 42
            lift = math.sin(u * math.pi) * 36
            anim, idx = ("jump", 0 if u < 0.25 else 1) if u < 0.6 else ("fall", 0)
        else:
            anim, idx = "run", (frame * 20 // 60 + self.phase) % 12
        img = self.sprites.get(anim, idx, self.direction)
        ui.blit_sprite(canvas, img, int(self.x), int(FLOOR_Y - lift), self.sprites.feet)
TAGLINES = ["PODS VS. CHAOS", "kubectl apply -f fight.yaml", "HIGH AVAILABILITY, LOW HP", "0/1 NODES ARE AVAILABLE TO SMASH",
            "NOW SCHEDULING: VIOLENCE", "REPLICAS: 2   DESIRED: 1", "CRASHLOOPBACKOFF? NOT TODAY"]
TAGLINE_FRAMES = 4 * FPS
MENU = [("VERSUS", "versus"), ("TRAINING", "training"), ("HOW TO PLAY", "tutorial"), ("LEADERBOARD", "scores"),
        ("SETTINGS", "settings")]
_logo: dict | None = None


def _logo_art() -> dict:
    """The logo letters, built once: K8S in tube blue over a big hot SMASH."""
    global _logo
    if _logo is None:
        _logo = {"top": logo.word("K8S", 78 * RS, logo.TUBE_BLUE, 7 * RS, gap=10 * RS),
                 "main": logo.word("SMASH", 108 * RS, logo.HOT, 9 * RS, gap=8 * RS)}
    return _logo


def _burst(canvas: pygame.Surface, cx: float, cy: float, r: float, angle: float) -> None:
    """A slowly turning impact star behind the logo: dark, wide spikes so it frames the letters without competing."""
    for scale, color in ((1.0, (52, 24, 58)), (0.78, (86, 36, 56)), (0.54, (122, 54, 52))):
        pts = []
        for i in range(28):
            a = angle + i * math.pi / 14
            rr = r * scale * (1.0 if i % 2 == 0 else 0.62)
            pts.append((cx + math.cos(a) * rr * 1.6, cy + math.sin(a) * rr * 0.62))
        pygame.draw.polygon(canvas, color, [(round(x), round(y)) for x, y in pts])


class Title(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.frame = 0
        self.row = 0
        self._select_since: int | None = None
        self._select_clean = True
        app.audio.music("splash")
        self.font = ui.UIFont(22)
        self.menu_font = ui.UIFont(18)
        self.small = ui.UIFont(13)
        self.tag_font = ui.UIFont(15)
        self.rng = random.Random(7)
        self.fx = Particles(seed=3, scale=ui.SCALE)
        self.parade = [Runner(f.name, self.rng, i) for i, f in enumerate(roster())]
        _logo_art()

    def update(self) -> None:
        from k8ssmash.scenes.attract import Attract

        self.frame += 1
        for runner in self.parade:
            runner.update(self.frame, self.fx)
        if self.frame % 5 == 0:
            self.fx.confetti(self.rng.uniform(20, CANVAS_W - 20), -6, 1)
        self.fx.update()
        players = self.app.input.players
        self._check_leaderboard_tap()
        for inp in players:
            if "UP" in inp.pressed:
                self.row = (self.row - 1) % len(MENU)
                self.app.audio.play("menu_move")
            if "DOWN" in inp.pressed:
                self.row = (self.row + 1) % len(MENU)
                self.app.audio.play("menu_move")
        go = any("SPECIAL" in p.pressed for p in players)  # A picks the highlighted row; START is not a menu button
        if go:
            self.app.audio.play("menu_select")
            self._enter(MENU[self.row][1])
        elif self.app.idle_frames >= ATTRACT_AFTER:
            self.app.set_scene(Attract(self.app))

    def _enter(self, choice: str) -> None:
        from k8ssmash.scenes.scoreboard import HighScores
        from k8ssmash.scenes.select import CharacterSelect
        from k8ssmash.scenes.settings import Settings

        if choice == "versus":
            self.app.set_scene(CharacterSelect(self.app))
        elif choice == "training":
            self.app.set_scene(CharacterSelect(self.app, training=True))
        elif choice == "tutorial":
            from k8ssmash.scenes.tutorial import Tutorial

            self.app.set_scene(Tutorial(self.app))
        elif choice == "scores":
            self.app.set_scene(HighScores(self.app, on_done=self.app.go_title))
        else:
            self.app.set_scene(Settings(self.app))

    def _check_leaderboard_tap(self) -> None:
        """A quick tap-and-release of SELECT opens the leaderboard (SELECT held with START is the test combo)."""
        players = self.app.input.players
        if any("START" in p.held or "START" in p.pressed for p in players):
            self._select_clean = False
        if any("SELECT" in p.pressed for p in players):
            self._select_since, self._select_clean = self.frame, not any("START" in p.held for p in players)
        if any("SELECT" in p.released for p in players) and self._select_since is not None:
            quick = self.frame - self._select_since < 40
            if quick and self._select_clean:
                self._enter("scores")
            self._select_since = None

    # --- drawing -------------------------------------------------------------------------
    def _background(self, canvas: pygame.Surface) -> None:
        global _sky
        if _sky is None:
            _sky = dither_gradient(PIX_W, PIX_H, [(0, (4, 6, 22)), (0.4, (8, 20, 70)), (0.6, (14, 70, 150)),
                                                        (0.63, (90, 220, 255)), (0.64, (4, 8, 26)), (1, (2, 4, 14))], bands=24)
        pd.blit(canvas, _sky, (0, 0))
        t = self.frame
        for k in range(-18, 19):  # the Grid: lines converging on the horizon
            bx = CANVAS_W / 2 + k * 52
            pd.line(canvas, (0, int(70 - abs(k) * 2.2), int(110 - abs(k) * 3)), (CANVAS_W / 2 + k * 2, HORIZON), (bx, CANVAS_H), 1)
        for i in range(12):  # cross lines roll toward the viewer
            u = ((i + (t * 0.014) % 1.0) / 12) ** 2.1
            y = HORIZON + (CANVAS_H - HORIZON) * u
            pd.line(canvas, (0, int(60 + 110 * u), int(90 + 150 * u)), (0, int(y)), (CANVAS_W, int(y)), 1)
        for n, (depth, speed, color, direction) in enumerate(((0.12, 3.6, CYAN, 1), (0.3, 4.6, (255, 140, 40), -1))):
            y = int(HORIZON + (CANVAS_H - HORIZON) * depth ** 2.1)
            x = (t * speed * direction + 200 * n) % (CANVAS_W + 300) - 150
            for k in range(8):  # a light-cycle's fading ribbon
                tx = x - direction * k * 12
                pd.line(canvas, tuple(int(c * (1 - k * 0.12)) for c in color), (tx, y), (tx - direction * 12, y), 2)
            pd.rect(canvas, (255, 255, 255), (int(x) - 4, y - 3, 8, 4))

    def _draw_word(self, canvas: pygame.Surface, letters, cx: float, y: float, base_frame: int, wave: float) -> None:
        """Letters drop in one after another with a bounce, then settle into a gentle wave."""
        width = letters[-1][1]
        x0 = cx - width / 2
        for i, (img, dx) in enumerate(letters[:-1]):
            t = self.frame - (base_frame + i * 6)
            if t < 0:
                continue
            drop = 220 * RS * math.exp(-t * 0.13) * abs(math.cos(t * 0.27))
            bob = math.sin(self.frame * 0.08 + i * 0.7) * wave * RS if t > 40 else 0
            canvas.blit(img, (round(x0 + dx), round(y - drop + bob)))

    def _shine(self, canvas: pygame.Surface, rect: pygame.Rect) -> None:
        """Every few seconds a soft diagonal sheen slides across the logo (a smooth sweep, never a flash)."""
        cycle = (self.frame - 120) % (6 * FPS)
        if self.frame < 120 or cycle > 50:
            return
        x = rect.x - 60 * RS + cycle / 50 * (rect.w + 120 * RS)
        band = pygame.Surface(rect.size, pygame.SRCALPHA)
        for k in range(26 * RS):
            a = 70 - abs(k - 13 * RS) * 5 // RS
            if a > 0:
                pygame.draw.line(band, (a, a, a), (x - rect.x + k, 0), (x - rect.x + k - 40 * RS, rect.h))
        canvas.blit(band, rect.topleft, special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, canvas: pygame.Surface) -> None:
        self._background(canvas)
        t = self.frame
        cx = canvas.get_width() / 2
        name = self.app.cfg.event_name.strip().upper()
        if name:  # an optional line for your own event; blank by default
            event = self.tag_font.render(f"{name} EDITION", False, (255, 215, 90))
            ui.blit_c(canvas, event, 4 + int(math.sin(t * 0.05) * 2))
        art = _logo_art()
        _burst(canvas, cx, 118 * ui.SCALE, 120 * ui.SCALE / 1.6, t * 0.004)
        for runner in sorted(self.parade, key=lambda r: r.speed):
            runner.draw(canvas, t)
        self.fx.draw(canvas)
        # K8S flanked by a pair of counter-rotating helm wheels, then SMASH big underneath
        top_y = 12 * ui.SCALE
        self._draw_word(canvas, art["top"], cx, top_y, 4, 2.0)
        spread = art["top"][-1][1] / 2 + 34 * ui.SCALE
        draw_helm(canvas, round((cx - spread) / ui.SCALE), 38, 13, t * 0.03, CYAN)
        draw_helm(canvas, round((cx + spread) / ui.SCALE), 38, 13, -t * 0.03, (255, 140, 40))
        main_y = 56 * ui.SCALE
        self._draw_word(canvas, art["main"], cx, main_y, 30, 3.0)
        main_w = art["main"][-1][1]
        if t > 100:
            self._shine(canvas, pygame.Rect(round(cx - main_w / 2), round(main_y), main_w, 130 * RS))
        # a ribbon with a changing tagline
        tag = TAGLINES[(t // TAGLINE_FRAMES) % len(TAGLINES)]
        phase = t % TAGLINE_FRAMES
        fade = min(1.0, phase / 20, (TAGLINE_FRAMES - phase) / 20)
        ribbon = pygame.Rect(150, 150, 340, 17)
        pd.rect(canvas, (14, 20, 70), (ribbon.x - 8, ribbon.y + 2, ribbon.w + 16, ribbon.h), border_radius=2)
        pd.polygon(canvas, (14, 20, 70), [(ribbon.x - 8, ribbon.y + 2), (ribbon.x - 18, ribbon.y + 10), (ribbon.x - 8, ribbon.y + 18)])
        pd.polygon(canvas, (14, 20, 70), [(ribbon.right + 8, ribbon.y + 2), (ribbon.right + 18, ribbon.y + 10), (ribbon.right + 8, ribbon.y + 18)])
        pd.rect(canvas, (0, 170, 220), ribbon, border_radius=2)
        pd.rect(canvas, (150, 245, 255), (ribbon.x, ribbon.y, ribbon.w, 2))
        line = ui.fit(tag, tuple(int(255 * (0.25 + 0.75 * fade)) for _ in range(3)), ribbon.w - 16, 14)
        pd.blit(canvas, line, (ribbon.centerx - line.get_width() / 2, ribbon.y + 1))
        self._draw_menu(canvas)
        hint = self.small.render("UP / DOWN choose      A select", False, (130, 146, 210))
        ui.blit_c(canvas, hint, 340)

    def _draw_menu(self, canvas: pygame.Surface) -> None:
        w, row_h = 190, 19
        x = (canvas.get_width() / ui.SCALE - w) / 2
        y0 = 172
        plate = pygame.Surface((round(w * ui.SCALE), round(row_h * len(MENU) * ui.SCALE + 8)), pygame.SRCALPHA)
        plate.fill((4, 8, 30, 170))
        canvas.blit(plate, (round(x * ui.SCALE), round((y0 - 3) * ui.SCALE)))
        pd.rect(canvas, (0, 200, 255), (x, y0 - 3, w, row_h * len(MENU) + 5), 1, border_radius=3)
        for i, (label, _) in enumerate(MENU):
            y = y0 + i * row_h
            active = i == self.row
            if active:
                pulse = 0.5 + 0.5 * math.sin(self.frame * 0.12)
                pd.rect(canvas, (40 + int(20 * pulse), 80 + int(30 * pulse), 190), (x + 4, y, w - 8, row_h - 2), border_radius=3)
                pd.rect(canvas, (255, 224, 90), (x + 4, y, w - 8, row_h - 3), 1, border_radius=3)
                bob = math.sin(self.frame * 0.2) * 2
                pd.polygon(canvas, (255, 224, 90), [(x + 12 + bob, y + 3), (x + 12 + bob, y + 13), (x + 20 + bob, y + 8)])
                pd.polygon(canvas, (255, 224, 90), [(x + w - 12 - bob, y + 3), (x + w - 12 - bob, y + 13), (x + w - 20 - bob, y + 8)])
            text = self.menu_font.render(label, False, (255, 255, 255) if active else (160, 176, 226))
            pd.blit(canvas, text, (x + (w - text.get_width()) / 2, y + 1))

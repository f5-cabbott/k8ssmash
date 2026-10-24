from __future__ import annotations

import math
import random

import pygame

from k8ssmash import ui
from k8ssmash.backdrops import dither_gradient
from k8ssmash.config import CANVAS_H, CANVAS_W, FPS
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
        pygame.draw.circle(canvas, tuple(int(c * (0.18 + 0.12 * (8 - k))) for c in color), (cx, cy), r + k, w)
    pygame.draw.circle(canvas, color, (cx, cy), r, 3)
    pygame.draw.circle(canvas, (255, 255, 255), (cx, cy), r // 4)
    pygame.draw.circle(canvas, color, (cx, cy), r // 4, 2)
    for i in range(7):
        a = angle + i * 2 * math.pi / 7
        ex, ey = cx + math.cos(a) * (r + 7), cy + math.sin(a) * (r + 7)
        pygame.draw.line(canvas, color, (cx + math.cos(a) * r // 4, cy + math.sin(a) * r // 4), (ex, ey), 3)
        pygame.draw.circle(canvas, (255, 255, 255), (int(ex), int(ey)), 3)
        pygame.draw.circle(canvas, color, (int(ex), int(ey)), 3, 1)


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
            anim, idx = "run", (frame * 16 // 60 + self.phase) % 8
        img = self.sprites.get(anim, idx, self.direction)
        fx, fy = self.sprites.feet
        canvas.blit(img, (int(self.x) - fx, int(FLOOR_Y - lift) - fy))


class Title(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.frame = 0
        self._select_since: int | None = None
        self._select_clean = True
        self._shield_held = 0
        app.audio.music("splash")
        self.huge = ui.Font(92)
        self.big = ui.Font(36)
        self.font = ui.Font(22)
        self.small = ui.Font(28)
        self.rng = random.Random(7)
        self.fx = Particles(seed=3)
        self.parade = [Runner(f.name, self.rng, i) for i, f in enumerate(roster())]

    def update(self) -> None:
        from k8ssmash.scenes.attract import Attract
        from k8ssmash.scenes.select import CharacterSelect

        self.frame += 1
        for runner in self.parade:
            runner.update(self.frame, self.fx)
        if self.frame % 5 == 0:
            self.fx.confetti(self.rng.uniform(20, CANVAS_W - 20), -6, 1)
        self.fx.update()
        # START with SELECT held is the controller-test combo, not "start game".
        starting = any("START" in p.pressed and "SELECT" not in p.held for p in self.app.input.players)
        self._check_leaderboard_tap()
        self._shield_held = self._shield_held + 1 if any("SHIELD" in p.held for p in self.app.input.players) else 0
        if self._shield_held >= 40:  # a deliberate hold of L/R, so nobody opens it by accident
            from k8ssmash.scenes.settings import Settings

            self.app.audio.play("menu_select")
            self.app.set_scene(Settings(self.app))
        elif starting:
            self.app.audio.play("menu_select")
            self.app.set_scene(CharacterSelect(self.app))
        elif any("SPECIAL" in p.pressed for p in self.app.input.players):
            self.app.audio.play("menu_select")
            self.app.set_scene(CharacterSelect(self.app, training=True))
        elif self.app.idle_frames >= ATTRACT_AFTER:
            self.app.set_scene(Attract(self.app))

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
                from k8ssmash.scenes.scoreboard import HighScores

                self.app.set_scene(HighScores(self.app, on_done=self.app.go_title))
            self._select_since = None

    # --- drawing -------------------------------------------------------------------------
    def _background(self, canvas: pygame.Surface) -> None:
        global _sky
        if _sky is None:
            _sky = dither_gradient(CANVAS_W, CANVAS_H, [(0, (4, 6, 22)), (0.4, (8, 20, 70)), (0.6, (14, 70, 150)),
                                                        (0.63, (90, 220, 255)), (0.64, (4, 8, 26)), (1, (2, 4, 14))], bands=24)
        canvas.blit(_sky, (0, 0))
        t = self.frame
        for k in range(-18, 19):  # the Grid: lines converging on the horizon
            bx = CANVAS_W / 2 + k * 52
            pygame.draw.line(canvas, (0, int(70 - abs(k) * 2.2), int(110 - abs(k) * 3)), (CANVAS_W / 2 + k * 2, HORIZON), (bx, CANVAS_H), 1)
        for i in range(12):  # cross lines roll toward the viewer
            u = ((i + (t * 0.014) % 1.0) / 12) ** 2.1
            y = HORIZON + (CANVAS_H - HORIZON) * u
            pygame.draw.line(canvas, (0, int(60 + 110 * u), int(90 + 150 * u)), (0, int(y)), (CANVAS_W, int(y)), 1)
        for n, (depth, speed, color, direction) in enumerate(((0.12, 3.6, CYAN, 1), (0.3, 4.6, (255, 140, 40), -1))):
            y = int(HORIZON + (CANVAS_H - HORIZON) * depth ** 2.1)
            x = (t * speed * direction + 200 * n) % (CANVAS_W + 300) - 150
            for k in range(8):  # a light-cycle's fading ribbon
                tx = x - direction * k * 12
                pygame.draw.line(canvas, tuple(int(c * (1 - k * 0.12)) for c in color), (tx, y), (tx - direction * 12, y), 2)
            pygame.draw.rect(canvas, (255, 255, 255), (int(x) - 4, y - 3, 8, 4))

    def draw(self, canvas: pygame.Surface) -> None:
        self._background(canvas)
        t = self.frame
        event = self.small.render(self.app.cfg.event_name.upper() + " EDITION", False, (255, 215, 90))
        canvas.blit(event, ((CANVAS_W - event.get_width()) // 2, 8 + int(math.sin(t * 0.05) * 2)))
        draw_helm(canvas, CANVAS_W // 2, 98, 40, t * 0.025, CYAN)
        for runner in sorted(self.parade, key=lambda r: r.speed):
            runner.draw(canvas, t)
        self.fx.draw(canvas)
        # the logo: every letter bobs on its own beat, like a wave rolling through
        text = "K8S SMASH"
        glyphs = [self.huge.render(c, False, (255, 255, 255)) for c in text]
        width = sum(g.get_width() for g in glyphs) - 6
        x, base = (CANVAS_W - width) // 2, 124
        for i, g in enumerate(glyphs):
            bob = math.sin(t * 0.13 + i * 0.55) * 4
            canvas.blit(g, (x, base + bob))
            x += g.get_width() - 1
        sub = self.big.render("PODS  VS.  CHAOS", False, CYAN)
        canvas.blit(sub, ((CANVAS_W - sub.get_width()) // 2, base + 84 + int(math.sin(t * 0.1) * 2)))
        pulse = 1.0 + 0.07 * math.sin(t * 0.14)  # a smooth pulse, not a blink
        press = self.big.render("PRESS START", False, (255, 224, 90))
        press = pygame.transform.smoothscale(press, (int(press.get_width() * pulse), int(press.get_height() * pulse)))
        canvas.blit(press, ((CANVAS_W - press.get_width()) // 2, 266 - press.get_height() // 2))
        hint = self.font.render("A: training     SELECT: leaderboard     hold L/R: settings", False, (130, 146, 210))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 336))

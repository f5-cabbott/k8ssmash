from __future__ import annotations

import math

import pygame

from k8ssmash import ui
from k8ssmash.ui import pd
from k8ssmash.config import CANVAS_W, FPS, WORLD_H, WORLD_W
from k8ssmash.particles import Particles
from k8ssmash.sprites import sprite_set
from k8ssmash.scenes.base import Scene
from k8ssmash.palette import player_colors

TIMEOUT = 20 * FPS
LOCK = 45


class Results(Scene):
    def __init__(self, app, winner: int, summary: list[dict], human: list[bool] | None = None):
        super().__init__(app)
        self.winner = winner
        self.summary = summary
        self.frame = 0
        human = human if human is not None else app.last_match[1]
        self.prompts = app.runs.record(winner, human, [row["kos"] for row in summary],
                                       [row["name"] for row in summary])
        self.new_runs: set[str] = set()
        self.ranks: dict[str, int | None] = {}
        app.audio.music("results", loop=False)
        self.huge = ui.UIFont(60)
        self.big = ui.UIFont(30)
        self.font = ui.UIFont(22)
        self.small = ui.UIFont(18)
        self.fx = Particles(seed=5, scale=ui.SCALE)

    def update(self) -> None:
        from k8ssmash.scenes.battle import Battle
        from k8ssmash.scenes.select import CharacterSelect

        self.frame += 1
        if self.winner >= 0 and self.frame % 3 == 0:  # confetti rains over the winner
            self.fx.confetti(170 + self.winner * 300, -4, 1, width=140)
        self.fx.update()
        if self.app.idle_frames >= TIMEOUT:
            self.app.go_title()
        elif self.frame > LOCK:
            if self.prompts and self.app.input.any_pressed("START"):
                self._enter_name(self.prompts.pop(0))
            elif self.app.input.any_pressed("START"):
                cursor, human, stage_idx = self.app.last_match
                from k8ssmash.roster import roster
                from k8ssmash.stage import STAGES
                r = roster()
                self.app.set_scene(Battle(self.app, [r[cursor[0]], r[cursor[1]]], stage=STAGES[stage_idx](),
                                          human=human))
            elif self.app.input.any_pressed("SELECT"):
                self.app.set_scene(CharacterSelect(self.app))
            elif self.app.input.any_pressed("SPECIAL"):
                self.app.audio.play("menu_move")
                self.app.go_title()  # A: leave to the main menu

    def _enter_name(self, prompt) -> None:
        from k8ssmash.scenes.scoreboard import HighScores, NameEntry

        def done(name: str) -> None:
            ranks = self.app.runs.commit_name(prompt.slot, name)
            self.new_runs.add(self.app.runs.runs[prompt.slot].id)
            self.frame = LOCK  # back on the results screen, ready for START / SELECT
            self.app.idle_frames = 0
            self.app.set_scene(HighScores(self.app, on_done=lambda: self.app.set_scene(self),
                                          highlight=set(self.new_runs)))

        self.app.set_scene(NameEntry(self.app, prompt, done))

    def draw(self, canvas: pygame.Surface) -> None:
        colors = player_colors(self.app.cfg)
        pd.blit(canvas, self._backdrop(), (0, 0))
        text = "DRAW" if self.winner == -1 else f"P{self.winner + 1} WINS!"
        color = (255, 255, 255) if self.winner == -1 else colors[self.winner]
        bounce = int(math.sin(self.frame * 0.12) * 3)
        surf = self.huge.render(text, False, color)
        ui.blit_c(canvas, surf, 6 + bounce)
        for slot, row in enumerate(self.summary):
            cx = 170 + slot * 300
            won = slot == self.winner
            alt = len({r["name"] for r in self.summary}) == 1 and slot == 1
            sprites = sprite_set(row["name"], alt)
            pd.line(canvas, (0, 226, 255), (cx - 84, 217), (cx + 84, 217), 2)  # the podium plate
            pd.line(canvas, (0, 90, 120), (cx - 84, 219), (cx + 84, 219), 1)
            if sprites is not None:
                if won or self.winner == -1:
                    idx = (self.frame * 7 // 60) % 4
                    anim, hop = "win", (0, -16, -22, -4)[idx]
                else:
                    anim, idx, hop = "lose", 0, 0
                img = sprites.get(anim, idx, 1 if slot == 0 else -1, 3.0)  # whole-number pixel scale: stays crisp
                fx, fy = sprites.feet
                ui.blit_sprite(canvas, img, cx, 214 + hop, (fx * 3, fy * 3))
            run = self.app.runs.runs[slot]
            if run.streak >= 2:
                t = self.small.render(f"{run.streak} wins in a row!", False, (255, 215, 90))
                pd.blit(canvas, t, (cx - t.get_width() // 2, 64))
            panel = pygame.Rect(cx - 130, 226, 260, 82)
            ui.window_d(canvas, panel, accent=colors[slot])
            pd.blit(canvas, self.big.render(row["name"], False, colors[slot]), (panel.x + 10, panel.y + 4))
            for i, line in enumerate((f"KOs  {row['kos']}", f"Damage dealt  {int(row['damage'])}%", f"Stocks left  {row['stocks']}")):
                pd.blit(canvas, self.small.render(line, False, (226, 230, 250)), (panel.x + 12, panel.y + 30 + i * 15))
        self.fx.draw(canvas)
        if self.prompts:
            who = " & ".join(f"P{p.slot + 1}" for p in self.prompts)
            banner = self.big.render(f"NEW HIGH SCORE!  {who}: press START", False, (255, 215, 90))
            pulse = 1.0 + 0.05 * math.sin(self.frame * 0.15)
            banner = ui.scale_surface(banner, pulse)
            ui.blit_c(canvas, banner, 318 - banner.get_height() // 2)
        if self.frame > LOCK:
            hint = self.small.render("START rematch     SELECT change fighters     A main menu", False, (255, 224, 140))
            ui.blit_c(canvas, hint, 340)
    _bg: pygame.Surface | None = None

    @classmethod
    def _backdrop(cls) -> pygame.Surface:
        if cls._bg is None:
            from k8ssmash.backdrops import dither_gradient
            cls._bg = dither_gradient(WORLD_W, WORLD_H, [(0, (4, 6, 22)), (0.55, (10, 26, 84)), (0.62, (30, 130, 190)),
                                                            (0.64, (4, 8, 26)), (1, (2, 4, 14))], bands=22)
        return cls._bg

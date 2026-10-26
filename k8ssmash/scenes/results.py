from __future__ import annotations

import math

import pygame

from k8ssmash import ui
from k8ssmash.ui import pd
from k8ssmash.config import CANVAS_W, FPS, PIX_H, PIX_W, RS
from k8ssmash.flair import WIN
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
        if 0 <= winner < len(summary):
            app.audio.play("win", fighter=summary[winner]["name"])  # the winner's own fanfare
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
        if self.frame == 70:  # the announcer calls it once the fanfare has settled
            name = self.summary[self.winner]["name"].lower() if 0 <= self.winner < len(self.summary) else None
            self.app.audio.play(f"ann_win_{name}" if name else "ann_draw")
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
            elif self.app.input.any_pressed("SHIELD"):  # L/R: pick the next stage for the rematch
                from k8ssmash.stage import STAGES
                cursor, human, stage_idx = self.app.last_match
                self.app.last_match = (cursor, human, (stage_idx + 1) % len(STAGES))
                self.app.audio.play("menu_move")
            elif self.app.input.any_pressed("JUMP"):  # swap sides: who starts on the left
                cursor, human, stage_idx = self.app.last_match
                self.app.last_match = ([cursor[1], cursor[0]], [human[1], human[0]], stage_idx)
                self.summary = self.summary[::-1]
                self.winner = {0: 1, 1: 0}.get(self.winner, self.winner)
                self.app.audio.play("menu_move")
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
                k = 3.0 / RS  # the same on-screen size as ever; the art underneath is RS times finer
                img = sprites.get(anim, idx, 1 if slot == 0 else -1, k)
                fx, fy = sprites.feet
                ui.blit_sprite(canvas, img, cx, 214 + hop, (fx * k, fy * k))
            run = self.app.runs.runs[slot]
            if run.streak >= 2:
                t = self.small.render(f"{run.streak} wins in a row!", False, (255, 215, 90))
                pd.blit(canvas, t, (cx - t.get_width() // 2, 64))
            panel = pygame.Rect(cx - 130, 226, 260, 98 if won else 84)
            ui.window_d(canvas, panel, accent=colors[slot])
            pd.blit(canvas, self.big.render(row["name"], False, colors[slot]), (panel.x + 10, panel.y + 4))
            lines = (f"KOs  {row['kos']}", f"Damage dealt  {int(row['damage'])}%", f"Stocks left  {row['stocks']}",
                     f"Best combo  {row.get('combo', 0)} hits")
            for i, line in enumerate(lines):
                pd.blit(canvas, self.small.render(line, False, (226, 230, 250)), (panel.x + 12, panel.y + 28 + i * 13))
        if 0 <= self.winner < len(self.summary):
            quote = WIN.get(self.summary[self.winner]["name"], "")
            qx = 170 + self.winner * 300
            q = self.small.render(f"\"{quote}\"", False, (255, 224, 140))
            pd.blit(canvas, q, (qx - q.get_width() // 2, 226 + 82))
        self.fx.draw(canvas)
        if self.prompts:
            who = " & ".join(f"P{p.slot + 1}" for p in self.prompts)
            banner = self.big.render(f"NEW HIGH SCORE!  {who}: press START", False, (255, 215, 90))
            pulse = 1.0 + 0.05 * math.sin(self.frame * 0.15)
            banner = ui.scale_surface(banner, pulse)
            ui.blit_c(canvas, banner, 318 - banner.get_height() // 2)
        if self.frame > LOCK:
            from k8ssmash.stage import STAGES
            stage = STAGES[self.app.last_match[2]]().name
            hint = ui.fit(f"START rematch     L/R stage: {stage}     Y/X swap sides     SELECT fighters     A menu",
                          (255, 224, 140), 620, 15, 9)
            ui.blit_c(canvas, hint, 338)
    _bg: pygame.Surface | None = None

    @classmethod
    def _backdrop(cls) -> pygame.Surface:
        if cls._bg is None:
            from k8ssmash.backdrops import dither_gradient
            cls._bg = dither_gradient(PIX_W, PIX_H, [(0, (4, 6, 22)), (0.55, (10, 26, 84)), (0.62, (30, 130, 190)),
                                                            (0.64, (4, 8, 26)), (1, (2, 4, 14))], bands=22)
        return cls._bg

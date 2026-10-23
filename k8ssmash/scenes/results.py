from __future__ import annotations

import pygame

from k8ssmash import ui
from k8ssmash.config import CANVAS_W, FPS
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
        self.huge = ui.Font(72)
        self.big = ui.Font(34)
        self.font = ui.Font(24)

    def update(self) -> None:
        from k8ssmash.scenes.battle import Battle
        from k8ssmash.scenes.select import CharacterSelect

        self.frame += 1
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
        canvas.fill((14, 18, 34))
        text = "DRAW" if self.winner == -1 else f"P{self.winner + 1} WINS!"
        color = (255, 255, 255) if self.winner == -1 else player_colors(self.app.cfg)[self.winner]
        surf = self.huge.render(text, False, color)
        canvas.blit(surf, ((CANVAS_W - surf.get_width()) // 2, 36))
        for slot, row in enumerate(self.summary):
            x = 70 + slot * 290
            canvas.blit(self.big.render(f"P{slot + 1}  {row['name']}", False, player_colors(self.app.cfg)[slot]), (x, 130))
            canvas.blit(self.font.render(f"KOs: {row['kos']}", False, (220, 220, 235)), (x, 170))
            canvas.blit(self.font.render(f"Damage dealt: {int(row['damage'])}%", False, (220, 220, 235)), (x, 196))
            canvas.blit(self.font.render(f"Stocks left: {row['stocks']}", False, (220, 220, 235)), (x, 222))
        if self.prompts:
            who = " & ".join(f"P{p.slot + 1}" for p in self.prompts)
            banner = self.big.render(f"NEW HIGH SCORE!  {who}: press START", False, (255, 215, 90))
            if (self.frame // 20) % 2 == 0:
                canvas.blit(banner, ((CANVAS_W - banner.get_width()) // 2, 268))
        if self.frame > LOCK:
            hint = self.font.render("START: rematch     SELECT: change fighters", False, (255, 220, 90))
            canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 318))
        for slot, run in enumerate(self.app.runs.runs):
            if run.streak >= 2:
                text = self.font.render(f"{run.streak} wins in a row!", False, (255, 215, 90))
                canvas.blit(text, (70 + slot * 290, 250))

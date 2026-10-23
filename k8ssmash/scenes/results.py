from __future__ import annotations

import pygame

from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.scenes.base import Scene
from k8ssmash.scenes.battle import P_COLORS

TIMEOUT = 20 * FPS
LOCK = 45


class Results(Scene):
    def __init__(self, app, winner: int, summary: list[dict]):
        super().__init__(app)
        self.winner = winner
        self.summary = summary
        self.frame = 0
        self.huge = pygame.font.Font(None, 72)
        self.big = pygame.font.Font(None, 34)
        self.font = pygame.font.Font(None, 24)

    def update(self) -> None:
        from k8ssmash.scenes.battle import Battle
        from k8ssmash.scenes.select import CharacterSelect

        self.frame += 1
        if self.app.idle_frames >= TIMEOUT:
            self.app.go_title()
        elif self.frame > LOCK:
            if self.app.input.any_pressed("START"):
                cursor, human, stage_idx = self.app.last_match
                from k8ssmash.roster import roster
                from k8ssmash.stage import STAGES
                r = roster()
                self.app.set_scene(Battle(self.app, [r[cursor[0]], r[cursor[1]]], stage=STAGES[stage_idx](),
                                          human=human))
            elif self.app.input.any_pressed("SELECT"):
                self.app.set_scene(CharacterSelect(self.app))

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((14, 18, 34))
        text = "DRAW" if self.winner == -1 else f"P{self.winner + 1} WINS!"
        color = (255, 255, 255) if self.winner == -1 else P_COLORS[self.winner]
        surf = self.huge.render(text, False, color)
        canvas.blit(surf, ((CANVAS_W - surf.get_width()) // 2, 36))
        for slot, row in enumerate(self.summary):
            x = 70 + slot * 290
            canvas.blit(self.big.render(f"P{slot + 1}  {row['name']}", False, P_COLORS[slot]), (x, 130))
            canvas.blit(self.font.render(f"KOs: {row['kos']}", False, (220, 220, 235)), (x, 170))
            canvas.blit(self.font.render(f"Damage dealt: {int(row['damage'])}%", False, (220, 220, 235)), (x, 196))
            canvas.blit(self.font.render(f"Stocks left: {row['stocks']}", False, (220, 220, 235)), (x, 222))
        if self.frame > LOCK:
            hint = self.font.render("START: rematch     SELECT: change fighters", False, (255, 220, 90))
            canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 310))

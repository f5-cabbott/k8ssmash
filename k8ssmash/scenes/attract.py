"""Attract mode: CPU vs CPU demo match. Any button returns to the title."""
from __future__ import annotations

import random

from k8ssmash.roster import roster
from k8ssmash.scenes.base import Scene
from k8ssmash.scenes.battle import Battle
from k8ssmash.stage import STAGES


class Attract(Scene):
    def __init__(self, app):
        super().__init__(app)
        stats = random.sample(roster(), 2)
        self.battle = Battle(app, stats, stage=random.choice(STAGES)(), human=[False, False], demo=True)

    def update(self) -> None:
        if self.app.idle_frames < 5 or self.battle.winner is not None:
            # Fresh input, or the demo finished: back to the title.
            if self.app.idle_frames < 5 or self.battle.finished_frames > 120:
                self.app.go_title()
                return
        self.battle.update()

    def draw(self, canvas) -> None:
        self.battle.draw(canvas)
        if (self.battle.frame // 40) % 2 == 0:
            surf = self.battle.big.render("PRESS START", False, (255, 220, 90))
            canvas.blit(surf, ((canvas.get_width() - surf.get_width()) // 2, 40))

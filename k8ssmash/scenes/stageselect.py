"""Stage select: a preview of each arena (with its set piece described) and a Random card. A confirms, B goes back."""
from __future__ import annotations

import random

import pygame

from k8ssmash import ui
from k8ssmash.backdrops import draw_backdrop, draw_platform
from k8ssmash.config import CANVAS_W, FPS, PIX_H, PIX_W
from k8ssmash.scenes.base import Scene
from k8ssmash.stage import STAGES
from k8ssmash.ui import pd

TIMEOUT = 30 * FPS
BLURBS = {
    "Datacenter": ("Server hall", "A rack hot-swaps into the middle of the floor."),
    "Control Plane": ("Core chamber", "Leader election: the crown perch changes sides."),
    "Node Pool": ("Pod bay", "The scheduler lays a bridge across the gap now and then."),
}
_thumbs: dict[int, pygame.Surface] = {}


def thumbnail(idx: int, size: tuple[int, int]) -> pygame.Surface:
    """What the arena looks like in play: backdrop and platforms, rendered once and scaled down smoothly."""
    key = (idx, size)
    if key not in _thumbs:
        stage = STAGES[idx]()
        for p in stage.platforms:  # show set-piece platforms as solid so the preview reads
            if p.schedule:
                p.glow, p.solid = 1.0, True
        full = pygame.Surface((PIX_W, PIX_H))
        draw_backdrop(full, stage.theme, 300, 0.0)
        for p in stage.platforms:
            draw_platform(full, p, stage.theme)
        _thumbs[key] = pygame.transform.smoothscale(full, size)
    return _thumbs[key]


class StageSelect(Scene):
    def __init__(self, app, stats, human, cursor, start_idx: int = 0):
        super().__init__(app)
        self.stats, self.human, self.cursor = stats, human, list(cursor)
        self.row = min(start_idx, len(STAGES) - 1)  # the last row is Random
        self.frame = 0
        self.big = ui.UIFont(26)
        self.font = ui.UIFont(17)
        self.small = ui.UIFont(13)
        app.audio.music("select")

    @property
    def count(self) -> int:
        return len(STAGES) + 1

    def update(self) -> None:
        from k8ssmash.scenes.battle import Battle
        from k8ssmash.scenes.select import CharacterSelect

        self.frame += 1
        if self.app.idle_frames >= TIMEOUT:
            self.app.go_title()
            return
        players = self.app.input.players
        for inp in players:
            if "LEFT" in inp.pressed:
                self.row = (self.row - 1) % self.count
                self.app.audio.play("menu_move")
            if "RIGHT" in inp.pressed:
                self.row = (self.row + 1) % self.count
                self.app.audio.play("menu_move")
        if self.frame < 8:
            return
        if any("SPECIAL" in inp.pressed or "START" in inp.pressed for inp in players):
            idx = random.randrange(len(STAGES)) if self.row == len(STAGES) else self.row
            self.app.audio.play("menu_select")
            self.app.last_match = (list(self.cursor), self.human, idx)
            self.app.set_scene(Battle(self.app, self.stats, stage=STAGES[idx](), human=self.human))
        elif any("ATTACK" in inp.pressed for inp in players):
            self.app.audio.play("menu_move")
            self.app.set_scene(CharacterSelect(self.app))

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((14, 18, 36))
        ui.blit_c(canvas, self.big.render("CHOOSE YOUR ARENA", False, (255, 255, 255)), 8)
        card_w, card_h, gap = 140, 79, 8
        x0 = (CANVAS_W - (self.count * card_w + (self.count - 1) * gap)) // 2
        for i in range(self.count):
            x, y = x0 + i * (card_w + gap), 62
            active = i == self.row
            rect = pygame.Rect(x, y, card_w, card_h)
            if i < len(STAGES):
                canvas.blit(thumbnail(i, (round(card_w * ui.SCALE), round(card_h * ui.SCALE))), (round(x * ui.SCALE), round(y * ui.SCALE)))
                name = STAGES[i]().name
            else:
                pd.rect(canvas, (20, 26, 60), rect)
                q = self.big.render("?", False, (255, 224, 90))
                pd.blit(canvas, q, (rect.centerx - q.get_width() / 2, rect.centery - q.get_height() / 2))
                name = "Random"
            pd.rect(canvas, (255, 224, 90) if active else (90, 104, 170), rect.inflate(4, 4) if active else rect, 2 if active else 1)
            label = self.font.render(name, False, (255, 255, 255) if active else (170, 182, 226))
            pd.blit(canvas, label, (rect.centerx - label.get_width() / 2, rect.bottom + 6))
        panel = pygame.Rect(40, 196, 560, 92)
        ui.window_d(canvas, panel)
        if self.row < len(STAGES):
            name = STAGES[self.row]().name
            kind, piece = BLURBS.get(name, ("", ""))
            pd.blit(canvas, ui.fit(f"{name}: {kind}", (255, 224, 90), panel.w - 24, 20), (panel.x + 12, panel.y + 10))
            pd.blit(canvas, ui.fit("Set piece: " + piece, (210, 220, 245), panel.w - 24, 15), (panel.x + 12, panel.y + 40))
            pd.blit(canvas, ui.fit("It fades in as a ghost first and dims before it leaves. None of it hurts.", (150, 166, 220),
                                   panel.w - 24, 12), (panel.x + 12, panel.y + 64))
        else:
            pd.blit(canvas, ui.fit("Random arena", (255, 224, 90), panel.w - 24, 20), (panel.x + 12, panel.y + 10))
            pd.blit(canvas, ui.fit("Let the scheduler pick.", (210, 220, 245), panel.w - 24, 15), (panel.x + 12, panel.y + 40))
        hint = self.small.render("LEFT / RIGHT choose        A fight        B back to fighters", False, (150, 166, 220))
        ui.blit_c(canvas, hint, 330)

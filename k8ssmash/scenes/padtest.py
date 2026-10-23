"""Controller test screen: shows each player's pad state. Toggle by holding SELECT+START."""
from __future__ import annotations

import pygame

from k8ssmash.config import CANVAS_W
from k8ssmash.scenes.base import Scene

BG = (14, 18, 30)
DIM = (50, 56, 80)
ON = (120, 230, 140)


class ControllerTest(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.font = pygame.font.Font(None, 17)
        self.big = pygame.font.Font(None, 34)

    def update(self) -> None:
        # Pressing JUMP on the pad currently labelled P2 makes it P1 (and swaps the other).
        if "JUMP" in self.app.input.players[1].pressed and self.app.input.pads[1] is not None:
            self.app.input.swap_pads()

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        title = self.big.render("CONTROLLER TEST   (hold SELECT+START to exit)", False, (255, 255, 255))
        canvas.blit(title, ((CANVAS_W - title.get_width()) // 2, 12))
        hint = self.font.render("Press JUMP on a pad labelled P2 to make it P1", False, (150, 160, 200))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 340))
        for slot, player in enumerate(self.app.input.players):
            self._draw_pad(canvas, slot, player.held, 20 + slot * 310)

    def _draw_pad(self, canvas: pygame.Surface, slot: int, held: set[str], x: int) -> None:
        pad = self.app.input.pads[slot]
        name = pad.get_name() if pad else "keyboard only (no pad)"
        canvas.blit(self.big.render(f"P{slot + 1}: {name}", False, (200, 210, 255)), (x, 50))

        def lamp(action: str, cx: int, cy: int, label: str, r: int = 14) -> None:
            on = action in held
            pygame.draw.circle(canvas, ON if on else DIM, (x + cx, 165 + cy), r)
            txt = self.font.render(label, False, (10, 10, 20) if on else (150, 156, 180))
            canvas.blit(txt, (x + cx - txt.get_width() // 2, 165 + cy - txt.get_height() // 2))

        # D-pad
        lamp("UP", 50, -22, "U")
        lamp("DOWN", 50, 22, "D")
        lamp("LEFT", 28, 0, "L")
        lamp("RIGHT", 72, 0, "R")
        # Actions by role
        lamp("JUMP", 195, 0, "JUMP", 22)
        lamp("ATTACK", 245, 30, "ATK", 22)
        lamp("SPECIAL", 245, -30, "SPC", 22)
        lamp("SHIELD", 150, -52, "SHLD", 22)
        lamp("SELECT", 105, 55, "SEL", 16)
        lamp("START", 150, 55, "STA", 16)

        raw = self.app.input.raw_state(slot)
        if raw is None:
            return
        buttons, axes, hat = raw
        lines = [f"buttons down: {buttons or '-'}", f"axes: {axes}  hat: {hat}"]
        for i, line in enumerate(lines):
            canvas.blit(self.font.render(line, False, (180, 190, 220)), (x, 240 + i * 18))

"""Controller test screen: shows each player's pad state. Toggle by holding SELECT+START."""
from __future__ import annotations

import pygame

from k8ssmash import ui
from k8ssmash.ui import pd
from k8ssmash.config import CANVAS_W
from k8ssmash.scenes.base import Scene

BG = (14, 18, 30)
DIM = (50, 56, 80)
ON = (120, 230, 140)


class ControllerTest(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.font = ui.UIFont(17)
        self.big = ui.UIFont(34)
        self._rebind_hold = 0

    def update(self) -> None:
        held = any("SELECT" in p.held and "START" not in p.held for p in self.app.input.players)
        self._rebind_hold = self._rebind_hold + 1 if held else 0
        if self._rebind_hold >= 120:
            from k8ssmash.scenes.rebind import Rebind

            self._rebind_hold = 0
            self.app.push_scene(Rebind(self.app, on_done=self.app.pop_scene))
            return
        # Pressing JUMP on the pad currently labelled P2 makes it P1 (and swaps the other).
        if "JUMP" in self.app.input.players[1].pressed and self.app.input.pads[1] is not None:
            self.app.input.swap_pads()

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        title = self.big.render("CONTROLLER TEST   (hold SELECT+START to exit)", False, (255, 255, 255))
        ui.blit_c(canvas, title, 12)
        hint = self.font.render("JUMP on P2 pad: make it P1      hold SELECT 2s: rebind buttons", False, (150, 160, 200))
        ui.blit_c(canvas, hint, 340)
        for slot, player in enumerate(self.app.input.players):
            self._draw_pad(canvas, slot, player.held, 20 + slot * 310)

    def _draw_pad(self, canvas: pygame.Surface, slot: int, held: set[str], x: int) -> None:
        pad = self.app.input.pads[slot]
        name = pad.get_name() if pad else "keyboard only (no pad)"
        pd.blit(canvas, self.big.render(f"P{slot + 1}: {name}", False, (200, 210, 255)), (x, 50))
        def lamp(action: str, cx: int, cy: int, label: str, r: int = 14) -> None:
            on = action in held
            pd.circle(canvas, ON if on else DIM, (x + cx, 165 + cy), r)
            txt = self.font.render(label, False, (10, 10, 20) if on else (150, 156, 180))
            pd.blit(canvas, txt, (x + cx - txt.get_width() // 2, 165 + cy - txt.get_height() // 2))
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
            pd.blit(canvas, self.font.render(line, False, (180, 190, 220)), (x, 240 + i * 18))
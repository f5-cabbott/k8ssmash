"""Button rebinding: press the button you want for each action, in order."""
from __future__ import annotations

import pygame

from k8ssmash import ui
from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.scenes.base import Scene

STEPS = [("JUMP", "JUMP"), ("ATTACK", "ATTACK"), ("SPECIAL", "SPECIAL"), ("SHIELD", "SHIELD (first button)"),
         ("SHIELD", "SHIELD (second button)"), ("START", "START"), ("SELECT", "SELECT")]
TIMEOUT = 40 * FPS


class Rebind(Scene):
    def __init__(self, app, on_done=None):
        super().__init__(app)
        self.on_done = on_done or app.go_title
        self.step = 0
        self.new: dict[str, list[int]] = {}
        self.message = ""
        self.frame = 0
        self.big = ui.Font(40)
        self.font = ui.Font(26)

    @property
    def finished(self) -> bool:
        return self.step >= len(STEPS)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.finished:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.app.cfg.dev_keys:
            self.on_done()
        elif event.type == pygame.JOYBUTTONDOWN:
            self.press(event.button)

    def press(self, button: int) -> None:
        action, _ = STEPS[self.step]
        owner = next((a for a, buttons in self.new.items() if button in buttons and a != action), None)
        if owner or (button in self.new.get(action, [])):
            self.message = f"Button {button} is already {owner or action}. Pick another."
            return
        self.new.setdefault(action, []).append(button)
        self.message = f"{action}: button {button}"
        self.step += 1
        self.frame = 0
        self.app.audio.play("menu_select")
        if self.finished:
            self.app.cfg.pad.update(self.new)
            self.app.cfg.save()

    def update(self) -> None:
        self.frame += 1
        if self.finished:
            if self.frame > 90:
                self.on_done()
        elif self.frame > TIMEOUT:
            self.on_done()  # nothing was saved

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((14, 18, 36))
        head = self.big.render("REBIND BUTTONS", False, (255, 215, 90))
        canvas.blit(head, ((CANVAS_W - head.get_width()) // 2, 30))
        if self.finished:
            self._center(canvas, "Saved!", self.big, 150, (120, 230, 140))
        else:
            self._center(canvas, f"Press the button for  {STEPS[self.step][1]}", self.big, 130, (255, 255, 255))
            self._center(canvas, f"step {self.step + 1} of {len(STEPS)}", self.font, 175, (130, 140, 190))
        self._center(canvas, self.message, self.font, 230, (255, 200, 120))
        for i, (action, buttons) in enumerate(self.new.items()):
            canvas.blit(self.font.render(f"{action}: {buttons}", False, (190, 200, 240)),
                        (60 + (i // 4) * 200, 280 + (i % 4) * 18))

    def _center(self, canvas, text, font, y, color) -> None:
        surf = font.render(text, False, color)
        canvas.blit(surf, ((CANVAS_W - surf.get_width()) // 2, y))

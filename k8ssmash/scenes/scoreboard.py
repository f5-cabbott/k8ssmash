"""Leaderboard display and 3-letter name entry."""
from __future__ import annotations

from typing import Callable

import pygame

from k8ssmash import ui
from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.palette import player_colors
from k8ssmash.scenes.base import Scene
from k8ssmash.scores import BOARD_TITLES, BOARDS, CHARSET, DEFAULT_NAME, MAX_ENTRIES, Prompt

BG = (14, 18, 36)
GOLD = (255, 215, 90)
DISPLAY_FRAMES = 12 * FPS
ENTRY_TIMEOUT = 25 * FPS


class HighScores(Scene):
    def __init__(self, app, on_done: Callable[[], None], highlight: set[str] | None = None,
                 seconds: float = 12.0):
        super().__init__(app)
        self.on_done = on_done
        self.highlight = highlight or set()
        self.frame = 0
        self.limit = int(seconds * FPS)
        self.big = ui.Font(40)
        self.font = ui.Font(26)
        self.small = ui.Font(20)
        app.audio.music("leaderboard")

    def update(self) -> None:
        self.frame += 1
        pressed = any(p.pressed & {"START", "ATTACK", "SPECIAL", "JUMP"} for p in self.app.input.players)
        if self.frame > 20 and (pressed or self.frame >= self.limit):
            self.on_done()

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        head = self.big.render(f"{self.app.cfg.event_name.upper()} LEADERBOARD", False, GOLD)
        canvas.blit(head, ((CANVAS_W - head.get_width()) // 2, 14))
        sub = self.small.render("K8S SMASH  -  PODS VS. CHAOS", False, (110, 130, 200))
        canvas.blit(sub, ((CANVAS_W - sub.get_width()) // 2, 46))
        for col, board in enumerate(BOARDS):
            x = 22 + col * 308
            canvas.blit(self.font.render(BOARD_TITLES[board], False, (180, 200, 255)), (x, 74))
            pygame.draw.line(canvas, (60, 76, 130), (x, 98), (x + 280, 98), 2)
            entries = self.app.scores.top(board)
            for i in range(MAX_ENTRIES):
                y = 106 + i * 24
                if i >= len(entries):
                    canvas.blit(self.small.render(f"{i + 1:>2}.  ---", False, (70, 78, 120)), (x, y + 3))
                    continue
                e = entries[i]
                fresh = e.run in self.highlight
                color = GOLD if fresh and (self.frame // 12) % 2 == 0 else (235, 238, 255) if i < 3 else (170, 178, 215)
                canvas.blit(self.font.render(f"{i + 1:>2}.  {e.name}", False, color), (x, y))
                canvas.blit(self.font.render(str(e.value), False, color), (x + 138, y))
                canvas.blit(self.small.render(e.fighter, False, (120, 132, 185)), (x + 178, y + 4))
        hint = self.small.render("Press any button", False, (110, 120, 170))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 346))


class NameEntry(Scene):
    """The winner enters three characters with their own pad."""

    def __init__(self, app, prompt: Prompt, on_done: Callable[[str], None]):
        super().__init__(app)
        self.prompt = prompt
        self.on_done = on_done
        self.chars = list(DEFAULT_NAME)
        self.pos = 0
        self.frame = 0
        self.big = ui.Font(40)
        self.huge = ui.Font(110)
        self.font = ui.Font(26)
        app.audio.play("pickup")

    def _finish(self) -> None:
        self.on_done("".join(self.chars))

    def update(self) -> None:
        self.frame += 1
        if self.frame >= ENTRY_TIMEOUT:
            self._finish()
            return
        inp = self.app.input.players[self.prompt.slot]
        if self.app.idle_frames == 0:
            self.frame = min(self.frame, ENTRY_TIMEOUT - 15 * FPS)  # any input buys more time
        step = ("UP" in inp.pressed) - ("DOWN" in inp.pressed)
        if step:
            i = CHARSET.index(self.chars[self.pos])
            self.chars[self.pos] = CHARSET[(i + step) % len(CHARSET)]
            self.app.audio.play("menu_move")
        if "RIGHT" in inp.pressed and self.pos < 2:
            self.pos += 1
            self.app.audio.play("menu_move")
        if "LEFT" in inp.pressed and self.pos > 0:
            self.pos -= 1
            self.app.audio.play("menu_move")
        if inp.pressed & {"ATTACK", "START", "JUMP"}:
            self.app.audio.play("menu_select")
            if self.pos < 2:
                self.pos += 1
            else:
                self._finish()
        if "SPECIAL" in inp.pressed and self.pos > 0:
            self.pos -= 1

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        color = player_colors(self.app.cfg)[self.prompt.slot]
        title = self.big.render(f"P{self.prompt.slot + 1}: NEW HIGH SCORE!", False, GOLD)
        canvas.blit(title, ((CANVAS_W - title.get_width()) // 2, 40))
        run = self.app.runs.runs[self.prompt.slot]
        line = f"{self.prompt.fighter}   streak {run.streak}   KOs {run.kos}"
        text = self.font.render(line, False, (200, 210, 245))
        canvas.blit(text, ((CANVAS_W - text.get_width()) // 2, 86))
        for i, ch in enumerate(self.chars):
            x = 200 + i * 90
            active = i == self.pos
            glyph = self.huge.render(ch, False, color if active else (200, 205, 230))
            canvas.blit(glyph, (x + (60 - glyph.get_width()) // 2, 140))
            pygame.draw.rect(canvas, color if active else (70, 80, 130), (x, 222, 60, 6))
            if active and (self.frame // 15) % 2 == 0:
                pygame.draw.polygon(canvas, color, [(x + 22, 130), (x + 38, 130), (x + 30, 120)])
                pygame.draw.polygon(canvas, color, [(x + 22, 236), (x + 38, 236), (x + 30, 246)])
        hint = self.font.render("UP/DOWN: letter    LEFT/RIGHT: move    B: OK", False, (120, 132, 185))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 300))

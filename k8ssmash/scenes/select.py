from __future__ import annotations

import random

import pygame

from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.roster import roster
from k8ssmash.scenes.base import Scene
from k8ssmash.scenes.battle import Battle, P_COLORS

BG = (16, 20, 38)
TIMEOUT = 30 * FPS
START_DELAY = 45


class CharacterSelect(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.roster = roster()
        self.joined = [False, False]
        self.cpu = [False, False]
        self.cursor = [0, min(1, len(self.roster) - 1)]
        self.locked = [False, False]
        self.ready_frames = 0
        self.big = pygame.font.Font(None, 40)
        self.font = pygame.font.Font(None, 22)
        self.rng = random.Random()

    # --- logic ---------------------------------------------------------------------------
    def _active(self, slot: int) -> bool:
        return self.joined[slot] or self.cpu[slot]

    def update(self) -> None:
        if self.app.idle_frames >= TIMEOUT:
            self.app.go_title()
            return
        players = self.app.input.players
        n = len(self.roster)
        for slot, inp in enumerate(players):
            if not self.joined[slot]:
                if "START" in inp.pressed and "SELECT" not in inp.held:
                    self.joined[slot] = True
                    self.cpu[slot] = False
                continue
            if self.locked[slot]:
                if "SPECIAL" in inp.pressed:
                    self.locked[slot] = False
                    self.ready_frames = 0
                continue
            if "LEFT" in inp.pressed:
                self.cursor[slot] = (self.cursor[slot] - 1) % n
            if "RIGHT" in inp.pressed:
                self.cursor[slot] = (self.cursor[slot] + 1) % n
            if "UP" in inp.pressed or "DOWN" in inp.pressed:
                self.cursor[slot] = (self.cursor[slot] + n // 2) % n if n > 2 else self.cursor[slot]
            if "ATTACK" in inp.pressed or "START" in inp.pressed:
                self.locked[slot] = True
            if "SPECIAL" in inp.pressed:
                self.joined[slot] = False

        # A lone player can press SELECT to add a CPU opponent.
        for slot in (0, 1):
            other = 1 - slot
            if self.joined[slot] and not self._active(other) and "SELECT" in players[slot].pressed:
                self.cpu[other] = True
                self.cursor[other] = self.rng.randrange(n)
        # The CPU locks in once its human opponent has.
        for slot in (0, 1):
            if self.cpu[slot] and self.locked[1 - slot]:
                self.locked[slot] = True

        both = all(self._active(s) for s in (0, 1)) and all(self.locked)
        self.ready_frames = self.ready_frames + 1 if both else 0
        if self.ready_frames >= START_DELAY:
            self._start()

    def _start(self) -> None:
        stats = [self.roster[self.cursor[s]] for s in (0, 1)]
        human = [self.joined[s] and not self.cpu[s] for s in (0, 1)]
        self.app.last_match = (list(self.cursor), human)
        self.app.set_scene(Battle(self.app, stats, human=human))

    # --- drawing -------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        head = self.big.render("CHOOSE YOUR POD", False, (255, 255, 255))
        canvas.blit(head, ((CANVAS_W - head.get_width()) // 2, 16))
        n = len(self.roster)
        cols = min(n, 4)
        card_w, card_h, gap = 120, 90, 14
        total = cols * card_w + (cols - 1) * gap
        x0 = (CANVAS_W - total) // 2
        for i, st in enumerate(self.roster):
            cx = x0 + (i % cols) * (card_w + gap)
            cy = 70 + (i // cols) * (card_h + gap)
            pygame.draw.rect(canvas, (34, 40, 70), (cx, cy, card_w, card_h))
            pygame.draw.rect(canvas, st.color, (cx + 40, cy + 14, 40, 52))
            canvas.blit(self.font.render(st.name, False, (230, 230, 245)), (cx + 8, cy + card_h - 20))
            for slot in (0, 1):
                if self._active(slot) and self.cursor[slot] == i:
                    off = slot * 4
                    width = 0 if self.locked[slot] and False else 3
                    pygame.draw.rect(canvas, P_COLORS[slot], (cx - off, cy - off, card_w + 2 * off, card_h + 2 * off), width)
        for slot in (0, 1):
            y = 262
            x = 40 + slot * 320
            if self.cpu[slot]:
                status, color = ("CPU  READY" if self.locked[slot] else "CPU"), (180, 180, 200)
            elif not self.joined[slot]:
                status, color = "Press START to join", (150, 150, 170)
                if slot == 1 and self.joined[0]:
                    status += "  (or SELECT: CPU)"
            elif self.locked[slot]:
                status, color = "READY!", (120, 230, 140)
            else:
                status, color = f"P{slot + 1}: {self.roster[self.cursor[slot]].name}", P_COLORS[slot]
            canvas.blit(self.big.render(f"P{slot + 1}", False, P_COLORS[slot]), (x, y))
            canvas.blit(self.font.render(status, False, color), (x + 40, y + 8))
        hint = self.font.render("B: select   A: back   SELECT: add CPU opponent", False, (120, 126, 160))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 332))

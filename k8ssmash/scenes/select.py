from __future__ import annotations

import random

import pygame

from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.roster import roster
from k8ssmash.scenes.base import Scene
from k8ssmash.scenes.battle import Battle, P_COLORS
from k8ssmash.sprites import sprite_set

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
        self.big = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 22)
        self.small = pygame.font.Font(None, 18)
        self.frame = 0
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
        canvas.blit(head, ((CANVAS_W - head.get_width()) // 2, 10))
        n = len(self.roster)
        cols = min(n, 4)
        card_w, card_h, gap = 140, 108, 12
        total = cols * card_w + (cols - 1) * gap
        x0 = (CANVAS_W - total) // 2
        for i, st in enumerate(self.roster):
            cx = x0 + (i % cols) * (card_w + gap)
            cy = 46 + (i // cols) * (card_h + gap)
            pygame.draw.rect(canvas, (30, 36, 64), (cx, cy, card_w, card_h))
            pygame.draw.rect(canvas, _dim(st.color), (cx, cy + card_h - 22, card_w, 22))
            sprites = sprite_set(st.name)
            if sprites is not None:
                img = sprites.get("idle", (self.frame // 12) % 4, 1)
                canvas.blit(img, (cx + (card_w - img.get_width()) // 2, cy + 2))
            else:
                pygame.draw.rect(canvas, st.color, (cx + 50, cy + 14, 40, 52))
            label = self.font.render(st.name, False, (240, 240, 255))
            canvas.blit(label, (cx + (card_w - label.get_width()) // 2, cy + card_h - 18))
            for slot in (0, 1):
                if self._active(slot) and self.cursor[slot] == i:
                    off = slot * 4
                    width = 3 if not self.locked[slot] or (self.frame // 8) % 2 == 0 else 5
                    pygame.draw.rect(canvas, P_COLORS[slot],
                                     (cx - off - 2, cy - off - 2, card_w + 2 * off + 4, card_h + 2 * off + 4), width)
        for slot in (0, 1):
            x = 24 + slot * 320
            y = 296
            if self.cpu[slot]:
                status, color = ("CPU  READY" if self.locked[slot] else "CPU"), (180, 180, 200)
                blurb = ""
            elif not self.joined[slot]:
                status, color = "Press START to join", (150, 150, 170)
                if slot == 1 and self.joined[0]:
                    status += "  (or SELECT: CPU)"
                blurb = ""
            elif self.locked[slot]:
                status, color = "READY!", (120, 230, 140)
                blurb = self.roster[self.cursor[slot]].blurb
            else:
                st = self.roster[self.cursor[slot]]
                status, color, blurb = st.name, P_COLORS[slot], st.blurb
            canvas.blit(self.big.render(f"P{slot + 1}", False, P_COLORS[slot]), (x, y - 4))
            canvas.blit(self.font.render(status, False, color), (x + 44, y))
            if blurb:
                canvas.blit(self.small.render(blurb, False, (170, 176, 205)), (x + 44, y + 16))
        hint = self.small.render("B: select   A: back   SELECT: add CPU opponent", False, (120, 126, 160))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 342))


def _dim(color):
    return tuple(int(c * 0.45) for c in color)

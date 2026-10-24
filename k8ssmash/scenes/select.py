from __future__ import annotations

import random

import pygame

from k8ssmash import ui
from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.fighter import FighterStats
from k8ssmash.roster import roster
from k8ssmash.scenes.base import Scene
from k8ssmash.palette import player_colors
from k8ssmash.scenes.battle import Battle
from k8ssmash.stage import STAGES
from k8ssmash.sprites import sprite_set

BG = (16, 20, 38)
TIMEOUT = 30 * FPS
START_DELAY = 45


class CharacterSelect(Scene):
    def __init__(self, app, training: bool = False):
        super().__init__(app)
        self.training = training
        self.roster = roster()
        self.joined = [False, False]
        self.cpu = [False, False]
        self.cursor = [0, min(1, len(self.roster) - 1)]
        self.locked = [False, False]
        self.ready_frames = 0
        self.stage_idx = random.randrange(len(STAGES))
        self.big = ui.Font(36)
        self.font = ui.Font(22)
        self.small = ui.Font(18)
        self.tiny = ui.Font(15)
        self.frame = 0
        app.audio.music("select")
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
                    self.app.audio.play("join")
                elif "SPECIAL" in inp.pressed and not any(self._active(s) for s in (0, 1)):
                    self.app.audio.play("menu_move")
                    self.app.go_title()  # backing out of the very first prompt leaves to the main menu
                    return
                continue
            if self.locked[slot]:
                if "SPECIAL" in inp.pressed:
                    self.locked[slot] = False
                    self.ready_frames = 0
                continue
            if inp.pressed & {"LEFT", "RIGHT", "UP", "DOWN"}:
                self.app.audio.play("menu_move")
            if "LEFT" in inp.pressed:
                self.cursor[slot] = (self.cursor[slot] - 1) % n
            if "RIGHT" in inp.pressed:
                self.cursor[slot] = (self.cursor[slot] + 1) % n
            if "UP" in inp.pressed or "DOWN" in inp.pressed:
                self.cursor[slot] = (self.cursor[slot] + n // 2) % n if n > 2 else self.cursor[slot]
            if "ATTACK" in inp.pressed or "START" in inp.pressed:
                self.locked[slot] = True
                self.app.audio.play("menu_select")
            if "SPECIAL" in inp.pressed:
                self.joined[slot] = False

        # L/R shoulder (SHIELD) cycles the stage.
        for inp in players:
            if "SHIELD" in inp.pressed:
                self.stage_idx = (self.stage_idx + 1) % len(STAGES)

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

        if self.training:
            both = self.joined[0] and self.locked[0]
        else:
            both = all(self._active(s) for s in (0, 1)) and all(self.locked)
        self.ready_frames = self.ready_frames + 1 if both else 0
        if self.ready_frames >= START_DELAY:
            self._start()

    def _start(self) -> None:
        if self.training:
            from k8ssmash.scenes.training import Training

            dummy = self.roster[(self.cursor[0] + 1 + self.rng.randrange(len(self.roster) - 1)) % len(self.roster)]
            self.app.set_scene(Training(self.app, [self.roster[self.cursor[0]], dummy],
                                        stage=STAGES[self.stage_idx]()))
            return
        stats = [self.roster[self.cursor[s]] for s in (0, 1)]
        human = [self.joined[s] and not self.cpu[s] for s in (0, 1)]
        self.app.last_match = (list(self.cursor), human, self.stage_idx)
        self.app.set_scene(Battle(self.app, stats, stage=STAGES[self.stage_idx](), human=human))

    # --- drawing -------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        colors = player_colors(self.app.cfg)
        head = self.big.render("TRAINING: CHOOSE YOUR POD" if self.training else "CHOOSE YOUR POD", False, (255, 255, 255))
        canvas.blit(head, ((CANVAS_W - head.get_width()) // 2, 5))
        n = len(self.roster)
        cols = min(n, 4)
        card_w, card_h, gap = 132, 78, 10
        x0 = (CANVAS_W - (cols * card_w + (cols - 1) * gap)) // 2
        for i, st in enumerate(self.roster):
            cx = x0 + (i % cols) * (card_w + gap)
            cy = 36 + (i // cols) * (card_h + 8)
            card = pygame.Rect(cx, cy, card_w, card_h)
            ui.window(canvas, card)
            pygame.draw.rect(canvas, _dim(st.color), (cx + 3, cy + card_h - 20, card_w - 6, 17))
            sprites = sprite_set(st.name)
            if sprites is not None:
                img = sprites.get("idle", (self.frame // 12) % 4, 1)
                fx, fy = sprites.feet
                canvas.set_clip(card.inflate(-4, -4))
                canvas.blit(img, (cx + card_w // 2 - fx, cy + card_h - 21 - fy))
                canvas.set_clip(None)
            label = self.small.render(st.name, False, (240, 240, 255))
            canvas.blit(label, (cx + (card_w - label.get_width()) // 2, cy + card_h - 18))
            for slot in (0, 1):
                if self._active(slot) and self.cursor[slot] == i:
                    off = slot * 3
                    width = 3 if not self.locked[slot] or (self.frame // 8) % 2 == 0 else 5
                    pygame.draw.rect(canvas, colors[slot], (cx - off - 2, cy - off - 2, card_w + 2 * off + 4, card_h + 2 * off + 4), width)
        for slot in (0, 1):
            self._draw_panel(canvas, pygame.Rect(12 + slot * 312, 204, 304, 112), slot, colors[slot])
        self._draw_legend(canvas)
        stage = STAGES[self.stage_idx]().name
        hint = self.tiny.render(f"START join/ready    A back / leave    SELECT add CPU    L/R stage: {stage}", False, (126, 134, 176))
        canvas.blit(hint, ((CANVAS_W - hint.get_width()) // 2, 347))

    def _draw_panel(self, canvas: pygame.Surface, rect: pygame.Rect, slot: int, color) -> None:
        ui.window(canvas, rect, accent=color)
        tag = self.big.render(f"P{slot + 1}", False, color)
        canvas.blit(tag, (rect.x + 8, rect.y + 6))
        if self.training and slot == 1:
            self._center_text(canvas, rect, "Dummy: a random fighter", (170, 176, 205))
            return
        if not self._active(slot):
            self._center_text(canvas, rect, "Press START to join", (150, 158, 190))
            return
        st = self.roster[self.cursor[slot]]
        status = "CPU" if self.cpu[slot] else ("READY!" if self.locked[slot] else "")
        name = self.font.render(st.name, False, (255, 255, 255))
        canvas.blit(name, (rect.x + 46, rect.y + 6))
        if status:
            s = self.small.render(status, False, (120, 230, 140) if status == "READY!" else (180, 184, 210))
            canvas.blit(s, (rect.right - s.get_width() - 10, rect.y + 8))
        canvas.blit(self.tiny.render(st.blurb, False, (170, 178, 214)), (rect.x + 46, rect.y + 24))
        for i, (direction, key, tag_text) in enumerate(MOVE_ROWS):
            self._move_row(canvas, rect.x + 12, rect.y + 44 + i * 16, direction, st, key, tag_text)

    def _move_row(self, canvas, x: int, y: int, direction: str | None, st: FighterStats, key: str, tag_text: str) -> None:
        move = st.moves.get(key)
        if move is None:
            return
        if direction:
            x += ui.dpad_glyph(canvas, x, y, direction)
            plus = self.tiny.render("+", False, (200, 206, 235))
            canvas.blit(plus, (x, y))
            x += plus.get_width() + 3
        x += ui.button_glyph(canvas, x, y, "A") + 6
        text = move.announce or move.name
        t = self.small.render(text[0].upper() + text[1:], False, (240, 242, 255))
        canvas.blit(t, (x, y - 1))
        if tag_text:
            canvas.blit(self.tiny.render(tag_text, False, (255, 214, 120)), (x + t.get_width() + 8, y + 1))

    def _center_text(self, canvas, rect: pygame.Rect, text: str, color) -> None:
        t = self.small.render(text, False, color)
        canvas.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2 + 8))

    def _draw_legend(self, canvas: pygame.Surface) -> None:
        bar = pygame.Rect(12, 320, 616, 24)
        ui.window(canvas, bar)
        x, y = bar.x + 10, bar.y + 4
        parts: list[tuple[str, tuple]] = [
            ("Move", ("dpad", None)), ("Jump x2", ("btn", "Y", "X")), ("Attack", ("btn", "B")),
            ("Special", ("btn", "A")), ("+ dir = more moves", ("dpad", "right")), ("Shield", ("btn", "L", "R")),
            ("Duck", ("dpad", "down")),
        ]
        for label, spec in parts:
            if spec[0] == "dpad":
                x += ui.dpad_glyph(canvas, x, y, spec[1]) + 2
            else:
                for b in spec[1:]:
                    x += ui.button_glyph(canvas, x, y, b) + 1
            t = self.tiny.render(label, False, (226, 230, 250))
            canvas.blit(t, (x + 2, y + 1))
            x += t.get_width() + 14


MOVE_ROWS = [(None, "special", ""), ("right", "special_side", ""), ("up", "special_up", "recovery"),
             ("down", "special_down", "")]


def _dim(color):
    return tuple(int(c * 0.45) for c in color)

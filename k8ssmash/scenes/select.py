from __future__ import annotations

import random

import pygame

from k8ssmash import ui
from k8ssmash.ui import pd
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


_portraits: dict[tuple, pygame.Surface] = {}


def _mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def portrait(name: str, color, w: int, h: int, floor: int) -> pygame.Surface:
    """A fighter's card art: a tinted Tron stage with a spotlight beam, a glowing podium and a perspective grid,
    and a bevelled name plate. Built once per fighter, in world pixels."""
    key = (name, tuple(color), w, h)
    cached = _portraits.get(key)
    if cached is not None:
        return cached
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base_top, base_bot = (6, 8, 26), _mix((8, 10, 30), color, 0.28)
    for y in range(h):
        pygame.draw.line(surf, _mix(base_top, base_bot, (y / h) ** 1.3), (0, y), (w, y))
    cx = w // 2
    # a soft beam of light dropping onto the podium
    beam = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(beam, _mix(color, (255, 255, 255), 0.25) + (46,), [(cx - 14, 0), (cx + 14, 0), (cx + 58, floor), (cx - 58, floor)])
    pygame.draw.polygon(beam, _mix(color, (255, 255, 255), 0.5) + (34,), [(cx - 6, 0), (cx + 6, 0), (cx + 26, floor), (cx - 26, floor)])
    surf.blit(beam, (0, 0))
    # halo behind the fighter, stepped so it stays pixel-crisp
    halo = pygame.Surface((w, h), pygame.SRCALPHA)
    for r, a in ((54, 14), (42, 20), (30, 28), (18, 36)):
        pygame.draw.ellipse(halo, color + (a,), (cx - r * 1.2, floor - 38 - r * 0.8, r * 2.4, r * 1.6))
    surf.blit(halo, (0, 0))
    # perspective grid on the floor
    grid = _mix(color, (255, 255, 255), 0.1)
    for k in range(-9, 10):
        pygame.draw.line(surf, _mix(base_bot, grid, 0.5), (cx + k * 3, floor), (cx + k * 26, h), 1)
    for i in range(1, 5):
        y = floor + round((h - floor) * (i / 4) ** 1.7)
        pygame.draw.line(surf, _mix(base_bot, grid, 0.35 + 0.1 * i), (0, y), (w, y), 1)
    # the podium: a glowing ellipse the fighter stands on
    for k, a in ((16, 36), (11, 70), (7, 140)):
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, _mix(color, (255, 255, 255), 0.2) + (a,), (cx - 34 - k, floor - 5 - k // 3, 68 + 2 * k, 10 + 2 * (k // 3)))
        surf.blit(glow, (0, 0))
    pygame.draw.ellipse(surf, _mix(color, (255, 255, 255), 0.6), (cx - 34, floor - 5, 68, 10), 1)
    # scanlines, so the art reads like a CRT card
    for y in range(0, h, 3):
        pygame.draw.line(surf, (0, 0, 0, 22), (0, y), (w, y))
    # name plate along the bottom
    plate_h = round(19 * ui.SCALE)
    plate = pygame.Surface((w, plate_h), pygame.SRCALPHA)
    for y in range(plate_h):
        pygame.draw.line(plate, _mix(_mix(color, (255, 255, 255), 0.18), (8, 10, 30), y / plate_h) + (255,), (0, y), (w, y))
    pygame.draw.line(plate, _mix(color, (255, 255, 255), 0.7), (0, 0), (w, 0), 2)
    surf.blit(plate, (0, h - plate_h))
    label = ui.fit(name, (255, 255, 255), w / ui.SCALE - 16, 13, 9)
    surf.blit(label, ((w - pygame.Surface.get_width(label)) // 2, h - plate_h + (plate_h - pygame.Surface.get_height(label)) // 2 + 1))
    pygame.draw.rect(surf, (6, 8, 30), (0, 0, w, h), 1)
    pygame.draw.rect(surf, _mix(color, (255, 255, 255), 0.35), (1, 1, w - 2, h - 2), 1)
    _portraits[key] = surf
    return surf


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
        self.big = ui.UIFont(22)  # screen title
        self.font = ui.UIFont(15)  # fighter name
        self.small = ui.UIFont(12)  # blurb, move names, card labels
        self.tiny = ui.UIFont(10)  # legend and hints
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
        ui.blit_c(canvas, head, 6)
        n = len(self.roster)
        cols = min(n, 4)
        card_w, card_h, gap = 142, 84, 8
        x0 = (CANVAS_W - (cols * card_w + (cols - 1) * gap)) // 2
        for i, st in enumerate(self.roster):
            cx = x0 + (i % cols) * (card_w + gap)
            cy = 32 + (i // cols) * (card_h + 6)
            floor_y = cy + card_h - 24  # where the fighter stands: always fully inside the card
            canvas.blit(portrait(st.name, st.color, round(card_w * ui.SCALE), round(card_h * ui.SCALE),
                                 round((floor_y - cy) * ui.SCALE)), (round(cx * ui.SCALE), round(cy * ui.SCALE)))
            sprites = sprite_set(st.name)
            if sprites is not None:  # the whole fighter at native pixel size, so it stays crisp and never gets cropped
                img = sprites.get("idle", (self.frame // 12) % 4, 1)
                ui.blit_sprite(canvas, img, cx + card_w // 2, floor_y, sprites.feet)
            for slot in (0, 1):
                if self._active(slot) and self.cursor[slot] == i:
                    off = slot * 3
                    width = 3 if not self.locked[slot] or (self.frame // 8) % 2 == 0 else 5
                    pd.rect(canvas, colors[slot], (cx - off - 2, cy - off - 2, card_w + 2 * off + 4, card_h + 2 * off + 4), width)
        for slot in (0, 1):
            self._draw_panel(canvas, pygame.Rect(12 + slot * 316, 214, 304, 86), slot, colors[slot])
        self._draw_legend(canvas)
        stage = STAGES[self.stage_idx]().name
        hint = ui.fit(f"START join/ready    A back / leave    SELECT add CPU    L/R stage: {stage}", (126, 134, 176), 600, 10, 8)
        ui.blit_c(canvas, hint, 335)

    def _draw_panel(self, canvas: pygame.Surface, rect: pygame.Rect, slot: int, color) -> None:
        ui.window_d(canvas, rect, accent=color)
        tag = self.font.render(f"P{slot + 1}", False, color)
        pd.blit(canvas, tag, (rect.x + 8, rect.y + 5))
        if self.training and slot == 1:
            self._center_text(canvas, rect, "Dummy: a random fighter", (170, 176, 205))
            return
        if not self._active(slot):
            self._center_text(canvas, rect, "Press START to join", (150, 158, 190))
            return
        st = self.roster[self.cursor[slot]]
        status = "CPU" if self.cpu[slot] else ("READY!" if self.locked[slot] else "")
        status_w = 0
        if status:
            s = self.small.render(status, False, (120, 230, 140) if status == "READY!" else (180, 184, 210))
            pd.blit(canvas, s, (rect.right - s.get_width() - 10, rect.y + 7))
            status_w = s.get_width() + 8
        pd.blit(canvas, ui.fit(st.name, (255, 255, 255), rect.w - 44 - status_w, 15, 10), (rect.x + 32, rect.y + 5))
        pd.blit(canvas, ui.fit(st.blurb, (170, 178, 214), rect.w - 44, 12, 9), (rect.x + 32, rect.y + 22))
        for i, (direction, key, tag_text) in enumerate(MOVE_ROWS):
            self._move_row(canvas, rect.x + 10, rect.y + 39 + i * 12, direction, st, key, tag_text, rect.right - 10)

    def _move_row(self, canvas, x: int, y: int, direction: str | None, st: FighterStats, key: str, tag_text: str,
                  right: int) -> None:
        move = st.moves.get(key)
        if move is None:
            return
        g = 0.72  # compact glyphs: the list is a reference, not the focus of the screen
        if direction:
            x += ui.dpad_glyph(canvas, x, y, direction, g)
            plus = self.tiny.render("+", False, (200, 206, 235))
            pd.blit(canvas, plus, (x, y + 1))
            x += plus.get_width() + 2
        x += ui.button_glyph(canvas, x, y, "A", g) + 4
        text = move.announce or move.name
        tag = self.tiny.render(tag_text, False, (255, 214, 120)) if tag_text else None
        room = right - x - (tag.get_width() + 8 if tag else 0)
        t = ui.fit(text[0].upper() + text[1:], (240, 242, 255), room, 12, 8)
        pd.blit(canvas, t, (x, y))
        if tag:
            pd.blit(canvas, tag, (x + t.get_width() + 6, y + 1))

    def _center_text(self, canvas, rect: pygame.Rect, text: str, color) -> None:
        t = ui.fit(text, color, rect.w - 20, 12, 8)
        pd.blit(canvas, t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2 + 6))

    def _draw_legend(self, canvas: pygame.Surface) -> None:
        bar = pygame.Rect(12, 306, 616, 22)
        ui.window_d(canvas, bar)
        x, y = bar.x + 10, bar.y + 5
        g = 0.72
        parts: list[tuple[str, tuple]] = [
            ("Move", ("dpad", None)), ("Jump x2", ("btn", "Y", "X")), ("Attack", ("btn", "B")),
            ("Special", ("btn", "A")), ("+ dir = more moves", ("dpad", "right")), ("Shield", ("btn", "L", "R")),
            ("Duck", ("dpad", "down")),
        ]
        used = sum(self.tiny.render(label, False, (226, 230, 250)).get_width() + 4
                   + (17 + 2 if spec[0] == "dpad" else 17 * (len(spec) - 1)) for label, spec in parts)
        gap = max(4, min(14, (bar.w - 20 - used) // len(parts)))
        for label, spec in parts:
            if spec[0] == "dpad":
                x += ui.dpad_glyph(canvas, x, y, spec[1], g) + 2
            else:
                for b in spec[1:]:
                    x += ui.button_glyph(canvas, x, y, b, g) + 1
            t = self.tiny.render(label, False, (226, 230, 250))
            pd.blit(canvas, t, (x + 2, y + 1))
            x += t.get_width() + gap


MOVE_ROWS = [(None, "special", ""), ("right", "special_side", ""), ("up", "special_up", "recovery"),
             ("down", "special_down", "")]


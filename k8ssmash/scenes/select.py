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
from k8ssmash.sprites import VARIANT_NAMES, sprite_set

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
    R = ui.SCALE / 1.5  # the art below was drawn for a 1.5-pixel design unit; R keeps its proportions at any render scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base_top, base_bot = (6, 8, 26), _mix((8, 10, 30), color, 0.28)
    for y in range(h):
        pygame.draw.line(surf, _mix(base_top, base_bot, (y / h) ** 1.3), (0, y), (w, y))
    cx = w // 2
    # a soft beam of light dropping onto the podium
    beam = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(beam, _mix(color, (255, 255, 255), 0.25) + (46,), [(cx - 14 * R, 0), (cx + 14 * R, 0), (cx + 58 * R, floor), (cx - 58 * R, floor)])
    pygame.draw.polygon(beam, _mix(color, (255, 255, 255), 0.5) + (34,), [(cx - 6 * R, 0), (cx + 6 * R, 0), (cx + 26 * R, floor), (cx - 26 * R, floor)])
    surf.blit(beam, (0, 0))
    # halo behind the fighter, stepped so it stays pixel-crisp
    halo = pygame.Surface((w, h), pygame.SRCALPHA)
    for r, a in ((54, 14), (42, 20), (30, 28), (18, 36)):
        pygame.draw.ellipse(halo, color + (a,), (cx - r * R * 1.2, floor - 38 * R - r * R * 0.8, r * R * 2.4, r * R * 1.6))
    surf.blit(halo, (0, 0))
    # perspective grid on the floor
    grid = _mix(color, (255, 255, 255), 0.1)
    for k in range(-9, 10):
        pygame.draw.line(surf, _mix(base_bot, grid, 0.5), (cx + k * 3 * R, floor), (cx + k * 26 * R, h), round(R))
    for i in range(1, 5):
        y = floor + round((h - floor) * (i / 4) ** 1.7)
        pygame.draw.line(surf, _mix(base_bot, grid, 0.35 + 0.1 * i), (0, y), (w, y), round(R))
    # the podium: a glowing ellipse the fighter stands on
    for k, a in ((16, 36), (11, 70), (7, 140)):
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, _mix(color, (255, 255, 255), 0.2) + (a,), (cx - (34 + k) * R, floor - (5 + k // 3) * R, (68 + 2 * k) * R, (10 + 2 * (k // 3)) * R))
        surf.blit(glow, (0, 0))
    pygame.draw.ellipse(surf, _mix(color, (255, 255, 255), 0.6), (cx - 34 * R, floor - 5 * R, 68 * R, 10 * R), round(R))
    # scanlines, so the art reads like a CRT card
    for y in range(0, h, round(3 * R)):
        pygame.draw.line(surf, (0, 0, 0, 22), (0, y), (w, y), round(R))
    # name plate along the bottom
    plate_h = round(19 * ui.SCALE)
    plate = pygame.Surface((w, plate_h), pygame.SRCALPHA)
    for y in range(plate_h):
        pygame.draw.line(plate, _mix(_mix(color, (255, 255, 255), 0.18), (8, 10, 30), y / plate_h) + (255,), (0, y), (w, y))
    pygame.draw.line(plate, _mix(color, (255, 255, 255), 0.7), (0, 0), (w, 0), round(2 * R))
    surf.blit(plate, (0, h - plate_h))
    label = ui.fit(name, (255, 255, 255), w / ui.SCALE - 16, 13, 9)
    surf.blit(label, ((w - pygame.Surface.get_width(label)) // 2, h - plate_h + (plate_h - pygame.Surface.get_height(label)) // 2 + 1))
    pygame.draw.rect(surf, (6, 8, 30), (0, 0, w, h), round(R))
    pygame.draw.rect(surf, _mix(color, (255, 255, 255), 0.35), (round(R), round(R), w - 2 * round(R), h - 2 * round(R)), round(R))
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
        self.variant = [0, 0]  # colour variant per slot (Y/X cycles)
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
            if "JUMP" in inp.pressed:
                self.variant[slot] = (self.variant[slot] + 1) % len(VARIANT_NAMES)
                self.app.audio.play("menu_move")
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
            self.app.last_variants = [self.variant[0], 0]
            self.app.set_scene(Training(self.app, [self.roster[self.cursor[0]], dummy],
                                        stage=STAGES[self.stage_idx]()))
            return
        from k8ssmash.scenes.stageselect import StageSelect

        stats = [self.roster[self.cursor[s]] for s in (0, 1)]
        human = [self.joined[s] and not self.cpu[s] for s in (0, 1)]
        self.app.last_match = (list(self.cursor), human, self.stage_idx)
        self.app.last_variants = list(self.variant)
        self.app.set_scene(StageSelect(self.app, stats, human, self.cursor, self.stage_idx))

    # --- drawing -------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(BG)
        colors = player_colors(self.app.cfg)
        head = self.big.render("TRAINING: CHOOSE YOUR POD" if self.training else "CHOOSE YOUR POD", False, (255, 255, 255))
        ui.blit_c(canvas, head, 3)
        n = len(self.roster)
        cols = min(n, 4)
        card_w, card_h, gap = 142, 68, 8
        x0 = (CANVAS_W - (cols * card_w + (cols - 1) * gap)) // 2
        for i, st in enumerate(self.roster):
            cx = x0 + (i % cols) * (card_w + gap)
            cy = 28 + (i // cols) * (card_h + 6)
            floor_y = cy + card_h - 19  # where the fighter stands: always fully inside the card, above the name plate
            canvas.blit(portrait(st.name, st.color, round(card_w * ui.SCALE), round(card_h * ui.SCALE),
                                 round((floor_y - cy) * ui.SCALE)), (round(cx * ui.SCALE), round(cy * ui.SCALE)))
            chosen = next((self.variant[sl] for sl in (0, 1) if self._active(sl) and self.cursor[sl] == i), 0)
            sprites = sprite_set(st.name, chosen)
            if sprites is not None:  # the whole fighter at native pixel size, so it stays crisp and never gets cropped
                img = sprites.get("idle", (self.frame // 12) % 4, 1)
                ui.blit_sprite(canvas, img, cx + card_w // 2, floor_y, sprites.feet)
            for slot in (0, 1):
                if self._active(slot) and self.cursor[slot] == i:
                    off = slot * 3
                    width = 3 if not self.locked[slot] or (self.frame // 8) % 2 == 0 else 5
                    pd.rect(canvas, colors[slot], (cx - off - 2, cy - off - 2, card_w + 2 * off + 4, card_h + 2 * off + 4), width)
        for slot in (0, 1):
            self._draw_panel(canvas, pygame.Rect(12 + slot * 316, 174, 304, 112), slot, colors[slot])
        self._draw_legend(canvas)
        stage = STAGES[self.stage_idx]().name
        hint = ui.fit(f"START join/ready    A back / leave    SELECT add CPU    L/R stage: {stage}", (126, 134, 176), 600, 10, 8)
        ui.blit_c(canvas, hint, 346)

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
        color_name = VARIANT_NAMES[self.variant[slot]]
        c = self.tiny.render(f"Y/X colors: {color_name}", False, (190, 200, 235))
        pd.blit(canvas, c, (rect.right - c.get_width() - 10, rect.bottom - 14))
        stats_x = rect.right - 98
        for i, (direction, key, tag_text) in enumerate(MOVE_ROWS):
            self._move_row(canvas, rect.x + 10, rect.y + 41 + i * 16, direction, st, key, tag_text, stats_x - 8)
        self._draw_stats(canvas, st, stats_x, rect.y + 42)

    def _draw_stats(self, canvas: pygame.Surface, st: FighterStats, x: int, y: int) -> None:
        """Three small meters (speed, weight, jumps), scaled against the whole roster so differences are visible."""
        def span(values):
            return min(values), max(values)
        r = self.roster
        rows = [("SPEED", st.run_speed, span([f.run_speed for f in r])), ("WEIGHT", st.weight, span([f.weight for f in r])),
                ("JUMPS", st.air_jumps, span([f.air_jumps for f in r]))]
        for i, (label, value, (lo, hi)) in enumerate(rows):
            yy = y + i * 18
            pd.blit(canvas, ui.fit(label, (170, 180, 220), 60, 10, 8), (x, yy))
            frac = 0.15 + 0.85 * ((value - lo) / (hi - lo) if hi > lo else 0.5)
            bar = (x, yy + 9, 84, 5)
            pd.rect(canvas, (8, 12, 40), bar)
            pd.rect(canvas, (255, 214, 120), (bar[0], bar[1], 84 * frac, 5))
            pd.rect(canvas, (150, 170, 230), bar, 1)

    def _move_row(self, canvas, x: int, y: int, direction: str | None, st: FighterStats, key: str, tag_text: str,
                  right: int) -> None:
        move = st.moves.get(key)
        if move is None:
            return
        g = 0.9
        if direction:
            x += ui.dpad_glyph(canvas, x, y, direction, g)
            plus = self.tiny.render("+", False, (200, 206, 235))
            pd.blit(canvas, plus, (x, y + 2))
            x += plus.get_width() + 3
        x += ui.button_glyph(canvas, x, y, "A", g) + 4
        text = move.announce or move.name
        tag = self.tiny.render(tag_text, False, (255, 214, 120)) if tag_text else None
        room = right - x - (tag.get_width() + 8 if tag else 0)
        t = ui.fit(text[0].upper() + text[1:], (240, 242, 255), room, 13, 8)
        pd.blit(canvas, t, (x, y + 1))
        if tag:
            pd.blit(canvas, tag, (x + t.get_width() + 6, y + 2))

    def _center_text(self, canvas, rect: pygame.Rect, text: str, color) -> None:
        t = ui.fit(text, color, rect.w - 20, 12, 8)
        pd.blit(canvas, t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

    def _draw_legend(self, canvas: pygame.Surface) -> None:
        """Controls in two rows of four, with full-size glyphs so every button letter can be read."""
        bar = pygame.Rect(12, 290, 616, 52)
        ui.window_d(canvas, bar)
        items = [
            [("Move", ("dpad", None)), ("Jump", ("btn", "Y", "X")), ("Attack", ("btn", "B")), ("Special", ("btn", "A"))],
            [("More specials", ("dpad", "right", "btn", "A")), ("Shield", ("btn", "L", "R")),
             ("Grab", ("btn", "L", "B")), ("Duck", ("dpad", "down"))],
        ]
        col_w = (bar.w - 20) / 4
        for r, row in enumerate(items):
            y = bar.y + 5 + r * 23
            for c, (label, spec) in enumerate(row):
                x = bar.x + 10 + c * col_w
                kind = spec[0]
                if kind == "dpad":
                    x += ui.dpad_glyph(canvas, x, y, spec[1], 0.95) + 3
                    rest = spec[2:]
                else:
                    rest = spec
                i = 0
                while i < len(rest):
                    if rest[i] == "btn":
                        i += 1
                        while i < len(rest) and rest[i] not in ("btn", "dpad"):
                            x += ui.button_glyph(canvas, x, y, rest[i], 0.95) + 2
                            i += 1
                    else:
                        i += 1
                t = ui.fit(label, (226, 230, 250), bar.x + 10 + (c + 1) * col_w - x - 4, 13, 8)
                pd.blit(canvas, t, (x + 3, y + 2))


MOVE_ROWS = [(None, "special", ""), ("right", "special_side", ""), ("up", "special_up", "recovery"),
             ("down", "special_down", "")]


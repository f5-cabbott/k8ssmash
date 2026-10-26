"""The settings menu: a hub of categories (UP/DOWN pick, A enters) and one page of options per category."""
from __future__ import annotations

import math

import pygame

from k8ssmash import ui
from k8ssmash.ui import pd
from k8ssmash.scenes.base import Scene

STEP = 0.05
REPEAT_DELAY, REPEAT_EVERY = 18, 3  # holding left/right keeps adjusting
CONFIRM, BACK = {"SPECIAL", "START"}, {"ATTACK", "SELECT"}  # START or A confirms, B backs out

STOCK_CHOICES = (1, 2, 3, 4, 5)
TIME_CHOICES = (60, 90, 120, 180, 300)

ASPECT_LABELS = {"16:9": "16:9 (standard)", "21:9": "21:9 (ultrawide)", "auto": "Auto (fit screen)"}

# category -> (title, blurb, rows); a row is (key, label, kind)
PAGES = {
    "audio": ("AUDIO", "Volume levels and mute", [
        ("master", "Master volume", "slider"),
        ("sfx", "Effects volume", "slider"),
        ("music", "Music volume", "slider"),
        ("mute", "Mute everything", "toggle"),
    ]),
    "display": ("DISPLAY", "Window, picture shape and colors", [
        ("fullscreen", "Fullscreen", "toggle"),
        ("aspect", "Screen shape", "choice"),
        ("size", "Window size", "choice"),
        ("colorblind", "Colorblind-safe colors", "toggle"),
    ]),
    "gameplay": ("GAMEPLAY", "Match rules", [
        ("stocks", "Stocks per fighter", "choice"),
        ("time", "Time limit", "choice"),
        ("items", "Power-ups", "toggle"),
    ]),
    "controls": ("CONTROLS", "Pads, buttons and tests", [
        ("rebind", "Rebind pad buttons", "action"),
        ("padtest", "Controller test", "action"),
        ("swap", "Swap P1 / P2 pads", "action"),
    ]),
}
HUB = ["audio", "display", "gameplay", "controls", "back"]
ROWS = [row for _, _, rows in PAGES.values() for row in rows]  # every option, flat (for tools and tests)


def _fmt_time(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


class Options:
    """Reads and changes the option behind each row key."""

    def __init__(self, app):
        self.app = app
        self.frame = 0

    def value(self, key: str):
        cfg = self.app.cfg
        return {"master": cfg.master_volume, "sfx": cfg.sfx_volume, "music": cfg.music_volume, "mute": cfg.muted,
                "colorblind": cfg.colorblind, "items": cfg.items, "fullscreen": cfg.fullscreen,
                "aspect": cfg.shape, "size": (cfg.width, cfg.height), "stocks": cfg.stocks,
                "time": cfg.match_seconds, "rebind": None, "padtest": None, "swap": cfg.swap_pads}[key]

    def label(self, key: str) -> str:
        value = self.value(key)
        if key == "aspect":
            return ASPECT_LABELS[value]
        if key == "size":
            return f"{value[0]} x {value[1]}"
        if key == "stocks":
            return f"{value} {'stock' if value == 1 else 'stocks'}"
        if key == "time":
            return _fmt_time(value)
        if key == "swap":
            return "swapped" if value else "normal"
        return str(value)

    def adjust(self, key: str, direction: int) -> None:
        cfg, audio = self.app.cfg, self.app.audio
        if key in ("master", "sfx", "music"):
            new = round(max(0.0, min(1.0, self.value(key) + direction * STEP)), 2)
            setattr(cfg, {"master": "master_volume", "sfx": "sfx_volume", "music": "music_volume"}[key], new)
            audio.set_volumes(master=cfg.master_volume, sfx=cfg.sfx_volume, music=cfg.music_volume)
            if key in ("master", "sfx") and self.frame % 3 == 0:
                audio.play("hit_light")  # a sample so you can hear the level you are choosing
        elif key == "mute":
            if (direction > 0) != cfg.muted:
                audio.toggle_mute()
                cfg.muted = audio.muted
        elif key == "colorblind":
            cfg.colorblind = direction > 0
        elif key == "items":
            cfg.items = direction > 0
        elif key == "fullscreen":
            if (direction > 0) != cfg.fullscreen:
                self.app.display.toggle_fullscreen()
        elif key == "aspect":
            modes = list(ASPECT_LABELS)
            self.app.display.set_aspect(modes[(modes.index(cfg.shape) + direction) % len(modes)])
        elif key == "size":
            sizes = self.app.display.sizes()
            cur = (cfg.width, cfg.height)
            idx = sizes.index(cur) if cur in sizes else 0
            self.app.display.set_size(*sizes[(idx + direction) % len(sizes)])
        elif key in ("stocks", "time"):
            choices = STOCK_CHOICES if key == "stocks" else TIME_CHOICES
            cur = self.value(key)
            idx = choices.index(cur) if cur in choices else choices.index(3 if key == "stocks" else 120)
            new = choices[(idx + direction) % len(choices)]
            if key == "stocks":
                cfg.stocks = new
            else:
                cfg.match_seconds = new

    def activate(self, key: str) -> None:
        """A row of kind 'action': open a tool, or flip a switch that has no on/off value of its own."""
        if key == "swap":
            self.app.input.swap_pads()
            self.app.cfg.swap_pads = not self.app.cfg.swap_pads
        elif key == "rebind":
            from k8ssmash.scenes.rebind import Rebind

            self.app.push_scene(Rebind(self.app, on_done=self.app.pop_scene))
        elif key == "padtest":
            from k8ssmash.scenes.padtest import ControllerTest

            self.app.push_scene(ControllerTest(self.app))


class Settings(Scene):
    """The hub: pick a category with UP/DOWN and press A to enter it."""

    def __init__(self, app, row: int = 0):
        super().__init__(app)
        self.row = row
        self.frame = 0
        self.big = ui.UIFont(34)
        self.font = ui.UIFont(22)
        self.small = ui.UIFont(14)
        app.audio.music("select")

    @property
    def page(self) -> str:
        return HUB[self.row]

    def update(self) -> None:
        self.frame += 1
        players = self.app.input.players
        for inp in players:
            if "UP" in inp.pressed:
                self.row = (self.row - 1) % len(HUB)
                self.app.audio.play("menu_move")
            if "DOWN" in inp.pressed:
                self.row = (self.row + 1) % len(HUB)
                self.app.audio.play("menu_move")
        if self.frame <= 10:
            return
        if any(inp.pressed & CONFIRM for inp in players):
            self.app.audio.play("menu_select")
            if self.page == "back":
                self._leave()
            else:
                self.app.set_scene(SettingsPage(self.app, self.page, hub_row=self.row))
        elif any(inp.pressed & BACK for inp in players):
            self.app.audio.play("menu_move")
            self._leave()

    def _leave(self) -> None:
        self.app.cfg.save()
        self.app.go_title()

    def draw(self, canvas: pygame.Surface) -> None:
        pd.blit(canvas, _background(), (0, 0))
        _heading(canvas, self.big, "SETTINGS", self.frame)
        for i, key in enumerate(HUB):
            rect = pygame.Rect(46, 62 + i * 46, 250, 38)
            active = i == self.row
            ui.window_d(canvas, rect, accent=(255, 224, 90) if active else None, alpha=240 if active else 190)
            title = PAGES[key][0] if key in PAGES else "BACK"
            color = (255, 255, 255) if active else (170, 182, 226)
            pd.blit(canvas, self.font.render(title, False, color), (rect.x + 52, rect.y + 8))
            _icon(canvas, key, rect.x + 26, rect.centery, active, self.frame)
            if active:
                bob = math.sin(self.frame * 0.2) * 2
                pd.polygon(canvas, (255, 224, 90), [(rect.right + 8 + bob, rect.centery - 7),
                                                    (rect.right + 8 + bob, rect.centery + 7), (rect.right + 18 + bob, rect.centery)])
        self._draw_preview(canvas)
        _hint(canvas, self.small, "UP / DOWN choose        START or A enter        B back")

    def _draw_preview(self, canvas: pygame.Surface) -> None:
        panel = pygame.Rect(334, 62, 262, 222)
        ui.window_d(canvas, panel)
        key = self.page
        if key == "back":
            pd.blit(canvas, ui.fit("Save and return to the title", (190, 200, 235), panel.w - 24, 15), (panel.x + 12, panel.y + 14))
            return
        title, blurb, rows = PAGES[key]
        pd.blit(canvas, ui.fit(title, (255, 224, 90), panel.w - 24, 20), (panel.x + 12, panel.y + 10))
        pd.blit(canvas, ui.fit(blurb, (150, 164, 214), panel.w - 24, 13), (panel.x + 12, panel.y + 34))
        opts = Options(self.app)
        for i, (rk, label, kind) in enumerate(rows):
            y = panel.y + 62 + i * 26
            pd.blit(canvas, ui.fit(label, (210, 218, 245), 128, 14), (panel.x + 12, y))
            if kind == "action":
                text = opts.label(rk) if rk == "swap" else "open"
                color = (255, 224, 140)
            elif kind == "slider":
                text, color = f"{round(opts.value(rk) * 100)}%", (255, 255, 255)
            elif kind == "toggle":
                on = bool(opts.value(rk))
                text, color = ("ON" if on else "OFF"), ((120, 255, 160) if on else (150, 156, 190))
            else:
                text, color = opts.label(rk), (255, 224, 140)
            pd.blit(canvas, ui.fit(text, color, 108, 14), (panel.x + 144, y))


class SettingsPage(Scene):
    """One category's options: UP/DOWN select a row, LEFT/RIGHT change it, A flips toggles and opens tools, B goes back."""

    def __init__(self, app, page: str, hub_row: int = 0):
        super().__init__(app)
        self.page = page
        self.hub_row = hub_row
        self.title, _, self.rows = PAGES[page]
        self.row = 0
        self.frame = 0
        self.held_for = 0
        self.options = Options(app)
        self.big = ui.UIFont(34)
        self.font = ui.UIFont(18)
        self.small = ui.UIFont(14)
        app.audio.music("select")

    # --- values ------------------------------------------------------------------------------
    def value(self, key: str):
        return self.options.value(key)

    def adjust(self, key: str, direction: int) -> None:
        self.options.frame = self.frame
        self.options.adjust(key, direction)

    # --- logic -------------------------------------------------------------------------------
    def update(self) -> None:
        self.frame += 1
        players = self.app.input.players
        for inp in players:
            if "UP" in inp.pressed:
                self.row = (self.row - 1) % len(self.rows)
                self.app.audio.play("menu_move")
            if "DOWN" in inp.pressed:
                self.row = (self.row + 1) % len(self.rows)
                self.app.audio.play("menu_move")
        key, _, kind = self.rows[self.row]
        direction = 0
        for inp in players:
            if "RIGHT" in inp.pressed:
                direction = 1
            elif "LEFT" in inp.pressed:
                direction = -1
            elif "SPECIAL" in inp.pressed and self.frame > 10:
                if kind == "action":
                    self.options.activate(key)
                    return
                if kind == "toggle":
                    direction = -1 if self.value(key) else 1
                elif kind == "choice":
                    direction = 1
        held = any(inp.axis_x for inp in players)
        self.held_for = self.held_for + 1 if held else 0
        if not direction and kind == "slider" and self.held_for > REPEAT_DELAY and self.held_for % REPEAT_EVERY == 0:
            direction = next(inp.axis_x for inp in players if inp.axis_x)
        if direction and kind != "action":
            self.adjust(key, direction)
        if self.frame > 10 and any(inp.pressed & (BACK | {"START"}) for inp in players):
            self.app.audio.play("menu_select")
            self.app.cfg.save()
            self.app.set_scene(Settings(self.app, row=self.hub_row))

    # --- drawing -----------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        pd.blit(canvas, _background(), (0, 0))
        _heading(canvas, self.big, self.title, self.frame)
        panel = pygame.Rect(60, 62, 520, 36 + len(self.rows) * 34)
        ui.window_d(canvas, panel)
        for i, (key, label, kind) in enumerate(self.rows):
            y = panel.y + 12 + i * 34
            active = i == self.row
            if active:
                pd.rect(canvas, (60, 90, 200), (panel.x + 8, y - 4, panel.w - 16, 30), border_radius=4)
                pd.polygon(canvas, (255, 224, 90), [(panel.x + 16, y + 3), (panel.x + 16, y + 17), (panel.x + 26, y + 10)])
            pd.blit(canvas, ui.fit(label, (255, 255, 255) if active else (190, 200, 235), 220, 18), (panel.x + 40, y))
            value = self.value(key)
            vx = panel.x + 270
            if kind == "slider":
                bar = pygame.Rect(vx, y + 3, 170, 15)
                pd.rect(canvas, (8, 12, 40), bar, border_radius=3)
                filled = int(bar.w * value)
                for sx in range(0, filled - 2, 8):  # segmented neon bar
                    pd.rect(canvas, _hue(sx / bar.w), (bar.x + 2 + sx, bar.y + 2, 6, bar.h - 4))
                pd.rect(canvas, (150, 170, 230), bar, 1, border_radius=3)
                pd.blit(canvas, self.font.render(f"{int(round(value * 100))}%", False, (255, 255, 255)), (bar.right + 10, y))
            elif kind == "choice":
                pd.blit(canvas, ui.fit(f"<  {self.options.label(key)}  >", (255, 224, 140), 230, 18), (vx, y))
            elif kind == "action":
                text = f"A: {self.options.label(key)}" if key == "swap" else "A: open"
                pd.blit(canvas, ui.fit(text, (255, 224, 140), 230, 18), (vx, y))
            else:
                on = bool(value)
                text = self.font.render("ON" if on else "OFF", False, (120, 255, 160) if on else (150, 156, 190))
                pd.blit(canvas, text, (vx + 20, y))
        verb = "A change" if any(k == "toggle" for _, _, k in self.rows) else "A select"
        _hint(canvas, self.small, f"UP / DOWN choose        LEFT / RIGHT change        {verb}        B back")


# --- shared look --------------------------------------------------------------------------------
_bg: pygame.Surface | None = None


def _background() -> pygame.Surface:
    global _bg
    if _bg is None:
        from k8ssmash.backdrops import dither_gradient
        from k8ssmash.config import PIX_H as WORLD_H, PIX_W as WORLD_W
        _bg = dither_gradient(WORLD_W, WORLD_H, [(0, (4, 6, 22)), (0.5, (10, 24, 80)), (1, (3, 6, 24))], bands=20)
    return _bg


def _hue(t: float) -> tuple[int, int, int]:
    """Slider colour: cool cyan at the quiet end, warm amber toward loud."""
    return (int(40 + 215 * t), int(220 - 80 * t), int(255 - 200 * t))


def _heading(canvas: pygame.Surface, font: ui.UIFont, text: str, frame: int) -> None:
    ui.blit_c(canvas, font.render(text, False, (255, 224, 90)), 14 + math.sin(frame * 0.06) * 1.5)
    pd.line(canvas, (0, 200, 255), (200, 52), (440, 52), 2)
    pd.line(canvas, (255, 150, 60), (240, 55), (400, 55), 1)


def _hint(canvas: pygame.Surface, font: ui.UIFont, text: str) -> None:
    ui.blit_c(canvas, font.render(text, False, (150, 166, 220)), 322)


def _icon(canvas: pygame.Surface, key: str, cx: int, cy: int, active: bool, frame: int) -> None:
    """Tiny pictograms for the hub: speaker, monitor, star and gamepad."""
    c = (255, 224, 90) if active else (140, 156, 214)
    if key == "audio":
        pd.polygon(canvas, c, [(cx - 9, cy - 3), (cx - 4, cy - 3), (cx + 2, cy - 8), (cx + 2, cy + 8), (cx - 4, cy + 3), (cx - 9, cy + 3)])
        for k in (1, 2):
            r = 4 + k * 4 + (math.sin(frame * 0.2) * 1 if active else 0)
            pygame.draw.arc(canvas, c, pygame.Rect(round((cx + 2 - r) * ui.SCALE), round((cy - r) * ui.SCALE),
                                                   round(2 * r * ui.SCALE), round(2 * r * ui.SCALE)), -0.9, 0.9, 2)
    elif key == "display":
        pd.rect(canvas, c, (cx - 11, cy - 8, 22, 15), 2, border_radius=2)
        pd.rect(canvas, c, (cx - 5, cy + 8, 10, 2))
        pd.line(canvas, c, (cx - 7, cy + 4), (cx - 2, cy - 2), 1)
        pd.line(canvas, c, (cx - 2, cy - 2), (cx + 2, cy + 2), 1)
        pd.line(canvas, c, (cx + 2, cy + 2), (cx + 7, cy - 4), 1)
    elif key == "gameplay":
        pts = [(cx + math.cos(-math.pi / 2 + i * math.pi / 5 + (frame * 0.03 if active else 0)) * (10 if i % 2 == 0 else 4.5),
                cy + math.sin(-math.pi / 2 + i * math.pi / 5 + (frame * 0.03 if active else 0)) * (10 if i % 2 == 0 else 4.5))
               for i in range(10)]
        pd.polygon(canvas, c, pts)
    elif key == "controls":
        pd.rect(canvas, c, (cx - 12, cy - 6, 24, 13), border_radius=5)
        dark = (20, 24, 60)
        pd.rect(canvas, dark, (cx - 9, cy - 1, 6, 2))
        pd.rect(canvas, dark, (cx - 7, cy - 3, 2, 6))
        pd.circle(canvas, dark, (cx + 5, cy - 1), 1.6)
        pd.circle(canvas, dark, (cx + 8, cy + 2), 1.6)
    else:
        pd.polygon(canvas, c, [(cx + 8, cy - 7), (cx - 6, cy), (cx + 8, cy + 7), (cx + 4, cy)])

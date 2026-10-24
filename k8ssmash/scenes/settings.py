"""The settings screen: master, effects and music volume, plus a few switches. Hold L/R on the title to open it."""
from __future__ import annotations

import pygame

from k8ssmash import ui
from k8ssmash.ui import pd
from k8ssmash.config import CANVAS_W, FPS
from k8ssmash.scenes.base import Scene

STEP = 0.05
REPEAT_DELAY, REPEAT_EVERY = 18, 3  # holding left/right keeps adjusting

ROWS = [
    ("master", "Master volume", "slider"),
    ("sfx", "Effects volume", "slider"),
    ("music", "Music volume", "slider"),
    ("mute", "Mute everything", "toggle"),
    ("colorblind", "Colorblind-safe colors", "toggle"),
    ("items", "Power-ups", "toggle"),
    ("fullscreen", "Fullscreen", "toggle"),
    ("aspect", "Screen shape", "choice"),
    ("size", "Window size", "choice"),
]
ASPECT_LABELS = {"auto": "Auto (fit screen)", "16:9": "16:9 (standard)", "21:9": "21:9 (ultrawide)"}


class Settings(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.row = 0
        self.frame = 0
        self.held_for = 0
        self.big = ui.UIFont(40)
        self.font = ui.UIFont(20)
        self.small = ui.UIFont(18)
        app.audio.music("select")

    # --- values --------------------------------------------------------------------------------
    def value(self, key: str):
        cfg = self.app.cfg
        return {"master": cfg.master_volume, "sfx": cfg.sfx_volume, "music": cfg.music_volume, "mute": cfg.muted,
                "colorblind": cfg.colorblind, "items": cfg.items, "fullscreen": cfg.fullscreen,
                "aspect": cfg.aspect, "size": (cfg.width, cfg.height)}[key]

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
            self.app.display.set_aspect(modes[(modes.index(cfg.aspect) + direction) % len(modes)])
        elif key == "size":
            sizes = self.app.display.sizes()
            cur = (cfg.width, cfg.height)
            idx = sizes.index(cur) if cur in sizes else 0
            self.app.display.set_size(*sizes[(idx + direction) % len(sizes)])

    # --- logic ---------------------------------------------------------------------------------
    def update(self) -> None:
        self.frame += 1
        players = self.app.input.players
        for inp in players:
            if "UP" in inp.pressed:
                self.row = (self.row - 1) % len(ROWS)
                self.app.audio.play("menu_move")
            if "DOWN" in inp.pressed:
                self.row = (self.row + 1) % len(ROWS)
                self.app.audio.play("menu_move")
        key, _, kind = ROWS[self.row]
        direction = 0
        for inp in players:
            if "RIGHT" in inp.pressed or "ATTACK" in inp.pressed and kind != "slider":
                direction = 1 if "RIGHT" in inp.pressed or kind == "choice" else (-1 if self.value(key) else 1)
            elif "LEFT" in inp.pressed:
                direction = -1
        held = any(inp.axis_x for inp in players)
        self.held_for = self.held_for + 1 if held else 0
        if not direction and kind == "slider" and self.held_for > REPEAT_DELAY and self.held_for % REPEAT_EVERY == 0:
            direction = next(inp.axis_x for inp in players if inp.axis_x)
        if direction:
            self.adjust(key, direction)
        if any(inp.pressed & {"START", "SPECIAL"} for inp in players) and self.frame > 10:
            self.app.audio.play("menu_select")
            self.app.cfg.save()
            self.app.go_title()

    # --- drawing -------------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        pd.blit(canvas, _background(), (0, 0))
        head = self.big.render("SETTINGS", False, (255, 224, 90))
        ui.blit_c(canvas, head, 18)
        panel = pygame.Rect(60, 62, 520, 252)
        ui.window_d(canvas, panel)
        for i, (key, label, kind) in enumerate(ROWS):
            y = panel.y + 10 + i * 26
            active = i == self.row
            if active:
                pd.rect(canvas, (60, 90, 200), (panel.x + 8, y - 3, panel.w - 16, 25), border_radius=4)
                pd.polygon(canvas, (255, 224, 90), [(panel.x + 16, y + 3), (panel.x + 16, y + 17), (panel.x + 26, y + 10)])
            pd.blit(canvas, self.font.render(label, False, (255, 255, 255) if active else (190, 200, 235)), (panel.x + 40, y))
            value = self.value(key)
            if kind == "slider":
                bar = pygame.Rect(panel.x + 270, y + 3, 170, 15)
                pd.rect(canvas, (8, 12, 40), bar, border_radius=3)
                filled = int(bar.w * value)
                for sx in range(0, filled - 2, 8):  # segmented neon bar
                    pd.rect(canvas, _hue(sx / bar.w), (bar.x + 2 + sx, bar.y + 2, 6, bar.h - 4))
                pd.rect(canvas, (150, 170, 230), bar, 1, border_radius=3)
                pct = self.font.render(f"{int(round(value * 100))}%", False, (255, 255, 255))
                pd.blit(canvas, pct, (bar.right + 12, y))
            elif kind == "choice":
                label_v = ASPECT_LABELS[value] if key == "aspect" else f"{value[0]} x {value[1]}"
                pd.blit(canvas, self.font.render(f"<  {label_v}  >", False, (255, 224, 140)), (panel.x + 270, y))
            else:
                on = bool(value)
                text = self.font.render("ON" if on else "OFF", False, (120, 255, 160) if on else (150, 156, 190))
                pd.blit(canvas, text, (panel.x + 290, y))
        hint = self.small.render("UP / DOWN choose     LEFT / RIGHT change     START or A: save and go back", False, (150, 166, 220))
        ui.blit_c(canvas, hint, 326)
_bg: pygame.Surface | None = None


def _background() -> pygame.Surface:
    global _bg
    if _bg is None:
        from k8ssmash.backdrops import dither_gradient
        from k8ssmash.config import WORLD_H, WORLD_W
        _bg = dither_gradient(WORLD_W, WORLD_H, [(0, (4, 6, 22)), (0.5, (10, 24, 80)), (1, (3, 6, 24))], bands=20)
    return _bg


def _hue(t: float) -> tuple[int, int, int]:
    """Slider colour: cool cyan at the quiet end, warm amber toward loud."""
    return (int(40 + 215 * t), int(220 - 80 * t), int(255 - 200 * t))

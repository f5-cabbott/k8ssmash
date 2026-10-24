"""Training mode: one human, one dummy, no stocks or clock. Tap START to reset, hold START to leave."""
from __future__ import annotations

import pygame

from k8ssmash.ai import SimpleAI
from k8ssmash.config import FPS, WORLD_H, WORLD_W
from k8ssmash.fighter import Fighter, FighterStats
from k8ssmash.input import PlayerInput
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.stage import Stage

DUMMY_MODES = ["Stand", "Shield", "Jump", "CPU"]
COMBO_WINDOW = 45  # frames between hits that still count as one combo
EXIT_HOLD = 90
TRAINING_IDLE = 120 * FPS


class Training(Battle):
    metrics_mode = "training"

    def __init__(self, app, stats: list[FighterStats], stage: Stage | None = None):
        super().__init__(app, stats, stage=stage, stocks=99, human=[True, False], items=False)
        self.frame = READY_FRAMES  # no countdown
        self.mode = 0
        self.start_hold = 0
        self.last_damage = 0.0
        self.combo = 0
        self.combo_damage = 0.0
        self.last_hit_frame = -999
        self.best_combo = 0
        self.ais = {1: SimpleAI(self.fighters[1], self.fighters[0], self.stage)}
        app.audio.music("training")

    # --- dummy behaviour -----------------------------------------------------------------
    def _inputs(self) -> list[PlayerInput]:
        mode = DUMMY_MODES[self.mode]
        held: set[str] = set()
        if mode == "Shield":
            held = {"SHIELD"}
        elif mode == "Jump" and self.frame % 70 == 0:
            held = {"JUMP"}
        elif mode == "CPU":
            held = self.ais[1].decide()
        self.cpu_inputs[1].update(held)
        return [self.app.input.players[0], self.cpu_inputs[1]]

    def reset(self) -> None:
        for f, spawn in zip(self.fighters, self.stage.spawns):
            f.spawn(spawn, 1 if f.slot == 0 else -1)
            f.percent = 0.0
            f.ko_timer = 0
        self.projectiles.clear()
        self.combo = 0
        self.combo_damage = 0.0

    # --- logic ---------------------------------------------------------------------------
    def update(self) -> None:
        players = self.app.input.players
        if "SELECT" in players[0].pressed and "START" not in players[0].held:
            self.mode = (self.mode + 1) % len(DUMMY_MODES)
        if "START" in players[0].held:
            self.start_hold += 1
        else:
            if "START" in players[0].released and 0 < self.start_hold < EXIT_HOLD:
                self.reset()  # a tap, not a hold
            self.start_hold = 0
        if self.start_hold >= EXIT_HOLD or self.app.idle_frames >= TRAINING_IDLE:
            from k8ssmash.scenes.select import CharacterSelect
            self.app.set_scene(CharacterSelect(self.app, training=True))
            return
        if self.fighters[1].percent > 999:
            self.fighters[1].percent = 0
        time_before = self.time_left
        super().update()
        self.time_left = time_before  # no clock
        self.winner = None
        self.fighters[0].stocks = self.fighters[1].stocks = 99
        for f in self.fighters:
            f.eliminated = False
        if self.combo and self.frame - self.last_hit_frame > COMBO_WINDOW:
            self.combo, self.combo_damage = 0, 0.0

    def _hit(self, victim: Fighter, attacker: Fighter, damage: float, base: float, growth: float,
             angle: float, direction: int) -> bool:
        before = victim.percent
        landed = super()._hit(victim, attacker, damage, base, growth, angle, direction)
        if landed and attacker is self.fighters[0] and victim.percent > before:
            gained = victim.percent - before
            self.last_damage = gained
            self.combo = self.combo + 1 if self.frame - self.last_hit_frame <= COMBO_WINDOW else 1
            self.combo_damage = gained if self.combo == 1 else self.combo_damage + gained
            self.best_combo = max(self.best_combo, self.combo)
            self.last_hit_frame = self.frame
        return landed

    # --- drawing -------------------------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        super().draw(canvas)
        lines = [
            f"TRAINING   dummy: {DUMMY_MODES[self.mode]}",
            f"last hit {self.last_damage:.1f}%   combo {self.combo} ({self.combo_damage:.0f}%)   best {self.best_combo}",
        ]
        for i, text in enumerate(lines):
            surf = self.font.render(text, False, (255, 235, 120) if i == 0 else (225, 230, 250), (10, 12, 28))
            canvas.blit(surf, ((canvas.get_width() - surf.get_width()) // 2, 44 + i * 20))
        hint = self.font.render("SELECT: dummy mode    START: reset    hold START: leave", False, (150, 160, 205))
        canvas.blit(hint, ((canvas.get_width() - hint.get_width()) // 2, WORLD_H - 20))

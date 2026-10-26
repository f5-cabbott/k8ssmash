"""How to play: short live demos of each skill. A scripted fighter performs the move on a dummy while the screen shows the
buttons. LEFT / RIGHT or A move between lessons, B leaves."""
from __future__ import annotations

import pygame

from k8ssmash import ui
from k8ssmash.config import FPS, RS
from k8ssmash.input import PlayerInput
from k8ssmash.roster import roster
from k8ssmash.scenes.base import Scene
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.stage import datacenter_stage
from k8ssmash.ui import pd

REST = 70  # frames to pause between runs of a lesson

# (title, two lines of text, buttons shown, start position or None for the usual spawn, script of (frames, held actions))
LESSONS = [
    ("MOVE AND JUMP", ("Push the D-pad to run. Tap Y or X to jump; tap again in the air to jump again.",
                       "Every fighter has several air jumps: use them to get back to the stage."),
     [("dpad", "right"), ("btn", "Y")], None,
     [(40, {"RIGHT"}), (3, {"RIGHT", "JUMP"}), (22, {"RIGHT"}), (3, {"RIGHT", "JUMP"}), (22, {"RIGHT"}), (3, {"RIGHT", "JUMP"}), (60, set())]),
    ("GLIDE", ("Hold Y or X while falling to glide and steer back toward the stage.",
               "Keep pushing toward the ledge: air control is strong."),
     [("dpad", "left"), ("btn", "Y")], (700, 250),
     [(3, {"JUMP"}), (40, {"LEFT"}), (80, {"LEFT", "JUMP"}), (60, {"LEFT"})]),
    ("ATTACK", ("B throws a quick jab. Hold a direction with B for stronger side, up and down attacks.",
                "Damage % builds up: the higher it is, the farther every hit sends them."),
     [("btn", "B"), ("dpad", "right")], None,
     [(34, {"RIGHT"}), (3, {"ATTACK"}), (22, set()), (3, {"ATTACK", "RIGHT"}), (50, set()), (3, {"ATTACK", "UP"}), (50, set())]),
    ("SPECIALS", ("A is your special move. With a direction it changes: side, up (a recovery move) or down.",
                  "Every fighter's four specials are listed on the fighter select screen."),
     [("btn", "A"), ("dpad", "up")], None,
     [(3, {"SPECIAL"}), (40, set()), (3, {"SPECIAL", "RIGHT"}), (40, set()), (3, {"SPECIAL", "UP"}), (70, set())]),
    ("SHIELD AND GRAB", ("Hold L or R to shield. Shield and press B to grab; a grab beats a shield.",
                         "Push a direction after the grab to throw forward, back, up or down."),
     [("btn", "L"), ("btn", "B")], None,
     [(34, {"RIGHT"}), (40, {"SHIELD"}), (3, {"SHIELD", "ATTACK"}), (14, set()), (3, {"RIGHT"}), (50, set())]),
    ("LEDGE HANG", ("Fall beside the edge of the stage and push toward it to catch the ledge.",
                    "You are safe for a moment while you hang. Push up or tap jump to climb back."),
     [("dpad", "right"), ("dpad", "up")], (150, 470),
     [(110, {"RIGHT"}), (6, set()), (3, {"UP"}), (70, set())]),
]


class Tutorial(Scene):
    def __init__(self, app, lesson: int = 0):
        super().__init__(app)
        self.lesson = lesson % len(LESSONS)
        self.frame = 0
        self.big = ui.UIFont(26)
        self.font = ui.UIFont(15)
        self.small = ui.UIFont(13)
        self.input = PlayerInput()
        self.dummy_input = PlayerInput()
        app.audio.music("training")
        self._start_lesson()

    # --- the live demo -------------------------------------------------------------------------
    def _start_lesson(self) -> None:
        r = roster()
        self.battle = Battle(self.app, [r[0], r[1]], stage=datacenter_stage(), human=[False, False], demo=True, items=False,
                             variants=[0, 0])
        b = self.battle
        b.frame = READY_FRAMES
        b.ais.clear()
        b._inputs = self._demo_inputs  # type: ignore[method-assign]
        _, _, _, start, _ = LESSONS[self.lesson]
        self.script_t = 0
        self.held: set[str] = set()
        self._place(start)

    def _place(self, start) -> None:
        f, d = self.battle.fighters
        f.spawn(self.battle.stage.spawns[0], 1)
        d.spawn((f.x + 150 if start is None else self.battle.stage.spawns[1][0] + 0, self.battle.stage.spawns[1][1]), -1)
        d.x = f.x + 90
        if start is not None:
            f.x, f.y = float(start[0]), float(start[1])
            f.vx = f.vy = 0.0
            if start[1] > 400:
                f.facing = 1
        f.percent = d.percent = 0.0
        self.battle.projectiles.clear()

    def _demo_inputs(self) -> list[PlayerInput]:
        script = LESSONS[self.lesson][4]
        total = sum(n for n, _ in script) + REST
        t = self.script_t % total
        held: set[str] = set()
        acc = 0
        for n, actions in script:
            if t < acc + n:
                held = actions
                break
            acc += n
        self.held = held
        self.input.update(held)
        self.dummy_input.update(set())
        if self.script_t % total == total - 1:
            self._place(LESSONS[self.lesson][3])
        self.script_t += 1
        return [self.input, self.dummy_input]

    # --- scene ---------------------------------------------------------------------------------
    def update(self) -> None:
        from k8ssmash.scenes.title import Title

        self.frame += 1
        b = self.battle
        b.update()
        b.time_left = 99 * FPS
        for f in b.fighters:
            f.stocks = 99
            f.eliminated = False
            if f.percent > 150:
                f.percent = 0.0
        b.winner = None
        players = self.app.input.players
        if self.frame > 8:
            if any(inp.pressed & {"RIGHT", "SPECIAL"} for inp in players):
                self.lesson = (self.lesson + 1) % len(LESSONS)
                self.app.audio.play("menu_move")
                self._start_lesson()
            elif any("LEFT" in inp.pressed for inp in players):
                self.lesson = (self.lesson - 1) % len(LESSONS)
                self.app.audio.play("menu_move")
                self._start_lesson()
            elif any(inp.pressed & {"ATTACK", "START"} for inp in players):
                self.app.audio.play("menu_select")
                self.app.set_scene(Title(self.app))

    def draw(self, canvas: pygame.Surface) -> None:
        self.battle.draw(canvas)
        title, lines, buttons, _, _ = LESSONS[self.lesson]
        panel = pygame.Rect(30, 8, 580, 70)
        ui.window_d(canvas, panel, accent=(255, 224, 90))
        pd.blit(canvas, self.big.render(f"{self.lesson + 1}/{len(LESSONS)}  {title}", False, (255, 224, 90)), (panel.x + 12, panel.y + 5))
        for i, text in enumerate(lines):
            pd.blit(canvas, ui.fit(text, (226, 232, 250), panel.w - 150, 13, 9), (panel.x + 12, panel.y + 30 + i * 16))
        x = panel.right - 120  # the buttons this lesson uses, lit while the demo presses them
        for kind, name in buttons:
            lit = {"right": "RIGHT", "left": "LEFT", "up": "UP", "Y": "JUMP", "B": "ATTACK", "A": "SPECIAL", "L": "SHIELD"}.get(name)
            if kind == "dpad":
                x += ui.dpad_glyph(canvas, x, panel.y + 20, name if lit in self.held else None, 1.1) + 8
            else:
                x += ui.button_glyph(canvas, x, panel.y + 20, name, 1.1) + 8
        hint = self.small.render("LEFT / RIGHT or A: next lesson        B: back to the title", False, (170, 182, 226))
        ui.blit_c(canvas, hint, 340)

"""A small CPU opponent, used for attract mode and for a lone player at the booth."""
from __future__ import annotations

import random

from k8ssmash.fighter import Fighter
from k8ssmash.stage import Stage


class SimpleAI:
    def __init__(self, me: Fighter, foe: Fighter, stage: Stage, seed: int | None = None):
        self.me, self.foe, self.stage = me, foe, stage
        self.rng = random.Random(seed)
        self.tap_cooldown = 0  # buttons must be released between presses to register
        self.pending: set[str] = set()

    def _pick_special(self, dist: float, toward: str, foe: Fighter) -> set[str]:
        moves = self.me.stats.moves
        options: list[set[str]] = []
        if dist > 70:
            options += [{"SPECIAL"}, {"SPECIAL"}]  # ranged neutral special
        if 40 < dist < 160:
            options.append({"SPECIAL", toward})  # side special (dash / blink / shot)
        if dist < 70:
            options.append({"SPECIAL", "DOWN"})  # down special (area / counter / buff)
        if foe.y < self.me.y - 50 and dist < 60:
            options.append({"SPECIAL", "UP"})
        return self.rng.choice(options) if options else {"SPECIAL"}

    def decide(self) -> set[str]:
        me, foe = self.me, self.foe
        held: set[str] = set()
        if not me.alive or not foe.alive:
            return held
        if self.tap_cooldown > 0:
            self.tap_cooldown -= 1
        solid = [pl.rect for pl in self.stage.live if not pl.dropthrough]
        main = min(solid, key=lambda r: abs(r.centerx - me.x))  # recover toward the nearest solid floor

        # Recovery: get back over the main platform first.
        off_left, off_right = me.x < main.left + 10, me.x > main.right - 10
        below = me.y > main.top + 4 and not me.on_ground
        if below or ((off_left or off_right) and not me.on_ground):
            held.add("RIGHT" if me.x < main.centerx else "LEFT")
            if me.vy > 0 and self.tap_cooldown == 0 and self.rng.random() < 0.5:
                held.add("JUMP")
                self.tap_cooldown = 6
            return held

        dx = foe.x - me.x
        dist = abs(dx)
        toward = "RIGHT" if dx > 0 else "LEFT"
        if dist > 36:
            held.add(toward)
        if me.on_ground and foe.y < me.y - 40 and self.tap_cooldown == 0 and self.rng.random() < 0.05:
            held.add("JUMP")
            self.tap_cooldown = 6
        if self.tap_cooldown == 0:
            roll = self.rng.random()
            if dist < 44 and roll < 0.12:
                held.add("ATTACK")
                if foe.y < me.y - 30:
                    held.add("UP")
                elif roll < 0.04:
                    held.add(toward)
                self.tap_cooldown = 8
            elif roll < 0.035 and me.move is None:
                held |= self._pick_special(dist, toward, foe)
                self.tap_cooldown = 20
        if foe.move is not None and dist < 50 and me.on_ground and self.rng.random() < 0.25:
            held = {"SHIELD"}
        return held

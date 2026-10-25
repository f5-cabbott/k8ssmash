"""Runtime sprite loading and animation frame selection."""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from k8ssmash.fighter import Fighter

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "sprites"


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


class SpriteSet:
    def __init__(self, name: str, alt: bool = False):
        tag = f"{slug(name)}{'_alt' if alt else ''}"
        meta = json.loads((ASSETS / f"{tag}.json").read_text())
        sheet = pygame.image.load(str(ASSETS / f"{tag}.png")).convert_alpha()
        self.size = meta["frame"]
        self.feet = tuple(meta["feet"])
        self.anims = meta["anims"]
        self.frames: dict[str, list[pygame.Surface]] = {}
        for anim, info in self.anims.items():
            self.frames[anim] = [
                sheet.subsurface((i * self.size, info["row"] * self.size, self.size, self.size)).copy()
                for i in range(info["frames"])]
        self._flipped: dict[tuple[str, int], pygame.Surface] = {}
        self._scaled: dict[tuple[str, int, int, int], pygame.Surface] = {}

    def get(self, anim: str, index: int, facing: int, scale: float = 1.0) -> pygame.Surface:
        frames = self.frames.get(anim) or self.frames["idle"]
        anim = anim if anim in self.frames else "idle"
        index %= len(frames)
        key = (anim, index, facing, round(scale * 100))
        surf = self._scaled.get(key)
        if surf is None:
            surf = frames[index]
            if facing < 0:
                surf = pygame.transform.flip(surf, True, False)
            if scale != 1.0:
                w = round(surf.get_width() * scale)
                surf = pygame.transform.scale(surf, (w, w))
            self._scaled[key] = surf
        return surf


_cache: dict[tuple[str, bool], SpriteSet | None] = {}


def sprite_set(name: str, alt: bool = False) -> SpriteSet | None:
    """A fighter's sprites. `alt` is the hue-rotated colour scheme used so a mirror match is readable."""
    key = (name, alt)
    if key not in _cache:
        try:
            _cache[key] = SpriteSet(name, alt)
        except (OSError, ValueError, KeyError, pygame.error):
            _cache[key] = None if not alt else sprite_set(name)
    return _cache[key]


def pick_frame(f: Fighter) -> tuple[str, int]:
    """Which animation and frame index a fighter should show right now."""
    state, n = f.state, f.anim_frame
    if state == "attack" and f.move is not None:
        m = f.move
        phase = 0 if f.move_frame < m.startup else 1 if f.move_frame < m.startup + m.active else 2
        return (m.anim or "jab"), phase
    if state == "run":
        return "run", (n * 16 // 60) % 8
    if state == "idle":
        if f.land_timer > 0:  # the squash after a landing, easing back up
            return "land", min(2, (6 - f.land_timer) // 2)
        if n % 210 < 8:  # a blink every few seconds
            return "idle", 6 + (n % 210) // 4
        return "idle", (n * 6 // 60) % 6
    if state == "djump":
        return "djump", min(3, n // 4)
    if state == "jump":
        return "jump", 0 if f.vy < -3.5 else 1
    if state == "fall":
        return "fall", 0 if f.vy < 5.0 else 1
    if state == "hurt":
        return "hurt", 0 if n < 5 else (1 if f.hitstun > 12 else 2)
    if state == "duck":
        return "duck", 0
    if state == "win":
        return "win", (n * 7 // 60) % 4
    return state, 0

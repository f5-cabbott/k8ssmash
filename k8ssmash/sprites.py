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
    def __init__(self, name: str):
        meta = json.loads((ASSETS / f"{slug(name)}.json").read_text())
        sheet = pygame.image.load(str(ASSETS / f"{slug(name)}.png")).convert_alpha()
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


_cache: dict[str, SpriteSet | None] = {}


def sprite_set(name: str) -> SpriteSet | None:
    if name not in _cache:
        try:
            _cache[name] = SpriteSet(name)
        except (OSError, ValueError, KeyError, pygame.error):
            _cache[name] = None
    return _cache[name]


def pick_frame(f: Fighter) -> tuple[str, int]:
    """Which animation and frame index a fighter should show right now."""
    state, n = f.state, f.anim_frame
    if state == "attack" and f.move is not None:
        m = f.move
        phase = 0 if f.move_frame < m.startup else 1 if f.move_frame < m.startup + m.active else 2
        return (m.anim or "jab"), phase
    if state == "run":
        return "run", (n * 14 // 60) % 6
    if state == "idle":
        return "idle", (n * 5 // 60) % 4
    if state == "djump":
        return "djump", min(2, n // 4)
    if state == "hurt":
        return "hurt", (n // 6) % 2
    return state, 0

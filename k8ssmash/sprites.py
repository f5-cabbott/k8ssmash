"""Runtime sprite loading and animation frame selection."""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from k8ssmash.config import RS

from k8ssmash.fighter import Fighter

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "sprites"


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


class SpriteSet:
    def __init__(self, name: str, variant: int | bool = 0):
        tag = f"{slug(name)}{VARIANT_TAGS[int(variant)]}"
        meta = json.loads((ASSETS / f"{tag}.json").read_text())
        sheet = pygame.image.load(str(ASSETS / f"{tag}.png")).convert_alpha()
        built = meta["frame"] // 96  # the sheets are drawn at some pixels-per-rig-unit; the game may run at another
        if built != RS:
            k = RS / built
            sheet = pygame.transform.smoothscale(sheet, (round(sheet.get_width() * k), round(sheet.get_height() * k)))
            meta = {**meta, "frame": round(meta["frame"] * k), "feet": [round(v * k) for v in meta["feet"]]}
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


VARIANT_TAGS = ("", "_alt", "_v2", "_v3")  # 0 is the original colours; 1 is the mirror-match scheme; 2 and 3 are extras
VARIANT_NAMES = ("Classic", "Twilight", "Sunset", "Lagoon")


def sprite_set(name: str, variant: int | bool = 0) -> SpriteSet | None:
    """A fighter's sprites in one of the colour variants (True means variant 1, for older callers)."""
    variant = int(variant)
    key = (name, variant)
    if key not in _cache:
        try:
            _cache[key] = SpriteSet(name, variant)
        except (OSError, ValueError, KeyError, pygame.error):
            _cache[key] = None if not variant else sprite_set(name)
    return _cache[key]


def resolve_variants(names: list[str], variants: list[int]) -> list[int]:
    """The colour variant each slot actually uses: a mirror match always gets two different schemes so it stays readable."""
    out = list(variants)
    if len(names) == 2 and names[0] == names[1] and out[0] == out[1]:
        out[1] = 1 if out[0] != 1 else 2
    return out


def sprite_frames(f: Fighter, anim: str) -> list:
    sprites = sprite_set(f.stats.name)
    return sprites.frames.get(anim, []) if sprites else [0, 0, 0, 0, 0, 0]


def pick_frame(f: Fighter) -> tuple[str, int]:
    """Which animation and frame index a fighter should show right now."""
    state, n = f.state, f.anim_frame
    if state == "attack" and f.move is not None:
        m = f.move
        anim = m.anim or "jab"
        n_frames = len(sprite_frames(f, anim))
        if n_frames < 6:  # the three-frame moves (counter, buff)
            phase = 0 if f.move_frame < m.startup else 1 if f.move_frame < m.startup + m.active else 2
            return anim, min(phase, n_frames - 1)
        if f.move_frame < m.startup:  # two frames of wind-up, two of strike, two of recovery
            return anim, 0 if f.move_frame < m.startup * 0.45 else 1
        if f.move_frame < m.startup + m.active:
            return anim, 2 if f.move_frame < m.startup + max(1, m.active * 0.55) else 3
        return anim, 4 if f.move_frame < m.startup + m.active + max(1, (m.total - m.startup - m.active) * 0.5) else 5
    if state == "run":
        return "run", (n * 20 // 60) % 12
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

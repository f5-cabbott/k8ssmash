"""Kubernetes-themed power-ups that drop onto the stage during a match."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable

import pygame

from k8ssmash.config import RS
from k8ssmash.ui import wd

from k8ssmash.config import FPS
from k8ssmash.fighter import BUFF_ARMOR, BUFF_GUARD, BUFF_HASTE, BUFF_POWER, BUFF_SCALED, Fighter
from k8ssmash.moves import ProjectileDef
from k8ssmash.stage import Stage

ITEM_SIZE = 16
ITEM_LIFE = 15 * FPS
FIRST_SPAWN = 7 * FPS
SPAWN_RANGE = (8 * FPS, 14 * FPS)
MAX_ITEMS = 2

DRONE = ProjectileDef(
    speed=0, width=12, height=12, damage=3, base_kb=2.2, kb_growth=0.02, angle=45, life=600,
    color=(190, 140, 255), shape="drone", orbit=True, hit_interval=24, replace_existing=True)
CHAOS_BOMB = ProjectileDef(
    speed=0, width=14, height=14, damage=0, base_kb=0, kb_growth=0, angle=0, life=90, gravity=0.3,
    spawn_dx=0, spawn_dy=-14, color=(240, 90, 60), shape="bomb", stick=True, explode_radius=60,
    explode_damage=16, harmless_to_owner=False, replace_existing=False)


@dataclass(frozen=True)
class ItemDef:
    key: str
    name: str  # announcer text
    glyph: str
    color: tuple[int, int, int]
    apply: Callable[[Fighter], None]


def _hpa(f: Fighter) -> None:
    f.add_buff(BUFF_POWER, 12 * FPS)
    f.add_buff(BUFF_SCALED, 12 * FPS)


def _sidecar(f: Fighter) -> None:
    f._fire(DRONE)


def _cordon(f: Fighter) -> None:
    f.add_buff(BUFF_ARMOR, 8 * FPS)


def _pdb(f: Fighter) -> None:
    f.add_buff(BUFF_GUARD, 12 * FPS)


def _chaos(f: Fighter) -> None:
    f._fire(CHAOS_BOMB)


def _undo(f: Fighter) -> None:
    f.percent = max(0.0, f.percent - 35)


def _probe(f: Fighter) -> None:
    f.add_buff(BUFF_HASTE, 10 * FPS)


ITEMS: dict[str, ItemDef] = {i.key: i for i in [
    ItemDef("hpa", "HPA: SCALED UP!", "H", (255, 130, 90), _hpa),
    ItemDef("sidecar", "SIDECAR INJECTED", "S", (190, 140, 255), _sidecar),
    ItemDef("cordon", "NODE CORDONED", "C", (255, 175, 60), _cordon),
    ItemDef("pdb", "PDB: PROTECTED", "P", (110, 235, 150), _pdb),
    ItemDef("chaos", "CHAOS BOMB!", "!", (240, 80, 70), _chaos),
    ItemDef("undo", "ROLLOUT UNDO", "R", (90, 200, 255), _undo),
    ItemDef("probe", "READINESS: GO!", "+", (255, 240, 120), _probe),
]}


@dataclass
class Item:
    defn: ItemDef
    x: float
    y: float  # bottom of the item
    vy: float = 0.0
    age: int = 0
    landed: bool = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - ITEM_SIZE / 2), int(self.y - ITEM_SIZE), ITEM_SIZE, ITEM_SIZE)

    @property
    def expiring(self) -> bool:
        return ITEM_LIFE - self.age < 3 * FPS

    def update(self, stage: Stage) -> None:
        self.age += 1
        if self.landed:
            return
        prev = self.y
        self.vy = min(self.vy + 0.22, 3.2)
        self.y += self.vy
        for plat in stage.live:
            r = plat.rect
            if r.left <= self.x <= r.right and prev <= r.top + 0.01 <= self.y:
                self.y, self.landed = float(r.top), True
                break


class ItemSpawner:
    def __init__(self, rng: random.Random | None = None, enabled: bool = True):
        self.rng = rng or random.Random()
        self.enabled = enabled
        self.items: list[Item] = []
        self.timer = FIRST_SPAWN

    def spawn(self, stage: Stage, key: str | None = None) -> Item:
        plat = self.rng.choice(stage.live)
        x = self.rng.uniform(plat.rect.left + 12, plat.rect.right - 12)
        defn = ITEMS[key] if key else self.rng.choice(list(ITEMS.values()))
        item = Item(defn, x, 10.0)
        self.items.append(item)
        return item

    def update(self, stage: Stage, fighters: list[Fighter]) -> list[tuple[Fighter, Item]]:
        """Advance items one frame; returns the (fighter, item) pickups that happened."""
        if self.enabled:
            self.timer -= 1
            if self.timer <= 0:
                if len(self.items) < MAX_ITEMS:
                    self.spawn(stage)
                self.timer = self.rng.randint(*SPAWN_RANGE)
        picked: list[tuple[Fighter, Item]] = []
        kept: list[Item] = []
        for item in self.items:
            item.update(stage)
            if item.age > ITEM_LIFE:
                continue
            taker = next((f for f in fighters if f.alive and f.hurtbox.colliderect(item.rect)), None)
            if taker is not None:
                item.defn.apply(taker)
                taker.say(item.defn.name)
                picked.append((taker, item))
            else:
                kept.append(item)
        self.items = kept
        return picked


def draw_item(canvas: pygame.Surface, item: Item, font: pygame.font.Font, frame: int) -> None:
    if item.expiring and (frame // 6) % 2 == 0:
        return
    bob = round(math.sin(frame * 0.12) * 2) if item.landed else 0
    cx, cy = round(item.x), round(item.y - ITEM_SIZE / 2) - 3 + bob
    pts = [(cx + math.cos(i * 2 * math.pi / 7 - math.pi / 2) * 9, cy + math.sin(i * 2 * math.pi / 7 - math.pi / 2) * 9)
           for i in range(7)]  # heptagon: the Kubernetes logo shape
    if item.landed:
        wd.ellipse(canvas, (0, 0, 0), (cx - 8, round(item.y) - 2, 16, 4))
    wd.polygon(canvas, (16, 12, 28), [(x + (x - cx) * 0.18, y + (y - cy) * 0.18) for x, y in pts])
    wd.polygon(canvas, item.defn.color, pts)
    wd.polygon(canvas, (255, 255, 255), pts, 1)
    glyph = font.render(item.defn.glyph, False, (20, 16, 36))
    canvas.blit(glyph, (cx * RS - glyph.get_width() // 2, cy * RS - glyph.get_height() // 2 + RS))

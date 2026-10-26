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
from k8ssmash.fighter import (BUFF_ARMOR, BUFF_CANARY, BUFF_GUARD, BUFF_HASTE, BUFF_POWER, BUFF_SCALED, BUFF_THROTTLED,
                              Fighter)
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
CHAOS_BOMB = ProjectileDef(  # lobbed ahead of the thrower; it can no longer hurt them
    speed=3.8, width=14, height=14, damage=0, base_kb=0, kb_growth=0, angle=0, life=80, gravity=0.3, vy=-4.4,
    spawn_dx=14, spawn_dy=-30, color=(240, 90, 60), shape="bomb", stick=True, explode_radius=64,
    explode_damage=15, harmless_to_owner=True, replace_existing=False)


@dataclass(frozen=True)
class ItemDef:
    key: str
    name: str  # what the picker shouts
    glyph: str  # a short tag drawn under the item
    color: tuple[int, int, int]
    apply: Callable[..., None]  # apply(picker, opponents)


def _hpa(f: Fighter, foes=()) -> None:
    f.add_buff(BUFF_POWER, 12 * FPS)
    f.add_buff(BUFF_SCALED, 12 * FPS)


def _sidecar(f: Fighter, foes=()) -> None:
    f._fire(DRONE)


def _cordon(f: Fighter, foes=()) -> None:
    f.add_buff(BUFF_ARMOR, 8 * FPS)


def _pdb(f: Fighter, foes=()) -> None:
    f.add_buff(BUFF_GUARD, 12 * FPS)


def _chaos(f: Fighter, foes=()) -> None:
    f._fire(CHAOS_BOMB)


def _undo(f: Fighter, foes=()) -> None:
    f.percent = max(0.0, f.percent - 35)


def _probe(f: Fighter, foes=()) -> None:
    f.add_buff(BUFF_HASTE, 10 * FPS)


def _canary(f: Fighter, foes=()) -> None:
    f.add_buff(BUFF_CANARY, 10 * FPS)


def _ratelimit(f: Fighter, foes=()) -> None:
    for o in foes:
        o.add_buff(BUFF_THROTTLED, 8 * FPS)


ITEMS: dict[str, ItemDef] = {i.key: i for i in [
    ItemDef("hpa", "HPA: BIGGER + STRONGER", "HPA", (255, 130, 90), _hpa),
    ItemDef("sidecar", "SIDECAR: HELPER DRONE", "SIDECAR", (190, 140, 255), _sidecar),
    ItemDef("cordon", "CORDON: ARMOR", "CORDON", (255, 175, 60), _cordon),
    ItemDef("pdb", "PDB: HALF DAMAGE", "PDB", (110, 235, 150), _pdb),
    ItemDef("chaos", "CHAOS BOMB!", "CHAOS", (240, 80, 70), _chaos),
    ItemDef("undo", "ROLLOUT UNDO: HEALED", "UNDO", (90, 200, 255), _undo),
    ItemDef("probe", "READINESS: SPEED", "PROBE", (255, 240, 120), _probe),
    ItemDef("canary", "CANARY: BIRD SHOTS", "CANARY", (255, 222, 70), _canary),
    ItemDef("ratelimit", "429: FOE THROTTLED", "429", (255, 96, 120), _ratelimit),
]}
BUFF_ITEM = {BUFF_POWER: "hpa", BUFF_ARMOR: "cordon", BUFF_GUARD: "pdb", BUFF_HASTE: "probe", BUFF_CANARY: "canary",
             BUFF_THROTTLED: "ratelimit"}  # which icon stands for which running buff


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
                item.defn.apply(taker, [o for o in fighters if o is not taker])
                taker.say(item.defn.name)
                picked.append((taker, item))
            else:
                kept.append(item)
        self.items = kept
        return picked


def _dark(c, k=0.35):
    return tuple(int(v * k) for v in c)


def draw_icon(canvas: pygame.Surface, key: str, cx: float, cy: float, r: float = 9.0, ring: float = 1.0) -> None:
    """One power-up's emblem on a dark disc: every item has its own shape so they can be told apart at a glance."""
    color = ITEMS[key].color
    white = (255, 255, 255)
    wd.circle(canvas, (14, 10, 34), (cx, cy), r + 1)
    wd.circle(canvas, _dark(color), (cx, cy), r)
    k = r / 9.0
    if key == "hpa":  # three chevrons stacked upward: scale up
        for i in range(3):
            y = cy + (3.6 - i * 3.4) * k
            wd.lines(canvas, white if i == 2 else color, False, [(cx - 4.4 * k, y), (cx, y - 3.2 * k), (cx + 4.4 * k, y)], 1.6)
    elif key == "sidecar":  # a little drone: body, rotor and eye
        wd.circle(canvas, white, (cx, cy + 1 * k), 3.6 * k)
        wd.line(canvas, color, (cx - 6 * k, cy - 3.6 * k), (cx + 6 * k, cy - 3.6 * k), 1.4)
        wd.line(canvas, color, (cx, cy - 3.6 * k), (cx, cy - 1.8 * k), 1.2)
        wd.circle(canvas, (30, 20, 60), (cx, cy + 1 * k), 1.4 * k)
    elif key in ("cordon", "pdb"):  # a shield; the PDB one carries a check mark
        pts = [(cx - 5 * k, cy - 5.6 * k), (cx + 5 * k, cy - 5.6 * k), (cx + 5 * k, cy + 0.8 * k), (cx, cy + 6.6 * k), (cx - 5 * k, cy + 0.8 * k)]
        wd.polygon(canvas, color, pts)
        wd.polygon(canvas, white, pts, 1)
        if key == "pdb":
            wd.lines(canvas, white, False, [(cx - 2.4 * k, cy), (cx - 0.6 * k, cy + 2.2 * k), (cx + 2.8 * k, cy - 2.4 * k)], 1.6)
        else:
            wd.line(canvas, white, (cx - 5 * k, cy - 1.4 * k), (cx + 5 * k, cy - 1.4 * k), 1.2)
    elif key == "chaos":  # a round bomb with a lit fuse
        wd.circle(canvas, (30, 24, 40), (cx - 0.6 * k, cy + 1.4 * k), 5 * k)
        wd.circle(canvas, white, (cx - 2.4 * k, cy - 0.6 * k), 1.1 * k)
        wd.lines(canvas, white, False, [(cx + 2 * k, cy - 2.4 * k), (cx + 4 * k, cy - 5 * k), (cx + 6 * k, cy - 4.6 * k)], 1.0)
        wd.circle(canvas, (255, 200, 80), (cx + 6.2 * k, cy - 4.8 * k), 1.5 * k)
    elif key == "undo":  # a circular arrow: roll back
        wd.arc(canvas, white, (cx - 5 * k, cy - 5 * k, 10 * k, 10 * k), 0.5, 5.2, 1.8)
        wd.polygon(canvas, white, [(cx + 5.6 * k, cy - 3.6 * k), (cx + 5.6 * k, cy + 1.6 * k), (cx + 1.2 * k, cy - 1.0 * k)])
    elif key == "probe":  # a lightning bolt: fast
        wd.polygon(canvas, color, [(cx + 1.6 * k, cy - 7 * k), (cx - 4.4 * k, cy + 1 * k), (cx - 0.4 * k, cy + 1 * k), (cx - 2 * k, cy + 7 * k),
                                   (cx + 4.4 * k, cy - 2 * k), (cx + 0.6 * k, cy - 2 * k)])
        wd.polygon(canvas, white, [(cx + 1.6 * k, cy - 7 * k), (cx - 4.4 * k, cy + 1 * k), (cx - 0.4 * k, cy + 1 * k), (cx - 2 * k, cy + 7 * k),
                                   (cx + 4.4 * k, cy - 2 * k), (cx + 0.6 * k, cy - 2 * k)], 1)
    elif key == "canary":  # a small yellow bird
        wd.circle(canvas, color, (cx - 0.6 * k, cy + 0.6 * k), 4.6 * k)
        wd.polygon(canvas, (255, 150, 50), [(cx + 3.8 * k, cy - 0.6 * k), (cx + 7 * k, cy + 0.6 * k), (cx + 3.8 * k, cy + 1.8 * k)])
        wd.circle(canvas, (30, 20, 40), (cx + 1.2 * k, cy - 1.2 * k), 0.9 * k)
        wd.ellipse(canvas, (240, 180, 40), (cx - 4.6 * k, cy + 0.4 * k, 4.6 * k, 3 * k))
        wd.polygon(canvas, color, [(cx - 3 * k, cy + 3 * k), (cx - 6.6 * k, cy + 5 * k), (cx - 2 * k, cy + 5 * k)])
    elif key == "ratelimit":  # a red stop sign with a bar: too many requests
        pts = [(cx + math.cos(i * math.pi / 4 + math.pi / 8) * 6.2 * k, cy + math.sin(i * math.pi / 4 + math.pi / 8) * 6.2 * k) for i in range(8)]
        wd.polygon(canvas, color, pts)
        wd.polygon(canvas, white, pts, 1)
        wd.rect(canvas, white, (cx - 3.6 * k, cy - 1 * k, 7.2 * k, 2 * k))
    wd.circle(canvas, color, (cx, cy), r, ring)


def draw_item(canvas: pygame.Surface, item: Item, font: pygame.font.Font, frame: int) -> None:
    if item.expiring and (frame // 6) % 2 == 0:
        return
    color = item.defn.color
    bob = round(math.sin(frame * 0.12) * 2) if item.landed else 0
    cx, cy = round(item.x), round(item.y - ITEM_SIZE / 2) - 4 + bob
    # a soft pillar of light from above, so a new item can be spotted from across the stage
    beam = pygame.Surface((14 * RS, max(1, int(item.y) * RS)), pygame.SRCALPHA)
    pygame.draw.rect(beam, (*color, 30), (0, 0, 14 * RS, beam.get_height()))
    pygame.draw.rect(beam, (*color, 55), (4 * RS, 0, 6 * RS, beam.get_height()))
    canvas.blit(beam, ((cx - 7) * RS, 0))
    if item.landed:
        wd.ellipse(canvas, (0, 0, 0), (cx - 8, round(item.y) - 2, 16, 4))
    pulse = 12 + 1.5 * math.sin(frame * 0.1)
    wd.circle(canvas, _dark(color, 0.5), (cx, cy), pulse, 1)
    draw_icon(canvas, item.defn.key, cx, cy, 9.5)
    tag = font.render(item.defn.glyph, False, color)
    canvas.blit(tag, (cx * RS - tag.get_width() // 2, (cy + 12) * RS))

"""The eight fighter designs: palettes, proportions, accessories and face/chest details."""
from __future__ import annotations

import math

import pygame

from k8ssmash.art.rig import WHITE, Color, ColorSet, Look, Rig, limb, with_back_palettes


def P(base: Color) -> ColorSet:
    dark = tuple(int(c * 0.6) for c in base)
    light = tuple(int(c + (255 - c) * 0.45) for c in base)
    return base, dark, light


def pt(p: tuple[float, float], dx: float = 0, dy: float = 0) -> tuple[int, int]:
    return round(p[0] + dx), round(p[1] + dy)


def eye(frame: pygame.Surface, x: int, y: int, w: int = 3, h: int = 4, look: int = 1) -> None:
    pygame.draw.rect(frame, (250, 250, 255), (x, y, w, h))
    pygame.draw.rect(frame, (20, 20, 40), (x + (w - 2 if look > 0 else 0), y + 1, 2, h - 1))


def poly(surf: pygame.Surface, pts: list[tuple[float, float]]) -> None:
    pygame.draw.polygon(surf, WHITE, [(round(x), round(y)) for x, y in pts])


# --- Pod ---------------------------------------------------------------------------------------
def pod() -> Look:
    pal = with_back_palettes({"body": P((70, 150, 255)), "leaf": P((90, 210, 110))})

    def sprout(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.line(s, WHITE, pt((cx, cy), 1, -8), pt((cx, cy), 2, -14), 2)
        poly(s, [(cx + 2, cy - 14), (cx + 11, cy - 17), (cx + 7, cy - 9)])

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(f, (225, 240, 255), (round(cx - 6), round(cy - 6), 17, 13))
        eye(f, round(cx + 1), round(cy - 3))
        eye(f, round(cx + 6), round(cy - 3))
        pygame.draw.line(f, (40, 60, 120), pt((cx, cy), 3, 3), pt((cx, cy), 7, 3), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 8
        pygame.draw.circle(f, (235, 245, 255), (round(hx), round(hy)), 4, 1)
        for i in range(7):
            a = i * 2 * math.pi / 7
            f.set_at((round(hx + math.cos(a) * 3), round(hy + math.sin(a) * 3)), (235, 245, 255))
        f.set_at((round(hx), round(hy)), (235, 245, 255))

    return Look("Pod", pal, head_r=11, torso_w=16, torso_h=15, leg_len=13, leg_w=6,
                head_pal="body", front=[(sprout, "leaf")], details=details)


# --- Helm --------------------------------------------------------------------------------------
def helm() -> Look:
    pal = with_back_palettes({
        "body": P((232, 190, 70)), "skin": P((240, 200, 160)), "hat": P((45, 55, 110)),
        "wood": P((150, 100, 55)), "pants": P((60, 70, 120)), "beard": P((140, 95, 60))})

    def wheel(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.shoulder[0] - 9, r.shoulder[1] + 5
        pygame.draw.circle(s, WHITE, (round(cx), round(cy)), 12, 3)
        for i in range(8):
            a = i * math.pi / 4
            pygame.draw.line(s, WHITE, (round(cx), round(cy)),
                             (round(cx + math.cos(a) * 15), round(cy + math.sin(a) * 15)), 2)

    def hat(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        poly(s, [(cx - 14, cy - 3), (cx - 3, cy - 12), (cx + 7, cy - 12), (cx + 15, cy - 3),
                 (cx + 6, cy - 6), (cx - 7, cy - 6)])

    def beard(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(s, WHITE, (round(cx - 3), round(cy + 1), 13, 10))

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        eye(f, round(cx + 1), round(cy - 3), 3, 3)
        eye(f, round(cx + 6), round(cy - 3), 3, 3)
        pygame.draw.line(f, (90, 60, 30), pt((cx, cy), 0, -5), pt((cx, cy), 4, -4), 1)
        pygame.draw.line(f, (90, 60, 30), pt((cx, cy), 5, -4), pt((cx, cy), 9, -5), 1)
        for i in range(3):
            f.set_at((round(r.hip[0] + 4 + r.pose.lean * (0.3 + i * .2)), round(r.hip[1] - 4 - i * 4)),
                     (255, 245, 190))

    return Look("Helm", pal, torso_w=19, torso_h=17, leg_len=14, leg_w=7, arm_w=6, head_r=9,
                leg_pal="pants", back=[(wheel, "wood")], front=[(beard, "beard"), (hat, "hat")],
                details=details)


# --- Kubectl -----------------------------------------------------------------------------------
def kubectl() -> Look:
    pal = with_back_palettes({
        "body": P((110, 235, 170)), "screen": P((28, 34, 50)), "metal": P((150, 160, 180)),
        "acc": P((255, 215, 90))})

    def antenna(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.line(s, WHITE, pt((cx, cy), -2, -8), pt((cx, cy), -4, -14), 2)
        pygame.draw.circle(s, WHITE, pt((cx, cy), -4, -15), 3)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        glow = (140, 255, 190)
        # ">_" prompt on the screen face
        pygame.draw.lines(f, glow, False, [pt((cx, cy), -1, -3), pt((cx, cy), 3, 0), pt((cx, cy), -1, 3)], 2)
        pygame.draw.line(f, glow, pt((cx, cy), 5, 3), pt((cx, cy), 8, 3), 2)
        hx, hy = r.hip[0] + r.pose.lean * 0.5, r.hip[1] - 9
        for i, c in enumerate(((255, 120, 110), (255, 215, 90), glow)):
            pygame.draw.rect(f, c, (round(hx - 4 + i * 4), round(hy), 3, 3))

    return Look("Kubectl", pal, head_style="box", head_w=22, head_h=16, head_r=9, torso_w=13, torso_h=16,
                leg_len=15, leg_w=5, arm_w=4, arm_len=16, head_pal="screen", limb_pal="metal",
                front=[(antenna, "acc")], details=details)


# --- Chaos Monkey ------------------------------------------------------------------------------
def monkey() -> Look:
    pal = with_back_palettes({
        "body": P((226, 128, 70)), "face": P((250, 214, 168)), "ear": P((236, 150, 100))})

    def tail(s: pygame.Surface, r: Rig) -> None:
        hx, hy = r.hip
        limb(s, [(hx - 5, hy), (hx - 13, hy + 2), (hx - 20, hy - 5), (hx - 19, hy - 15), (hx - 13, hy - 20)], 4)

    def ears(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.circle(s, WHITE, pt((cx, cy), -6, -3), 5)
        pygame.draw.circle(s, WHITE, pt((cx, cy), 5, -7), 4)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(f, (250, 214, 168), (round(cx - 1), round(cy - 4), 12, 11))
        eye(f, round(cx + 1), round(cy - 3), 3, 4)
        eye(f, round(cx + 6), round(cy - 3), 3, 4)
        pygame.draw.line(f, (150, 70, 40), pt((cx, cy), 3, 4), pt((cx, cy), 8, 4), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 8
        pygame.draw.ellipse(f, (250, 214, 168), (round(hx - 3), round(hy - 3), 8, 9))

    return Look("Chaos Monkey", pal, torso_w=13, torso_h=14, leg_len=13, leg_w=5, arm_w=5, arm_len=17,
                head_r=9, head_pal="body", back=[(tail, "body")], front=[(ears, "ear")], details=details)


# --- Sidecar -----------------------------------------------------------------------------------
def sidecar() -> Look:
    pal = with_back_palettes({
        "body": P((184, 136, 252)), "skin": P((245, 215, 185)), "steel": P((205, 208, 222)),
        "scarf": P((255, 205, 80))})

    def scarf(s: pygame.Surface, r: Rig) -> None:
        sx, sy = r.shoulder
        limb(s, [(sx, sy - 1), (sx - 8, sy + 1), (sx - 15, sy + 6 + math.sin(sx) * 2)], 4)

    def helmet(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(s, WHITE, (round(cx - 11), round(cy - 12), 22, 11))
        pygame.draw.rect(s, WHITE, (round(cx - 11), round(cy - 7), 22, 3))

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        for dx in (0, 7):
            pygame.draw.circle(f, (90, 200, 230), pt((cx, cy), 2 + dx, -3), 3)
            pygame.draw.circle(f, (240, 250, 255), pt((cx, cy), 3 + dx, -4), 1)
            pygame.draw.circle(f, (60, 50, 90), pt((cx, cy), 2 + dx, -3), 3, 1)
        pygame.draw.line(f, (150, 80, 70), pt((cx, cy), 4, 4), pt((cx, cy), 8, 4), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 7
        pygame.draw.rect(f, (255, 215, 90), (round(hx - 2), round(hy), 5, 4))

    return Look("Sidecar", pal, torso_w=14, torso_h=15, leg_len=14, head_r=9, head_pal="skin",
                back=[(scarf, "scarf")], front=[(helmet, "steel")], details=details)


# --- Ingress -----------------------------------------------------------------------------------
def ingress() -> Look:
    pal = with_back_palettes({
        "body": P((90, 215, 220)), "steel": P((190, 205, 220)), "dark": P((50, 70, 100))})

    def shield(s: pygame.Surface, r: Rig) -> None:
        hx, hy = r.hand_f
        x, y = hx + 2, hy - 4
        poly(s, [(x - 7, y + 14), (x - 7, y - 4), (x - 4, y - 12), (x + 4, y - 12), (x + 7, y - 4), (x + 7, y + 14)])

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.rect(f, (25, 35, 55), (round(cx - 1), round(cy - 3), 12, 4))
        pygame.draw.rect(f, (130, 245, 255), (round(cx + 3), round(cy - 2), 4, 2))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        pygame.draw.arc(f, (230, 250, 255), (round(hx - 4), round(hy - 3), 8, 8), 0, math.pi, 2)
        pygame.draw.line(f, (230, 250, 255), (round(hx - 4), round(hy + 1)), (round(hx - 4), round(hy + 5)), 1)
        pygame.draw.line(f, (230, 250, 255), (round(hx + 3), round(hy + 1)), (round(hx + 3), round(hy + 5)), 1)

    def crest(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        poly(s, [(cx - 3, cy - 9), (cx, cy - 17), (cx + 3, cy - 9)])

    return Look("Ingress", pal, torso_w=18, torso_h=16, leg_len=14, leg_w=6, arm_w=6, head_r=10,
                head_pal="steel", leg_pal="dark", front=[(crest, "body"), (shield, "steel")], details=details)


# --- Operator ----------------------------------------------------------------------------------
def operator() -> Look:
    pal = with_back_palettes({
        "body": P((255, 150, 190)), "skin": P((250, 215, 185)), "coat": P((240, 240, 250)),
        "dark": P((70, 70, 90)), "hair": P((130, 70, 110))})

    def coat(s: pygame.Surface, r: Rig) -> None:
        sx, sy = r.shoulder
        hx, hy = r.hip
        poly(s, [(sx - 5, sy), (hx - 5, hy + 2), (hx - 15 - abs(r.pose.lean) * 0.3, hy + 11), (hx - 4, hy + 11)])

    def hair(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(s, WHITE, (round(cx - 11), round(cy - 12), 21, 9))
        pygame.draw.circle(s, WHITE, pt((cx, cy), -9, -4), 4)
        pygame.draw.circle(s, WHITE, pt((cx, cy), 8, -12), 4)

    def headset(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.arc(s, WHITE, (round(cx - 10), round(cy - 13), 20, 20), 0.3, math.pi - 0.3, 2)
        pygame.draw.circle(s, WHITE, pt((cx, cy), -1, 0), 4)
        pygame.draw.line(s, WHITE, pt((cx, cy), -1, 3), pt((cx, cy), 5, 9), 2)
        pygame.draw.circle(s, WHITE, pt((cx, cy), 6, 9), 2)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        eye(f, round(cx + 1), round(cy - 2), 3, 4)
        eye(f, round(cx + 6), round(cy - 2), 3, 4)
        pygame.draw.line(f, (200, 90, 100), pt((cx, cy), 5, 5), pt((cx, cy), 8, 5), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        pygame.draw.rect(f, (255, 240, 250), (round(hx - 1), round(hy), 3, 6))

    return Look("Operator", pal, torso_w=14, torso_h=16, leg_len=15, leg_w=5, head_r=10, head_pal="skin",
                leg_pal="dark", back=[(coat, "coat")], front=[(hair, "hair"), (headset, "dark")],
                details=details)


# --- OOMKiller ---------------------------------------------------------------------------------
def oomkiller() -> Look:
    pal = with_back_palettes({
        "body": P((205, 60, 70)), "hood": P((70, 28, 60)), "bone": P((238, 232, 215)),
        "steel": P((185, 195, 215)), "wood": P((120, 80, 50))})

    def hood(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(s, WHITE, (round(cx - 12), round(cy - 13), 24, 25))

    def horns(s: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        poly(s, [(cx - 9, cy - 8), (cx - 14, cy - 18), (cx - 4, cy - 11)])
        poly(s, [(cx + 6, cy - 11), (cx + 12, cy - 19), (cx + 12, cy - 8)])

    def scythe(s: pygame.Surface, r: Rig) -> None:
        hx, hy = r.hand_f
        pygame.draw.line(s, WHITE, (round(hx - 2), round(hy + 14)), (round(hx + 3), round(hy - 34)), 3)

    def blade(s: pygame.Surface, r: Rig) -> None:
        hx, hy = r.hand_f
        poly(s, [(hx + 3, hy - 35), (hx + 17, hy - 31), (hx + 23, hy - 22), (hx + 12, hy - 27), (hx + 3, hy - 28)])

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.ellipse(f, (238, 232, 215), (round(cx - 3), round(cy - 8), 15, 15))
        pygame.draw.rect(f, (50, 20, 40), (round(cx), round(cy - 3), 4, 4))
        pygame.draw.rect(f, (50, 20, 40), (round(cx + 6), round(cy - 3), 4, 4))
        f.set_at((round(cx + 2), round(cy - 2)), (255, 70, 70))
        f.set_at((round(cx + 8), round(cy - 2)), (255, 70, 70))
        for i in range(4):
            f.set_at((round(cx + 1 + i * 3), round(cy + 5)), (60, 30, 50))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 10
        pygame.draw.line(f, (238, 232, 215), (round(hx - 3), round(hy)), (round(hx + 3), round(hy + 6)), 1)
        pygame.draw.line(f, (238, 232, 215), (round(hx + 3), round(hy)), (round(hx - 3), round(hy + 6)), 1)

    return Look("OOMKiller", pal, torso_w=19, torso_h=19, leg_len=14, leg_w=7, arm_w=6, head_r=10,
                head_pal="hood", front=[(horns, "bone"), (scythe, "wood"), (blade, "steel")], details=details)


LOOKS = {"Pod": pod, "Helm": helm, "Kubectl": kubectl, "Chaos Monkey": monkey, "Sidecar": sidecar,
         "Ingress": ingress, "Operator": operator, "OOMKiller": oomkiller}

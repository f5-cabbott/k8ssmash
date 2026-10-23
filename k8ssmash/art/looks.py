"""The eight fighter designs: palettes, proportions, accessories and face/chest details."""
from __future__ import annotations

import math

import pygame

from k8ssmash.art import draw
from k8ssmash.art.rig import Look, Rig, with_back_palettes


def pt(p, dx: float = 0, dy: float = 0) -> tuple[int, int]:
    return round(p[0] + dx), round(p[1] + dy)


def eye(f: pygame.Surface, x: int, y: int, w: int = 4, h: int = 5, iris=(70, 100, 210)) -> None:
    """A little glossy eye: white, colored iris looking forward, dark pupil and a glint."""
    pygame.draw.rect(f, (252, 252, 255), (x, y, w, h))
    pygame.draw.rect(f, iris, (x + w // 2 - 1, y + 1, w - w // 2 + 1, h - 1))
    pygame.draw.rect(f, (18, 16, 40), (x + w - 2, y + 2, 2, h - 2))
    f.set_at((x + w // 2, y + 1), (255, 255, 255))
    pygame.draw.line(f, (30, 24, 50), (x, y - 1), (x + w - 1, y - 1))  # lash line


# --- Pod ---------------------------------------------------------------------------------------
def pod() -> Look:
    pal = with_back_palettes({"body": (70, 150, 255), "leaf": (90, 210, 110), "face": (226, 240, 255)})

    def sprout(s, r: Rig) -> None:
        cx, cy = r.head
        draw.line(s, (cx + 1, cy - 8), (cx + 2, cy - 13), 2)
        draw.poly(s, [(cx + 2, cy - 14), (cx + 12, cy - 18), (cx + 7, cy - 9)])

    def face(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 6, cy - 6.5, 18, 14)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        eye(f, round(cx + 1), round(cy - 3), 4, 5, (60, 110, 230))
        eye(f, round(cx + 7), round(cy - 3), 4, 5, (60, 110, 230))
        pygame.draw.line(f, (50, 70, 140), pt((cx, cy), 3, 5), pt((cx, cy), 8, 5), 1)
        f.set_at(pt((cx, cy), 2, 4), (50, 70, 140))
        f.set_at(pt((cx, cy), 9, 4), (50, 70, 140))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 8
        for i in range(7):  # ship's-wheel emblem on the belly
            a = i * 2 * math.pi / 7
            f.set_at((round(hx + math.cos(a) * 3.2), round(hy + math.sin(a) * 3.2)), (240, 248, 255))
        f.set_at((round(hx), round(hy)), (240, 248, 255))
        pygame.draw.circle(f, (200, 226, 255), (round(hx), round(hy)), 5, 1)

    return Look("Pod", pal, head_r=11, torso_w=16, torso_h=15, leg_len=13, leg_w=6, head_pal="body",
                front=[(face, "face"), (sprout, "leaf")], details=details)


# --- Helm --------------------------------------------------------------------------------------
def helm() -> Look:
    pal = with_back_palettes({
        "body": (232, 190, 70), "skin": (240, 200, 160), "hat": (45, 55, 110), "wood": (150, 100, 55),
        "pants": (60, 70, 120), "beard": (150, 105, 66)})

    def wheel(s, r: Rig) -> None:
        cx, cy = r.shoulder[0] - 9, r.shoulder[1] + 5
        draw.circle(s, (cx, cy), 11, width=3)
        draw.circle(s, (cx, cy), 3)
        for i in range(8):
            a = i * math.pi / 4
            draw.line(s, (cx, cy), (cx + math.cos(a) * 13, cy + math.sin(a) * 13), 1.6)
            draw.circle(s, (cx + math.cos(a) * 14, cy + math.sin(a) * 14), 1.8)

    def wheel_hole(s, r: Rig) -> None:
        pass

    def hat(s, r: Rig) -> None:
        cx, cy = r.head
        draw.poly(s, [(cx - 14, cy - 3), (cx - 3, cy - 12), (cx + 7, cy - 12), (cx + 15, cy - 3),
                      (cx + 6, cy - 6), (cx - 7, cy - 6)])

    def beard(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 3, cy + 1, 13, 11)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        eye(f, round(cx + 1), round(cy - 3), 3, 4, (90, 70, 40))
        eye(f, round(cx + 6), round(cy - 3), 3, 4, (90, 70, 40))
        pygame.draw.line(f, (90, 60, 30), pt((cx, cy), 0, -5), pt((cx, cy), 4, -4), 1)
        pygame.draw.line(f, (90, 60, 30), pt((cx, cy), 5, -4), pt((cx, cy), 9, -5), 1)
        for i in range(3):
            f.set_at((round(r.hip[0] + 4 + r.pose.lean * (0.3 + i * .2)), round(r.hip[1] - 4 - i * 4)), (255, 245, 190))

    return Look("Helm", pal, torso_w=19, torso_h=17, leg_len=14, leg_w=7, arm_w=6, head_r=9, leg_pal="pants",
                back=[(wheel, "wood")], front=[(beard, "beard"), (hat, "hat")], details=details)


# --- Kubectl -----------------------------------------------------------------------------------
def kubectl() -> Look:
    pal = with_back_palettes({"body": (110, 235, 170), "screen": (28, 34, 50), "metal": (150, 160, 180),
                              "acc": (255, 215, 90)})

    def antenna(s, r: Rig) -> None:
        cx, cy = r.head
        draw.line(s, (cx - 2, cy - 8), (cx - 4, cy - 14), 2)
        draw.circle(s, (cx - 4, cy - 15), 3)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        glow = (140, 255, 190)
        pygame.draw.lines(f, glow, False, [pt((cx, cy), -1, -3), pt((cx, cy), 3, 0), pt((cx, cy), -1, 3)], 2)
        pygame.draw.line(f, glow, pt((cx, cy), 5, 3), pt((cx, cy), 8, 3), 2)
        hx, hy = r.hip[0] + r.pose.lean * 0.5, r.hip[1] - 9
        for i, c in enumerate(((255, 120, 110), (255, 215, 90), glow)):
            pygame.draw.rect(f, c, (round(hx - 4 + i * 4), round(hy), 3, 3))

    return Look("Kubectl", pal, head_style="box", head_w=22, head_h=16, head_r=9, torso_w=13, torso_h=16,
                leg_len=15, leg_w=5, arm_w=4, arm_len=16, head_pal="screen", limb_pal="metal",
                flat=("screen",), front=[(antenna, "acc")], details=details)


# --- Chaos Monkey ------------------------------------------------------------------------------
def monkey() -> Look:
    pal = with_back_palettes({"body": (226, 128, 70), "face": (250, 214, 168), "ear": (240, 160, 110)})

    def tail(s, r: Rig) -> None:
        hx, hy = r.hip
        draw.limb(s, [(hx - 5, hy), (hx - 13, hy + 2), (hx - 20, hy - 5), (hx - 19, hy - 15), (hx - 13, hy - 20)], 4)

    def ears(s, r: Rig) -> None:
        cx, cy = r.head
        draw.circle(s, (cx - 6, cy - 3), 5)
        draw.circle(s, (cx + 5, cy - 7), 4)

    def face(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 1, cy - 4.5, 12.5, 12)

    def belly(s, r: Rig) -> None:
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 8
        draw.ellipse(s, hx - 3, hy - 3, 8.5, 9.5)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        eye(f, round(cx + 1), round(cy - 3), 3, 4, (110, 70, 30))
        eye(f, round(cx + 6), round(cy - 3), 3, 4, (110, 70, 30))
        pygame.draw.line(f, (150, 70, 40), pt((cx, cy), 3, 5), pt((cx, cy), 8, 5), 1)
        f.set_at(pt((cx, cy), 5, 3), (150, 70, 40))

    return Look("Chaos Monkey", pal, torso_w=13, torso_h=14, leg_len=13, leg_w=5, arm_w=5, arm_len=17,
                head_r=9, head_pal="body", back=[(tail, "body")],
                front=[(ears, "ear"), (face, "face"), (belly, "face")], details=details)


# --- Sidecar -----------------------------------------------------------------------------------
def sidecar() -> Look:
    pal = with_back_palettes({"body": (184, 136, 252), "skin": (245, 215, 185), "steel": (205, 208, 222),
                              "scarf": (255, 205, 80)})

    def scarf(s, r: Rig) -> None:
        sx, sy = r.shoulder
        draw.limb(s, [(sx, sy - 1), (sx - 8, sy + 1), (sx - 15, sy + 6 + math.sin(sx) * 2)], 4)

    def helmet(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 11, cy - 12, 22, 11)
        draw.rect(s, cx - 11, cy - 7, 22, 3)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        for dx in (0, 7):
            pygame.draw.circle(f, (60, 50, 90), pt((cx, cy), 2 + dx, -2), 4)
            pygame.draw.circle(f, (90, 200, 230), pt((cx, cy), 2 + dx, -2), 3)
            pygame.draw.circle(f, (170, 235, 250), pt((cx, cy), 2 + dx, -3), 1)
            f.set_at(pt((cx, cy), 3 + dx, -4), (255, 255, 255))
        pygame.draw.line(f, (150, 80, 70), pt((cx, cy), 4, 5), pt((cx, cy), 8, 5), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 7
        pygame.draw.rect(f, (255, 215, 90), (round(hx - 2), round(hy), 5, 4))

    return Look("Sidecar", pal, torso_w=14, torso_h=15, leg_len=14, head_r=9, head_pal="skin",
                back=[(scarf, "scarf")], front=[(helmet, "steel")], details=details)


# --- Ingress -----------------------------------------------------------------------------------
def ingress() -> Look:
    pal = with_back_palettes({"body": (90, 215, 220), "steel": (190, 205, 220), "dark": (50, 70, 100)})

    def shield(s, r: Rig) -> None:
        hx, hy = r.hand_f
        x, y = hx + 2, hy - 4
        draw.poly(s, [(x - 7, y + 14), (x - 7, y - 4), (x - 4, y - 12), (x + 4, y - 12), (x + 7, y - 4), (x + 7, y + 14)])

    def crest(s, r: Rig) -> None:
        cx, cy = r.head
        draw.poly(s, [(cx - 3, cy - 9), (cx, cy - 17), (cx + 3, cy - 9)])

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.rect(f, (25, 35, 55), (round(cx - 1), round(cy - 3), 12, 4))
        pygame.draw.rect(f, (130, 245, 255), (round(cx + 3), round(cy - 2), 5, 2))
        f.set_at((round(cx + 4), round(cy - 2)), (240, 255, 255))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        pygame.draw.arc(f, (230, 250, 255), (round(hx - 4), round(hy - 3), 8, 8), 0, math.pi, 2)
        pygame.draw.line(f, (230, 250, 255), (round(hx - 4), round(hy + 1)), (round(hx - 4), round(hy + 5)), 1)
        pygame.draw.line(f, (230, 250, 255), (round(hx + 3), round(hy + 1)), (round(hx + 3), round(hy + 5)), 1)

    return Look("Ingress", pal, torso_w=18, torso_h=16, leg_len=14, leg_w=6, arm_w=6, head_r=10,
                head_pal="steel", leg_pal="dark", front=[(crest, "body"), (shield, "steel")], details=details)


# --- Operator ----------------------------------------------------------------------------------
def operator() -> Look:
    pal = with_back_palettes({"body": (255, 150, 190), "skin": (250, 215, 185), "coat": (240, 240, 250),
                              "dark": (70, 70, 90), "hair": (130, 70, 110)})

    def coat(s, r: Rig) -> None:
        sx, sy = r.shoulder
        hx, hy = r.hip
        draw.poly(s, [(sx - 5, sy), (hx - 5, hy + 2), (hx - 15 - abs(r.pose.lean) * 0.3, hy + 11), (hx - 4, hy + 11)])

    def hair(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 11, cy - 12, 21, 9)
        draw.circle(s, (cx - 9, cy - 4), 4)
        draw.circle(s, (cx + 8, cy - 12), 4)

    def headset(s, r: Rig) -> None:
        cx, cy = r.head
        draw.arc(s, cx - 10, cy - 13, 20, 20, 0.3, math.pi - 0.3, 2)
        draw.circle(s, (cx - 6, cy + 1), 3)
        draw.line(s, (cx - 6, cy + 3), (cx + 3, cy + 9), 1.6)
        draw.circle(s, (cx + 5, cy + 9), 1.8)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        eye(f, round(cx + 1), round(cy - 2), 3, 4, (150, 80, 130))
        eye(f, round(cx + 6), round(cy - 2), 3, 4, (150, 80, 130))
        pygame.draw.line(f, (200, 90, 100), pt((cx, cy), 5, 5), pt((cx, cy), 8, 5), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        pygame.draw.rect(f, (255, 240, 250), (round(hx - 1), round(hy), 3, 6))

    return Look("Operator", pal, torso_w=14, torso_h=16, leg_len=15, leg_w=5, head_r=10, head_pal="skin",
                leg_pal="dark", back=[(coat, "coat")], front=[(hair, "hair"), (headset, "dark")], details=details)


# --- OOMKiller ---------------------------------------------------------------------------------
def oomkiller() -> Look:
    pal = with_back_palettes({"body": (205, 60, 70), "hood": (84, 34, 74), "bone": (238, 232, 215),
                              "steel": (185, 195, 215), "wood": (130, 88, 54)})

    def horns(s, r: Rig) -> None:
        cx, cy = r.head
        draw.poly(s, [(cx - 9, cy - 8), (cx - 14, cy - 18), (cx - 4, cy - 11)])
        draw.poly(s, [(cx + 6, cy - 11), (cx + 12, cy - 19), (cx + 12, cy - 8)])

    def scythe(s, r: Rig) -> None:
        hx, hy = r.hand_f
        draw.line(s, (hx - 2, hy + 14), (hx + 3, hy - 34), 3)

    def blade(s, r: Rig) -> None:
        hx, hy = r.hand_f
        draw.poly(s, [(hx + 3, hy - 35), (hx + 17, hy - 31), (hx + 23, hy - 22), (hx + 12, hy - 27), (hx + 3, hy - 28)])

    def skull(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 3, cy - 8, 15, 15)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        pygame.draw.rect(f, (40, 14, 34), (round(cx), round(cy - 3), 4, 4))
        pygame.draw.rect(f, (40, 14, 34), (round(cx + 6), round(cy - 3), 4, 4))
        f.set_at((round(cx + 2), round(cy - 2)), (255, 90, 80))
        f.set_at((round(cx + 8), round(cy - 2)), (255, 90, 80))
        for i in range(4):
            f.set_at((round(cx + 1 + i * 3), round(cy + 5)), (70, 40, 60))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 10
        pygame.draw.line(f, (238, 232, 215), (round(hx - 3), round(hy)), (round(hx + 3), round(hy + 6)), 1)
        pygame.draw.line(f, (238, 232, 215), (round(hx + 3), round(hy)), (round(hx - 3), round(hy + 6)), 1)

    return Look("OOMKiller", pal, torso_w=19, torso_h=19, leg_len=14, leg_w=7, arm_w=6, head_r=10,
                head_pal="hood", front=[(skull, "bone"), (horns, "bone"), (scythe, "wood"), (blade, "steel")],
                details=details)


LOOKS = {"Pod": pod, "Helm": helm, "Kubectl": kubectl, "Chaos Monkey": monkey, "Sidecar": sidecar,
         "Ingress": ingress, "Operator": operator, "OOMKiller": oomkiller}

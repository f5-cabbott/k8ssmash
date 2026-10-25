"""The eight fighter designs: palettes, proportions, accessories, materials and expressive faces."""
from __future__ import annotations

import math

import pygame

from k8ssmash.art import draw
from k8ssmash.art.rig import Look, Rig, with_back_palettes

LASH = (30, 24, 50)


def pt(p, dx: float = 0, dy: float = 0) -> tuple[int, int]:
    return round(p[0] + dx), round(p[1] + dy)


# --- expressive face parts -------------------------------------------------------------------
def eye(f: pygame.Surface, x: int, y: int, w: int = 4, h: int = 5, iris=(70, 100, 210)) -> None:
    """A little glossy eye: white, colored iris looking forward, dark pupil and a glint."""
    pygame.draw.rect(f, (252, 252, 255), (x, y, w, h))
    pygame.draw.rect(f, iris, (x + w // 2 - 1, y + 1, w - w // 2 + 1, h - 1))
    pygame.draw.rect(f, (18, 16, 40), (x + w - 2, y + 2, 2, h - 2))
    f.set_at((x + w // 2, y + 1), (255, 255, 255))
    pygame.draw.line(f, LASH, (x, y - 1), (x + w - 1, y - 1))  # lash line


def eye_expr(f: pygame.Surface, x: int, y: int, w: int, h: int, face: str, iris, side: int) -> None:
    """One eye that changes with the expression. side 0 is the far eye, 1 the near eye."""
    if face == "blink":
        pygame.draw.line(f, LASH, (x, y + h // 2), (x + w - 1, y + h // 2))
    elif face == "happy":  # a joyful upside-down V
        pygame.draw.lines(f, LASH, False, [(x, y + h - 1), (x + w // 2, y + 1), (x + w - 1, y + h - 1)])
    elif face == "hurt":  # squeezed > <
        if side == 0:
            pygame.draw.lines(f, LASH, False, [(x, y), (x + w - 1, y + h // 2), (x, y + h - 1)])
        else:
            pygame.draw.lines(f, LASH, False, [(x + w - 1, y), (x, y + h // 2), (x + w - 1, y + h - 1)])
    elif face == "shock":  # wide eyes with pinprick pupils
        pygame.draw.rect(f, (252, 252, 255), (x - 1, y - 1, w + 2, h + 2))
        pygame.draw.rect(f, LASH, (x - 1, y - 2, w + 2, 1))
        f.set_at((x + w - 1, y + h // 2), (18, 16, 40))
    elif face in ("effort", "focus", "angry"):
        eye(f, x, y + 1, w, h - 1 if face == "angry" else h - 2, iris)
        pygame.draw.line(f, LASH, (x - 1, y), (x + w, y))  # heavy lid
        if face in ("angry", "effort"):  # brows slope in toward the nose
            if side == 0:
                pygame.draw.line(f, LASH, (x - 1, y - 2), (x + w, y))
            else:
                pygame.draw.line(f, LASH, (x, y), (x + w + 1, y - 2))
    else:
        eye(f, x, y, w, h, iris)


def mouth_expr(f: pygame.Surface, x: int, y: int, w: int, face: str, color=(150, 70, 80)) -> None:
    if face == "happy":
        pygame.draw.lines(f, color, False, [(x, y), (x + 1, y + 1), (x + w - 2, y + 1), (x + w - 1, y)])
    elif face in ("hurt", "shock"):
        pygame.draw.ellipse(f, (40, 12, 24), (x + w // 2 - 1, y - 1, 3, 4))
    elif face == "effort":
        pygame.draw.rect(f, (40, 12, 24), (x + 1, y - 1, max(2, w - 2), 3))
        pygame.draw.line(f, (250, 244, 240), (x + 1, y - 1), (x + w - 2, y - 1))  # clenched teeth
    elif face == "angry":
        pygame.draw.lines(f, color, False, [(x, y + 1), (x + 1, y), (x + w - 2, y), (x + w - 1, y + 1)])
    else:
        pygame.draw.line(f, color, (x, y), (x + w - 1, y))


def face(f, r: Rig, eyes: list[tuple[int, int]], size: tuple[int, int], iris, mouth: tuple[int, int, int] | None,
         mouth_color=(150, 70, 80)) -> None:
    """Draw eyes (and optionally a mouth) for the pose's expression. Coordinates are relative to the head centre."""
    cx, cy = r.head
    for i, (dx, dy) in enumerate(eyes):
        eye_expr(f, round(cx + dx), round(cy + dy), size[0], size[1], r.pose.face, iris, i)
    if mouth:
        mouth_expr(f, round(cx + mouth[0]), round(cy + mouth[1]), mouth[2], r.pose.face, mouth_color)


# --- Pod ---------------------------------------------------------------------------------------
def pod() -> Look:
    pal = with_back_palettes({"body": (70, 150, 255), "leaf": (150, 225, 255), "face": (226, 240, 255)})

    def tail_fin(s, r: Rig) -> None:  # a whale's flukes curling up behind: it swishes with the motion
        hx, hy = r.hip
        sw = math.sin(r.pose.lean * 0.7 + r.pose.bob) * 2.0 + r.pose.lean * 0.3
        draw.limb(s, [(hx - 4, hy), (hx - 11, hy + 1), (hx - 16 - sw, hy - 6), (hx - 15 - sw, hy - 13)], 4)
        draw.poly(s, [(hx - 15 - sw, hy - 13), (hx - 23 - sw, hy - 19), (hx - 20 - sw, hy - 12), (hx - 24 - sw, hy - 9),
                      (hx - 14 - sw, hy - 9)])

    def sprout(s, r: Rig) -> None:  # the water spout from the blowhole, drifting with the motion
        cx, cy = r.head
        sway = math.sin(r.pose.lean * 0.5 + r.pose.bob) * 1.5
        draw.line(s, (cx + 1, cy - 9), (cx + 2 + sway, cy - 14), 2)
        for dx, dy, rad in ((-4, -16, 1.8), (2, -19, 2.2), (8, -16, 1.8)):
            draw.circle(s, (cx + dx + sway * 1.4, cy + dy), rad)

    def belly(s, r: Rig) -> None:
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        draw.ellipse(s, hx - 2, hy - 5, 10, 13)

    def face_plate(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 6, cy - 6.5, 18, 14)

    def details(f: pygame.Surface, r: Rig) -> None:
        face(f, r, [(1, -3), (7, -3)], (4, 5), (60, 110, 230), (3, 5, 6), (50, 70, 140))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        for i in range(-1, 2):  # throat pleats of a baleen whale
            pygame.draw.line(f, (160, 196, 240), (round(hx + 1), round(hy + i * 3)), (round(hx + 6), round(hy + i * 3)), 1)

    return Look("Pod", pal, head_r=11, torso_w=16, torso_h=15, leg_len=13, leg_w=6, head_pal="body",
                no_hue_shift=("face", "leaf"), back=[(tail_fin, "body")],
                front=[(belly, "face"), (face_plate, "face"), (sprout, "leaf")], details=details)


# --- StatefulSet -------------------------------------------------------------------------------
def statefulset() -> Look:
    pal = with_back_palettes({
        "body": (240, 204, 58), "skin": (238, 196, 156), "hat": (236, 238, 244), "drum": (96, 132, 190),
        "pants": (70, 78, 112), "stache": (120, 82, 54), "boots": (92, 66, 46), "lock": (214, 218, 230)})

    def drum2(s, r: Rig) -> None:  # a second, smaller drum stacked on top: lots of persistent storage
        cx, cy = r.shoulder[0] - 9, r.shoulder[1] + 6
        draw.rect(s, cx - 5, cy - 24, 10, 10, radius=2)
        draw.ellipse(s, cx - 5, cy - 27, 10, 6)

    def padlock(s, r: Rig) -> None:
        hx, hy = r.hip[0] + r.pose.lean * 0.3 + 6, r.hip[1] - 3
        draw.rect(s, hx - 3, hy - 2, 7, 6, radius=1)

    def drum(s, r: Rig) -> None:  # a big persistent-volume drum strapped to his back
        cx, cy = r.shoulder[0] - 9, r.shoulder[1] + 6
        draw.rect(s, cx - 7, cy - 12, 14, 26, radius=3)
        draw.ellipse(s, cx - 7, cy - 15, 14, 7)

    def hoops(s, r: Rig) -> None:
        cx, cy = r.shoulder[0] - 9, r.shoulder[1] + 6
        for dy in (-6, 2, 9):
            draw.rect(s, cx - 7.5, cy + dy, 15, 2.2)

    def hard_hat(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 10, cy - 13, 20, 13)
        draw.rect(s, cx - 12, cy - 5, 25, 3, radius=1.5)  # the brim
        draw.rect(s, cx - 1.5, cy - 15, 3, 4)  # centre ridge

    def lamp(s, r: Rig) -> None:
        cx, cy = r.head
        draw.circle(s, (cx + 8, cy - 8), 2.6)

    def stache(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx + 1, cy + 2, 10, 4 + (2 if r.pose.face in ("hurt", "shock", "effort") else 0))

    def details(f: pygame.Surface, r: Rig) -> None:
        face(f, r, [(1, -3), (6, -3)], (3, 4), (90, 70, 40), None)
        cx, cy = r.head
        if r.pose.face not in ("angry", "effort", "hurt"):
            pygame.draw.line(f, (90, 60, 30), pt((cx, cy), 0, -5), pt((cx, cy), 4, -4), 1)
            pygame.draw.line(f, (90, 60, 30), pt((cx, cy), 5, -4), pt((cx, cy), 9, -5), 1)
        pygame.draw.circle(f, (255, 250, 200), pt((cx, cy), 8, -8), 1)  # the lamp lens
        hx, hy = r.hip[0] + r.pose.lean * 0.3, r.hip[1] - 4
        pygame.draw.line(f, (240, 244, 255), (round(hx - 8), round(hy - 6)), (round(hx + 8), round(hy - 6)), 1)  # reflective vest stripes
        pygame.draw.line(f, (240, 244, 255), (round(hx - 8), round(hy - 2)), (round(hx + 8), round(hy - 2)), 1)
        lx, ly = r.hip[0] + r.pose.lean * 0.3 + 6, r.hip[1] - 3
        pygame.draw.arc(f, (170, 176, 196), (round(lx - 2), round(ly - 6), 5, 7), 0, math.pi, 1)  # the padlock's shackle
        f.set_at((round(lx), round(ly + 1)), (60, 60, 80))
        dx, dy = r.shoulder[0] - 9, r.shoulder[1] + 6
        pygame.draw.rect(f, (255, 255, 255), (round(dx) - 3, round(dy) - 2, 6, 5))  # the drum's label
        pygame.draw.line(f, (60, 90, 150), (round(dx) - 2, round(dy)), (round(dx) + 2, round(dy)), 1)

    return Look("StatefulSet", pal, torso_w=19, torso_h=17, leg_len=14, leg_w=7, arm_w=6, head_r=9, leg_pal="pants",
                textures={"body": "cloth", "pants": "cloth", "drum": "metal", "hat": "metal"},
                no_hue_shift=("skin", "stache", "hat", "drum", "boots", "lock"),
                back=[(drum, "drum"), (drum2, "drum"), (hoops, "hat")],
                front=[(stache, "stache"), (hard_hat, "hat"), (lamp, "body"), (padlock, "lock")],
                details=details)


# --- Kubectl -----------------------------------------------------------------------------------
def kubectl() -> Look:
    pal = with_back_palettes({"body": (110, 235, 170), "screen": (28, 34, 50), "metal": (150, 160, 180),
                              "acc": (255, 215, 90)})

    def antenna(s, r: Rig) -> None:
        cx, cy = r.head
        wob = math.sin(r.pose.lean + r.pose.bob * 2) * 1.5
        draw.line(s, (cx - 2, cy - 8), (cx - 4 + wob, cy - 14), 2)
        draw.circle(s, (cx - 4 + wob, cy - 15), 3)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        glow = {"angry": (255, 120, 110), "hurt": (255, 210, 120), "shock": (255, 255, 255)}.get(r.pose.face, (140, 255, 190))
        x, y, ln = round(cx), round(cy), pygame.draw.line
        face = r.pose.face
        if face == "blink":
            ln(f, glow, (x - 2, y), (x + 2, y), 2); ln(f, glow, (x + 5, y + 3), (x + 8, y + 3), 2)  # "-_"
        elif face == "happy":
            pygame.draw.lines(f, glow, False, [(x - 3, y + 1), (x - 1, y - 2), (x + 1, y + 1)], 2)  # "^_^"
            pygame.draw.lines(f, glow, False, [(x + 3, y + 1), (x + 5, y - 2), (x + 7, y + 1)], 2)
        elif face == "hurt":  # "x_x"
            for ox in (-2, 4):
                ln(f, glow, (x + ox, y - 2), (x + ox + 3, y + 1), 1); ln(f, glow, (x + ox + 3, y - 2), (x + ox, y + 1), 1)
        elif face in ("effort", "angry"):  # ">_<"
            pygame.draw.lines(f, glow, False, [(x - 2, y - 3), (x + 2, y), (x - 2, y + 3)], 2)
            pygame.draw.lines(f, glow, False, [(x + 9, y - 3), (x + 5, y), (x + 9, y + 3)], 2)
        elif face == "shock":  # "O_O"
            pygame.draw.circle(f, glow, (x, y), 3, 1); pygame.draw.circle(f, glow, (x + 7, y), 3, 1)
        else:  # ">_" with a couple of lines of output above it
            pygame.draw.lines(f, glow, False, [(x - 1, y - 3), (x + 3, y), (x - 1, y + 3)], 2)
            ln(f, glow, (x + 5, y + 3), (x + 8, y + 3), 2)
            dim = tuple(int(c * 0.5) for c in glow)
            ln(f, dim, (x - 3, y - 6), (x + 6, y - 6), 1)
            ln(f, dim, (x - 3, y - 4), (x + 1, y - 4), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.5, r.hip[1] - 9
        for i, c in enumerate(((255, 120, 110), (255, 215, 90), (140, 255, 190))):
            pygame.draw.rect(f, c, (round(hx - 4 + i * 4), round(hy), 3, 3))

    return Look("Kubectl", pal, head_style="box", head_w=22, head_h=16, head_r=9, torso_w=13, torso_h=16,
                leg_len=15, leg_w=5, arm_w=4, arm_len=16, head_pal="screen", limb_pal="metal",
                flat=("screen",), textures={"metal": "metal", "body": "panel"}, no_hue_shift=("screen", "metal"),
                front=[(antenna, "acc")], details=details)


# --- Chaos Monkey ------------------------------------------------------------------------------
def monkey() -> Look:
    pal = with_back_palettes({"body": (226, 128, 70), "face": (250, 214, 168), "ear": (240, 160, 110),
                              "banana": (255, 222, 70)})

    def banana_hat(s, r: Rig) -> None:  # a banana worn like a jaunty hat
        cx, cy = r.head
        tilt = r.pose.lean * 0.3 + math.sin(r.pose.bob * 2) * 0.8
        draw.limb(s, [(cx - 8, cy - 7 - tilt), (cx - 3, cy - 14), (cx + 5, cy - 15 + tilt), (cx + 11, cy - 10 + tilt)], 4)

    def tail(s, r: Rig) -> None:
        hx, hy = r.hip
        sway = math.sin(r.pose.lean * 0.7 + r.pose.bob) * 2.5 + r.pose.lean * 0.4  # the tail swings against the motion
        draw.limb(s, [(hx - 5, hy), (hx - 13, hy + 2 - sway * 0.3), (hx - 20 - sway, hy - 5), (hx - 19 - sway * 1.4, hy - 15),
                      (hx - 13 - sway, hy - 20)], 4)

    def ears(s, r: Rig) -> None:
        cx, cy = r.head
        draw.circle(s, (cx - 6, cy - 3), 5)
        draw.circle(s, (cx + 5, cy - 7), 4)

    def face_patch(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 1, cy - 4.5, 12.5, 12)

    def belly(s, r: Rig) -> None:
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 8
        draw.ellipse(s, hx - 3, hy - 3, 8.5, 9.5)

    def details(f: pygame.Surface, r: Rig) -> None:
        face(f, r, [(1, -3), (6, -3)], (3, 4), (110, 70, 30), (3, 5, 5), (150, 70, 40))

    return Look("Chaos Monkey", pal, torso_w=13, torso_h=14, leg_len=13, leg_w=5, arm_w=5, arm_len=17,
                head_r=9, head_pal="body", textures={"body": "fur", "ear": "fur"}, no_hue_shift=("face", "banana"),
                back=[(tail, "body")], front=[(ears, "ear"), (face_patch, "face"), (belly, "face"), (banana_hat, "banana")],
                details=details)


# --- Sidecar -----------------------------------------------------------------------------------
def sidecar() -> Look:
    pal = with_back_palettes({"body": (184, 136, 252), "skin": (245, 215, 185), "steel": (205, 208, 222),
                              "scarf": (255, 205, 80)})

    def scarf(s, r: Rig) -> None:
        sx, sy = r.shoulder
        flutter = math.sin(r.pose.lean + r.pose.bob * 3) * 2 + max(0.0, r.pose.lean) * 0.5
        draw.limb(s, [(sx, sy - 1), (sx - 8, sy + 1 - flutter * 0.3), (sx - 15 - flutter * 0.5, sy + 6 + flutter)], 4)

    def drone_pos(r: Rig) -> tuple[float, float]:
        return r.shoulder[0] + 24 - r.pose.lean * 0.3, r.shoulder[1] - 12 + math.sin(r.pose.bob * 2) * 2

    def drone(s, r: Rig) -> None:  # the sidecar itself: a round little drone that follows along and bobs
        x, y = drone_pos(r)
        draw.circle(s, (x, y), 6)
        draw.line(s, (x, y - 5), (x - 1, y - 9), 1.4)
        draw.line(s, (x - 9, y + 1), (x + 9, y + 1), 1.6)  # stubby side rotors

    def helmet(s, r: Rig) -> None:
        cx, cy = r.head
        draw.ellipse(s, cx - 11, cy - 12, 22, 11)
        draw.rect(s, cx - 11, cy - 7, 22, 3)

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        lens = {"angry": (255, 100, 90), "effort": (255, 190, 80), "happy": (150, 255, 200), "shock": (255, 255, 255),
                "hurt": (150, 150, 170), "blink": (60, 70, 100), "focus": (70, 170, 210)}.get(r.pose.face, (90, 200, 230))
        for dx in (0, 7):
            pygame.draw.circle(f, (60, 50, 90), pt((cx, cy), 2 + dx, -2), 4)
            pygame.draw.circle(f, lens, pt((cx, cy), 2 + dx, -2), 3)
            if r.pose.face == "hurt":
                pygame.draw.line(f, (60, 50, 90), pt((cx, cy), dx, -4), pt((cx, cy), 4 + dx, 0)); pygame.draw.line(f, (60, 50, 90), pt((cx, cy), 4 + dx, -4), pt((cx, cy), dx, 0))
            elif r.pose.face == "blink":
                pygame.draw.line(f, (60, 50, 90), pt((cx, cy), dx, -2), pt((cx, cy), 4 + dx, -2))
            else:
                pygame.draw.circle(f, tuple(min(255, c + 80) for c in lens), pt((cx, cy), 3 + dx, -3), 1)
                f.set_at(pt((cx, cy), 3 + dx, -4), (255, 255, 255))
        if r.pose.face == "angry":
            pygame.draw.line(f, (60, 50, 90), pt((cx, cy), -1, -6), pt((cx, cy), 5, -4), 1)
            pygame.draw.line(f, (60, 50, 90), pt((cx, cy), 6, -4), pt((cx, cy), 12, -6), 1)
        mouth_expr(f, round(cx + 4), round(cy + 5), 5, r.pose.face, (150, 80, 70))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 7
        pygame.draw.rect(f, (255, 215, 90), (round(hx - 2), round(hy), 5, 4))
        dx, dy = drone_pos(r)  # the drone's single glowing eye and antenna light
        pygame.draw.circle(f, (30, 40, 70), (round(dx + 1), round(dy)), 3)
        pygame.draw.circle(f, lens, (round(dx + 1), round(dy)), 2)
        f.set_at((round(dx - 1), round(dy - 9)), (255, 120, 110))

    return Look("Sidecar", pal, torso_w=14, torso_h=15, leg_len=14, head_r=9, head_pal="skin",
                textures={"body": "cloth", "steel": "metal"}, no_hue_shift=("skin", "steel"),
                back=[(scarf, "scarf")], front=[(helmet, "steel"), (drone, "steel")], details=details)


# --- Ingress -----------------------------------------------------------------------------------
def ingress() -> Look:
    pal = with_back_palettes({"body": (90, 215, 220), "steel": (190, 205, 220), "dark": (50, 70, 100),
                              "cone": (255, 150, 40)})

    def shield(s, r: Rig) -> None:
        hx, hy = r.hand_f
        x, y = hx + 2, hy - 4
        draw.poly(s, [(x - 7, y + 14), (x - 7, y - 4), (x - 4, y - 12), (x + 4, y - 12), (x + 7, y - 4), (x + 7, y + 14)])

    def crest(s, r: Rig) -> None:
        cx, cy = r.head
        draw.poly(s, [(cx - 3, cy - 9), (cx, cy - 17), (cx + 3, cy - 9)])

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        x, y = round(cx), round(cy)
        face = r.pose.face
        pygame.draw.rect(f, (25, 35, 55), (x - 1, y - 3, 12, 4))
        color = {"angry": (255, 90, 80), "effort": (255, 190, 90), "hurt": (255, 255, 255), "shock": (255, 255, 255),
                 "happy": (150, 255, 210), "focus": (110, 220, 235), "blink": (50, 90, 110)}.get(face, (130, 245, 255))
        if face == "angry":
            pygame.draw.lines(f, color, False, [(x, y - 3), (x + 4, y - 1), (x + 9, y - 3)], 1)
        elif face == "happy":
            pygame.draw.lines(f, color, False, [(x + 1, y - 1), (x + 5, y - 3), (x + 9, y - 1)], 1)
        elif face in ("hurt", "shock"):
            pygame.draw.rect(f, color, (x + 3, y - 3, 3, 4))
        elif face == "blink":
            pygame.draw.line(f, color, (x + 3, y - 1), (x + 7, y - 1))
        else:
            pygame.draw.rect(f, color, (x + 3, y - 2, 5, 2))
            f.set_at((x + 4, y - 2), (240, 255, 255))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        pygame.draw.arc(f, (230, 250, 255), (round(hx - 4), round(hy - 3), 8, 8), 0, math.pi, 2)
        pygame.draw.line(f, (230, 250, 255), (round(hx - 4), round(hy + 1)), (round(hx - 4), round(hy + 5)), 1)
        pygame.draw.line(f, (230, 250, 255), (round(hx + 3), round(hy + 1)), (round(hx + 3), round(hy + 5)), 1)
        for gx in range(-2, 4, 2):  # portcullis bars across the gate
            pygame.draw.line(f, (40, 80, 100), (round(hx + gx), round(hy - 7)), (round(hx + gx), round(hy - 3)), 1)
        pygame.draw.line(f, (255, 255, 255), (round(cx - 2), round(cy - 12)), (round(cx + 2), round(cy - 12)), 1)  # the cone's stripe

    return Look("Ingress", pal, torso_w=18, torso_h=16, leg_len=14, leg_w=6, arm_w=6, head_r=10,
                head_pal="steel", leg_pal="dark", textures={"body": "panel", "steel": "metal"},
                no_hue_shift=("steel", "dark", "cone"), front=[(crest, "cone"), (shield, "steel")], details=details)


# --- Operator ----------------------------------------------------------------------------------
def operator() -> Look:
    pal = with_back_palettes({"body": (255, 150, 190), "skin": (250, 215, 185), "coat": (240, 240, 250),
                              "dark": (70, 70, 90), "hair": (130, 70, 110)})

    def coat(s, r: Rig) -> None:
        sx, sy = r.shoulder
        hx, hy = r.hip
        sw = max(0.0, r.pose.lean) * 0.8 + math.sin(r.pose.bob * 2) * 1.2  # coat tails trail behind a runner
        draw.poly(s, [(sx - 5, sy), (hx - 5, hy + 2), (hx - 15 - sw - abs(r.pose.lean) * 0.3, hy + 11), (hx - 4, hy + 11)])

    def hair(s, r: Rig) -> None:
        cx, cy = r.head
        bounce = math.sin(r.pose.bob * 2.5) * 1.2
        draw.ellipse(s, cx - 11, cy - 12, 21, 9)
        draw.circle(s, (cx - 9, cy - 4 + bounce), 4)
        draw.circle(s, (cx + 8, cy - 12 + bounce), 4)

    def cord(s, r: Rig) -> None:  # a patch cord from the switchboard, swinging with every step
        hx, hy = r.hip
        sw = math.sin(r.pose.bob * 2 + r.pose.lean * 0.5) * 2 + r.pose.lean * 0.4
        draw.limb(s, [(hx - 4, hy - 2), (hx - 12, hy + 2), (hx - 17 - sw, hy - 5), (hx - 22 - sw, hy - 1), (hx - 25 - sw, hy - 8)], 2)
        draw.rect(s, hx - 28 - sw, hy - 12, 6, 5, radius=1)  # the plug

    def headset(s, r: Rig) -> None:
        cx, cy = r.head
        draw.arc(s, cx - 10, cy - 13, 20, 20, 0.3, math.pi - 0.3, 2)
        draw.circle(s, (cx - 6, cy + 1), 3)
        draw.line(s, (cx - 6, cy + 3), (cx + 3, cy + 9), 1.6)
        draw.circle(s, (cx + 5, cy + 9), 1.8)

    def details(f: pygame.Surface, r: Rig) -> None:
        face(f, r, [(1, -2), (6, -2)], (3, 4), (150, 80, 130), (4, 5, 4), (200, 90, 100))
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 9
        pygame.draw.rect(f, (255, 240, 250), (round(hx - 1), round(hy), 3, 6))

    return Look("Operator", pal, torso_w=14, torso_h=16, leg_len=15, leg_w=5, head_r=10, head_pal="skin",
                leg_pal="dark", textures={"coat": "cloth", "body": "cloth"}, no_hue_shift=("skin", "coat", "dark"),
                back=[(coat, "coat"), (cord, "dark")], front=[(hair, "hair"), (headset, "dark")], details=details)


# --- OOMKiller ---------------------------------------------------------------------------------
def oomkiller() -> Look:
    pal = with_back_palettes({"body": (205, 60, 70), "hood": (84, 34, 74), "bone": (238, 232, 215),
                              "steel": (185, 195, 215), "wood": (130, 88, 54), "pcb": (52, 168, 104)})

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
        draw.ellipse(s, cx - 3, cy - 8, 15, 15 + (2 if r.pose.face in ("hurt", "shock", "effort") else 0))  # the jaw drops

    def details(f: pygame.Surface, r: Rig) -> None:
        cx, cy = r.head
        x, y = round(cx), round(cy)
        face = r.pose.face
        glow = {"angry": (255, 190, 90), "effort": (255, 150, 80), "happy": (150, 255, 160), "shock": (255, 255, 255),
                "hurt": (255, 255, 255), "focus": (255, 70, 70), "blink": (70, 20, 40)}.get(face, (255, 90, 80))
        for dx in (0, 6):
            pygame.draw.rect(f, (40, 14, 34), (x + dx, y - 3, 4, 4))
            if face == "hurt":
                pygame.draw.line(f, glow, (x + dx, y - 3), (x + dx + 3, y)); pygame.draw.line(f, glow, (x + dx + 3, y - 3), (x + dx, y))
            elif face == "happy":
                pygame.draw.lines(f, glow, False, [(x + dx, y), (x + dx + 1, y - 2), (x + dx + 3, y)])
            elif face == "shock":
                pygame.draw.rect(f, glow, (x + dx, y - 3, 4, 4))
                f.set_at((x + dx + 2, y - 1), (40, 14, 34))
            elif face == "blink":
                f.set_at((x + dx + 1, y - 1), glow)
            else:
                size = 2 if face in ("angry", "effort") else 1
                pygame.draw.rect(f, glow, (x + dx + 1, y - 2, size, size))
        if face in ("angry", "effort"):  # a heavy brow ridge
            pygame.draw.line(f, (60, 30, 50), (x - 1, y - 5), (x + 4, y - 3)); pygame.draw.line(f, (60, 30, 50), (x + 6, y - 3), (x + 11, y - 5))
        for i in range(4):  # teeth
            f.set_at((x + 1 + i * 3, y + 5 + (1 if face in ("hurt", "shock", "effort") else 0)), (70, 40, 60))
        bx, by = r.hand_f  # memory chips and gold contacts on the RAM-stick blade
        for i in range(3):
            pygame.draw.rect(f, (28, 34, 40), (round(bx + 6 + i * 4), round(by - 33 + i * 2), 3, 2))
        pygame.draw.line(f, (240, 200, 80), (round(bx + 5), round(by - 29)), (round(bx + 18), round(by - 27)), 1)
        hx, hy = r.hip[0] + r.pose.lean * 0.4, r.hip[1] - 10
        pygame.draw.line(f, (238, 232, 215), (round(hx - 3), round(hy)), (round(hx + 3), round(hy + 6)), 1)
        pygame.draw.line(f, (238, 232, 215), (round(hx + 3), round(hy)), (round(hx - 3), round(hy + 6)), 1)

    return Look("OOMKiller", pal, torso_w=19, torso_h=19, leg_len=14, leg_w=7, arm_w=6, head_r=10,
                head_pal="hood", textures={"body": "cloth", "hood": "cloth", "steel": "metal"},
                no_hue_shift=("bone", "steel", "wood", "pcb"),
                front=[(skull, "bone"), (horns, "bone"), (scythe, "wood"), (blade, "pcb")], details=details)


LOOKS = {"Pod": pod, "StatefulSet": statefulset, "Kubectl": kubectl, "Chaos Monkey": monkey, "Sidecar": sidecar,
         "Ingress": ingress, "Operator": operator, "OOMKiller": oomkiller}

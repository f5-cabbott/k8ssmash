"""The supporting cast, drawn by hand like Pod: each fighter has its own head contour, hat/hair/hood pieces, accessories,
palette and expressive face. Everything is in rig units, +x forward; shapes.py supplies the shared limb styles."""
from __future__ import annotations

import math

import pygame

from k8ssmash.art import draw, shapes
from k8ssmash.art.rig import Look, Rig, with_back_palettes
from k8ssmash.ui import wd


# --- shared helpers ------------------------------------------------------------------------------
def tp(r: Rig, t: float, side: float) -> tuple[float, float]:
    """A point on the torso: t from hip (0) to shoulder (1), side in half-widths (+ toward the belly)."""
    hx, hy = r.hip
    sx, sy = r.shoulder
    return (hx + (sx - hx) * t + side * r.look.torso_w * 0.5, hy + (sy - hy) * t)


def hp(r: Rig, base: float, pts):
    """Head-relative points, scaled so a contour authored for head_r == base fits any head size."""
    cx, cy = r.head
    k = r.look.head_r / base
    return [(cx + x * k, cy + y * k) for x, y in pts]


def ring(cx: float, cy: float, rx: float, ry: float, n: int = 14, phase: float = 0.0):
    return [(cx + math.cos(phase + i * 2 * math.pi / n) * rx, cy + math.sin(phase + i * 2 * math.pi / n) * ry) for i in range(n)]


def eye_hi(f: pygame.Surface, x: float, y: float, expr: str, near: bool, w: float = 4.8, h: float = 5.8,
           iris=((20, 50, 138), (74, 134, 232)), ink=(24, 36, 96), sclera=(252, 253, 255), lash: bool = True) -> None:
    """A hand-shaped eye: glossy sclera, a forward iris with a lighter lower half, pupil, glints, and lids that follow the
    expression. The same eye drawn at different sizes and colours gives every character a face."""
    if not near:
        w, h = w * 0.82, h * 0.86
    if expr == "shock":
        w, h = w + 0.8, h + 0.8
    if expr == "blink":
        wd.line(f, ink, (x - w / 2, y + 0.4), (x + w / 2, y + 0.4), 0.9)
        return
    if expr == "happy":
        wd.lines(f, ink, False, [(x - w / 2, y + 1.2), (x, y - 0.9), (x + w / 2, y + 1.2)], 0.9)
        return
    if expr == "hurt":
        sgn = 1 if near else -1
        wd.lines(f, ink, False, [(x - sgn * 1.5, y - 1.9), (x + sgn * 1.5, y + 0.1), (x - sgn * 1.5, y + 2.0)], 0.9)
        return
    wd.ellipse(f, sclera, (x - w / 2, y - h / 2, w, h))
    wd.ellipse(f, iris[0], (x - w / 2 + w * 0.36, y - h / 2 + h * 0.16, w * 0.6, h * 0.74))
    wd.ellipse(f, iris[1], (x - w / 2 + w * 0.42, y + h * 0.08, w * 0.48, h * 0.3))
    pr = 0.7 if expr == "shock" else max(0.8, w * 0.26)
    wd.ellipse(f, (6, 10, 36), (x + w * 0.16, y - h * 0.16, pr, pr * 1.45))
    wd.circle(f, (255, 255, 255), (x + w * 0.12, y - h * 0.28), max(0.4, w * 0.11))
    wd.circle(f, (255, 255, 255), (x + w * 0.4, y + h * 0.14), 0.28)
    wd.ellipse(f, ink, (x - w / 2, y - h / 2, w, h), 0.6)
    if expr in ("angry", "effort", "focus"):
        tilt = -1.1 if expr == "angry" else (-0.5 if near else 0.2)
        wd.line(f, ink, (x - w / 2 - 0.4, y - h / 2 + 0.7), (x + w / 2 + 0.4, y - h / 2 + 0.7 + tilt), 1.1)
    elif lash:
        wd.lines(f, ink, False, [(x - w / 2 - 0.3, y - h / 2 + 0.5), (x, y - h / 2 - 0.2), (x + w / 2 + 0.4, y - h / 2 + 0.3)], 1.0)


def mouth_hi(f: pygame.Surface, x: float, y: float, w: float, expr: str, ink=(60, 24, 40), inside=(120, 30, 56)) -> None:
    if expr in ("hurt", "shock"):
        wd.ellipse(f, inside, (x + w * 0.15, y - 0.6, w * 0.6, w * 0.7))
    elif expr == "happy":
        wd.lines(f, ink, False, [(x, y), (x + w * 0.2, y + 1.3), (x + w * 0.8, y + 1.3), (x + w, y - 0.3)], 0.8)
    elif expr in ("angry", "effort"):
        wd.lines(f, ink, False, [(x, y + 0.8), (x + w * 0.5, y), (x + w, y + 0.8)], 0.9)
    else:
        wd.lines(f, ink, False, [(x, y), (x + w * 0.5, y + 0.7), (x + w, y)], 0.7)


def brow(f: pygame.Surface, x0: float, x1: float, y: float, expr: str, ink, thick: float = 1.3) -> None:
    """A heavy brow over one eye that tilts with the mood."""
    tilt = {"angry": -1.6, "effort": -1.0, "focus": -0.5, "happy": 0.6, "hurt": 1.2, "shock": 1.0}.get(expr, 0.0)
    wd.line(f, ink, (x0, y - tilt * 0.4), (x1, y + tilt * 0.4), thick)


# --- StatefulSet: the site foreman with a drum on his back --------------------------------------
def statefulset() -> Look:
    pal = with_back_palettes({
        "body": (244, 190, 40), "skin": (240, 190, 148), "hat": (240, 242, 248), "band": (255, 124, 40), "drum": (88, 124, 186),
        "pants": (60, 70, 112), "stache": (116, 74, 46), "boots": (96, 66, 44), "belt": (122, 80, 48), "lock": (214, 218, 230),
        "lamp": (255, 248, 196), "buckle": (236, 200, 90), "hoop": (60, 84, 130)})

    def hard_hat(s, r):
        draw.smooth(s, hp(r, 10, [(-11, -4.4), (-10, -9.4), (-4.5, -13.6), (3.5, -13.8), (9.5, -10.4), (11.2, -4.6), (0, -3.8)]))

    def brim(s, r):
        draw.smooth(s, hp(r, 10, [(-12, -5.2), (-3, -6.0), (8, -6.0), (15, -4.8), (14.6, -2.8), (8, -3.8), (-3, -3.8), (-11.6, -3.4)]))

    def band(s, r):
        draw.smooth(s, hp(r, 10, [(-10.4, -8.4), (10, -8.4), (10.7, -6.4), (-10.8, -6.4)]))

    def lamp(s, r):
        cx, cy = r.head
        k = r.look.head_r / 10
        draw.circle(s, (cx + 9.2 * k, cy - 10.2 * k), 2.3 * k)

    def stache(s, r):
        open_ = 1.5 if r.pose.face in ("hurt", "shock", "effort") else 0.0
        draw.smooth(s, hp(r, 10, [(3, 3.4), (6, 2.6), (10.5, 3.0), (13, 4.4), (12, 6.4 + open_), (10.4, 5.2), (6.5, 5.2 + open_), (3.5, 5.8)]))

    def nose(s, r):
        draw.smooth(s, hp(r, 10, [(9.8, -2.0), (13.0, 0.2), (12.6, 3.0), (9.6, 3.2)]))

    def belt(s, r):
        draw.poly(s, [tp(r, 0.05, -0.95), tp(r, 0.05, 0.95), tp(r, 0.2, 0.98), tp(r, 0.2, -0.98)])

    def buckle(s, r):
        draw.smooth(s, [tp(r, 0.07, 0.62), tp(r, 0.07, 0.95), tp(r, 0.18, 0.95), tp(r, 0.18, 0.62)])

    def pouch(s, r):
        draw.smooth(s, [tp(r, 0.04, 0.0), tp(r, 0.04, 0.5), tp(r, 0.27, 0.52), tp(r, 0.27, 0.04)])

    def padlock(s, r):
        x, y = tp(r, 0.1, 1.05)
        draw.smooth(s, [(x - 2.6, y - 2), (x + 3, y - 2), (x + 3.4, y + 3.6), (x - 2.4, y + 3.8)])

    def drum(s, r):
        cx, cy = r.shoulder[0] - 10, r.shoulder[1] + 6
        draw.smooth(s, [(cx - 7, cy - 12), (cx - 3, cy - 13.4), (cx + 3, cy - 13.4), (cx + 7, cy - 12), (cx + 8.4, cy - 3), (cx + 8.4, cy + 7),
                        (cx + 6.6, cy + 13), (cx + 3, cy + 14), (cx - 3, cy + 14), (cx - 6.6, cy + 13), (cx - 8.4, cy + 7), (cx - 8.4, cy - 3)])
        draw.ellipse(s, cx - 7.2, cy - 15.6, 14.4, 6)

    def drum2(s, r):  # a second canister stacked on top: lots of persistent storage
        cx, cy = r.shoulder[0] - 10, r.shoulder[1] + 6
        draw.smooth(s, [(cx - 4.4, cy - 17), (cx + 4.4, cy - 17), (cx + 5, cy - 24), (cx + 3, cy - 26), (cx - 3, cy - 26), (cx - 5, cy - 24)])

    def hoops(s, r):
        cx, cy = r.shoulder[0] - 10, r.shoulder[1] + 6
        for dy in (-7, 2, 10):
            draw.smooth(s, [(cx - 8.6, cy + dy), (cx + 8.6, cy + dy), (cx + 8.8, cy + dy + 2.2), (cx - 8.8, cy + dy + 2.2)])

    def details(f, r):
        x, y = r.head
        k = r.look.head_r / 10
        e = r.pose.face
        eye_hi(f, x + 3.6 * k, y - 0.2 * k, e, True, 5.6, 6.0, iris=((70, 44, 20), (140, 96, 50)), ink=(60, 36, 20), lash=False)
        eye_hi(f, x + 9.6 * k, y - 0.1 * k, e, False, 5.6, 6.0, iris=((70, 44, 20), (140, 96, 50)), ink=(60, 36, 20), lash=False)
        brow(f, x + 1.0 * k, x + 6.2 * k, y - 3.0 * k, e, (70, 44, 26), 1.6)
        brow(f, x + 7.4 * k, x + 12 * k, y - 2.8 * k, e, (70, 44, 26), 1.6)
        wd.circle(f, (255, 255, 230), (x + 9.2 * k, y - 10.2 * k), 1.0 * k)  # the lamp lens
        for t in (0.5, 0.68):  # hi-vis reflective stripes across the vest
            a, b = tp(r, t, -0.5), tp(r, t, 0.85)
            wd.line(f, (246, 250, 255), a, b, 1.0)
        lx, ly = tp(r, 0.1, 1.05)
        wd.arc(f, (170, 176, 196), (lx - 2.2, ly - 6.2, 5.2, 7.2), 0, math.pi, 0.9)  # the padlock's shackle
        wd.circle(f, (50, 50, 70), (lx + 0.3, ly + 1.4), 0.7)

    return Look("StatefulSet", pal, torso_w=22, torso_h=18, leg_len=15, leg_w=7.6, arm_w=7, arm_len=17, head_r=10, leg_pal="pants", cartoon=0.85,
                head_fn=shapes.head([(-9, -3), (-6, -8), (0, -9.5), (7, -8), (10.5, -3), (11, 3), (9, 8), (3, 10), (-4, 9.5), (-8.5, 5)]),
                torso_fn=shapes.torso([(-0.05, 0), (0.02, -0.9), (0.45, -1.0), (0.85, -1.15), (1.05, -0.5), (1.05, 0.6), (0.85, 1.18), (0.45, 1.0), (0.04, 0.9)]),
                arm_fn=shapes.arm("glove", (1.2, 1.05, 0.95)), leg_fn=shapes.leg("boot", (1.25, 1.0, 0.9)),
                cel=("body", "skin", "pants", "boots", "hat", "stache", "drum", "belt"), plain=("lamp", "band", "hoop"),
                no_hue_shift=("skin", "stache", "hat", "drum", "boots", "lock", "belt", "lamp", "buckle", "band", "hoop"),
                back=[(drum, "drum"), (drum2, "drum"), (hoops, "hoop")],
                front=[(belt, "belt"), (pouch, "belt"), (buckle, "buckle"), (padlock, "lock"), (nose, "skin"), (stache, "stache"),
                       (hard_hat, "hat"), (band, "band"), (brim, "hat"), (lamp, "lamp")],
                details=details)


# --- Kubectl: a terminal on legs -----------------------------------------------------------------
def kubectl() -> Look:
    pal = with_back_palettes({"body": (96, 224, 168), "metal": (146, 158, 182), "screen": (12, 38, 48), "bezel": (64, 72, 94),
                              "glass": (150, 225, 215), "acc": (255, 214, 90)})

    def screen(s, r):
        draw.smooth(s, hp(r, 9, [(-9.4, -7.6), (9.4, -7.6), (10.4, -6.6), (10.4, 6.6), (9.4, 7.6), (-9.4, 7.6), (-10.4, 6.6), (-10.4, -6.6)]))

    def glass(s, r):
        draw.smooth(s, hp(r, 9, [(-8.5, -6.6), (-3, -6.6), (-6.5, -1.6), (-8.5, -1)]))

    def neck(s, r):
        draw.smooth(s, hp(r, 9, [(-4, 8), (4, 8), (5.2, 13), (-5.2, 13)]))

    def antenna(s, r):
        cx, cy = r.head
        wob = math.sin(r.pose.lean + r.pose.bob * 2) * 1.5
        draw.ribbon(s, [(cx - 3, cy - 10), (cx - 4 + wob * 0.5, cy - 14), (cx - 4 + wob, cy - 17)], [1.8, 1.4, 1.2])
        draw.circle(s, (cx - 4 + wob, cy - 18), 2.4)

    def chest(s, r):
        draw.poly(s, [tp(r, 0.28, -0.55), tp(r, 0.28, 0.75), tp(r, 0.82, 0.75), tp(r, 0.82, -0.55)])

    def pauldron(s, r):
        sx, sy = r.shoulder
        draw.smooth(s, ring(sx + 1, sy + 1.5, r.look.arm_w * 1.1, r.look.arm_w * 0.95, 10))

    def details(f, r):
        cx, cy = r.head
        k = r.look.head_r / 9
        e = r.pose.face
        col = {"angry": (255, 120, 110), "effort": (255, 190, 90), "hurt": (255, 255, 255), "shock": (255, 255, 255),
               "happy": (150, 255, 210), "focus": (110, 235, 220), "blink": (50, 120, 110)}.get(e, (120, 255, 200))
        dim = tuple(int(c * 0.45) for c in col)
        for ex in (-4.6, 3.6):  # the glowing eyes on the screen
            x, y = cx + (ex + 1.5) * k, cy - 1.6 * k
            if e in ("hurt",):
                wd.line(f, col, (x - 1.4, y - 1.6), (x + 1.4, y + 1.6), 1.0)
                wd.line(f, col, (x + 1.4, y - 1.6), (x - 1.4, y + 1.6), 1.0)
            elif e == "happy":
                wd.lines(f, col, False, [(x - 1.7, y + 1.2), (x, y - 1.2), (x + 1.7, y + 1.2)], 1.1)
            elif e == "blink":
                wd.line(f, col, (x - 1.7, y), (x + 1.7, y), 0.9)
            elif e == "shock":
                wd.circle(f, col, (x, y), 2.0, 0.9)
            else:
                h = 2.3 if e in ("angry", "effort") else 3.4
                wd.rect(f, dim, (x - 1.6, y - h / 2 - 0.5, 3.2, h + 1.0))
                wd.rect(f, col, (x - 1.2, y - h / 2, 2.4, h))
                if e == "angry":
                    wd.line(f, col, (x - 2.2, y - 3.0 - (0.6 if ex < 0 else -0.6)), (x + 2.2, y - 2.2 + (0.6 if ex < 0 else -0.6)), 0.9)
        mx, my = cx + 2.4 * k, cy + 4.0 * k
        mouth_hi(f, mx - 2.5, my, 5, e, ink=col, inside=col)
        wd.line(f, dim, (cx - 8 * k, cy + 6.2 * k), (cx - 3 * k, cy + 6.2 * k), 0.6)  # a prompt line, ">_"
        for i, c in enumerate(((255, 120, 110), (255, 214, 90), (140, 255, 190))):  # status LEDs on the chest plate
            x, y = tp(r, 0.7 - i * 0.14, 0.1)
            wd.circle(f, c, (x, y), 1.0)
            wd.circle(f, (255, 255, 255), (x - 0.3, y - 0.3), 0.3)
        a, b = tp(r, 0.34, -0.4), tp(r, 0.34, 0.6)
        wd.line(f, (30, 36, 54), a, b, 0.7)

    return Look("Kubectl", pal, torso_w=13, torso_h=16, leg_len=15, leg_w=5, arm_w=4, arm_len=16, head_r=9, cartoon=0.4,
                head_pal="bezel", limb_pal="metal", textures={"metal": "metal"}, cel=("body", "bezel"), plain=("screen", "glass"),
                no_hue_shift=("screen", "metal", "bezel", "glass", "acc"),
                head_fn=shapes.head([(-12, -7), (-9, -10.5), (9, -10.5), (12, -7), (12, 7), (9, 10.5), (-9, 10.5), (-12, 7)], 9.0, hard=True),
                torso_fn=shapes.torso([(0, -0.7), (0.1, -0.95), (0.9, -1.05), (1.05, -0.8), (1.05, 0.8), (0.9, 1.05), (0.1, 0.95), (0, 0.7)], hard=True),
                arm_fn=shapes.arm("mech", (1.0, 0.85, 0.8)), leg_fn=shapes.leg("piston", (1.1, 0.9, 0.85)),
                back=[(neck, "metal")], front=[(chest, "bezel"), (pauldron, "metal"), (screen, "screen"), (glass, "glass"), (antenna, "acc")],
                details=details)


# --- CronJob: an alarm-clock trickster ------------------------------------------------------------
def cronjob() -> Look:
    pal = with_back_palettes({"body": (244, 164, 52), "face": (252, 246, 226), "bell": (255, 206, 70), "key": (200, 206, 224),
                              "spring": (150, 160, 190), "rim": (255, 214, 96), "sneaker": (246, 246, 252)})

    def bell(cx, cy, w, h):
        return [(cx - w, cy), (cx - w * 0.84, cy - h * 0.66), (cx, cy - h), (cx + w * 0.84, cy - h * 0.66), (cx + w, cy), (cx, cy + h * 0.2)]

    def bells(s, r):
        cx, cy = r.head
        k = r.look.head_r / 9
        rattle = math.sin(r.pose.bob * 4) * 1.0 + r.pose.lean * 0.12
        draw.smooth(s, bell(cx - 5.4 * k - rattle * 0.3, cy - 9.2 * k + rattle * 0.3, 4.4 * k, 4.6 * k))
        draw.smooth(s, bell(cx + 6.4 * k - rattle * 0.3, cy - 9.0 * k - rattle * 0.3, 4.4 * k, 4.6 * k))
        draw.ribbon(s, [(cx - 3 * k, cy - 11.4 * k), (cx + 0.5 * k, cy - 13 * k), (cx + 4 * k, cy - 11.2 * k)], [1.4, 1.5, 1.4])  # the striker

    def rim(s, r):
        cx, cy = r.head
        k = r.look.head_r / 9
        draw.smooth(s, ring(cx + 1.4 * k, cy + 0.6 * k, 10.4 * k, 10.4 * k, 16))

    def dial(s, r):
        cx, cy = r.head
        k = r.look.head_r / 9
        draw.smooth(s, ring(cx + 1.4 * k, cy + 0.6 * k, 8.4 * k, 8.4 * k, 16))

    def key(s, r):  # a wind-up key that turns in the back
        hx, hy = r.hip
        sx, sy = r.shoulder
        a = r.pose.bob * 2.2
        kx, ky = (hx + sx) / 2 - 9, (hy + sy) / 2
        draw.line(s, (kx + 6, ky), (kx - 1, ky), 1.8)
        draw.smooth(s, ring(kx - 4, ky, 3.6, 1.6 + 3.2 * abs(math.cos(a)), 10))

    def spring(s, r):  # a coiled-spring tail that bounces behind
        hx, hy = r.hip
        sway = math.sin(r.pose.bob * 2 + r.pose.lean * 0.5) * 2 + r.pose.lean * 0.4
        pts = [(hx - 5, hy)]
        for i in range(1, 7):
            pts.append((hx - 5 - i * 3.0 - sway * i * 0.15, hy - 1 - i * 2.0 + (3.2 if i % 2 else -3.2)))
        draw.limb(s, pts, 2.2)
        draw.circle(s, pts[-1], 2.6)

    def details(f, r):
        cx, cy = r.head
        k = r.look.head_r / 9
        e = r.pose.face
        ox, oy = cx + 1.4 * k, cy + 0.6 * k
        for i in range(12):  # hour ticks around the dial
            a = i * math.pi / 6
            big = i % 3 == 0
            wd.line(f, (150, 100, 60), (ox + math.cos(a) * (7.2 if big else 7.6) * k, oy + math.sin(a) * (7.2 if big else 7.6) * k),
                    (ox + math.cos(a) * 8.2 * k, oy + math.sin(a) * 8.2 * k), 0.8 if big else 0.5)
        hour, minute = {"angry": (-2.2, -2.9), "hurt": (-1.2, 1.0), "happy": (-1.9, -2.5)}.get(e, (-2.1, -1.5))
        wd.line(f, (90, 56, 40), (ox + 0.8, oy + 4.6 * k), (ox + 0.8 + hour * 0.4, oy + 4.6 * k + hour * 0.3), 0.8)  # little hands under the chin
        eye_hi(f, cx + 0.2 * k, cy - 1.8 * k, e, True, 4.4, 5.2, iris=((110, 56, 12), (230, 156, 44)), ink=(86, 52, 30))
        eye_hi(f, cx + 6.4 * k, cy - 1.6 * k, e, False, 4.4, 5.2, iris=((110, 56, 12), (230, 156, 44)), ink=(86, 52, 30))
        mouth_hi(f, cx + 1.8 * k, cy + 4.4 * k, 4.2, e, ink=(120, 60, 50))
        hx, hy = tp(r, 0.38, 0.55)
        wd.circle(f, (252, 250, 240), (hx, hy), 3.0)  # a little belly dial
        wd.circle(f, (150, 110, 70), (hx, hy), 3.0, 0.5)
        wd.line(f, (90, 60, 40), (hx, hy), (hx, hy - 1.8), 0.6)
        wd.line(f, (200, 50, 50), (hx, hy), (hx + 1.6, hy + 0.3), 0.6)

    return Look("CronJob", pal, torso_w=13, torso_h=14, leg_len=13, leg_w=5, arm_w=5, arm_len=17, head_r=9, head_pal="body", cartoon=0.5,
                limb_pal="body", leg_pal="body", cel=("body", "face", "bell", "rim", "sneaker"), textures={"key": "metal"},
                no_hue_shift=("face", "bell", "key", "spring", "rim", "sneaker"),
                head_fn=shapes.head([(-10, 0), (-8, -7), (-2, -10), (5, -9), (10, -4), (10.5, 3), (7, 8.5), (0, 10), (-7, 8)], 9.0),
                torso_fn=shapes.torso([(-0.05, 0), (0.05, -0.95), (0.5, -0.85), (0.9, -0.75), (1.05, -0.2), (1.0, 0.55), (0.8, 0.95), (0.4, 1.05), (0.05, 0.9)]),
                arm_fn=shapes.arm("glove", (1.0, 0.85, 0.8)), leg_fn=shapes.leg("sneaker", (1.15, 0.9, 0.8)),
                back=[(spring, "spring"), (key, "key")], front=[(rim, "rim"), (dial, "face"), (bells, "bell")], details=details)


# --- Sidecar: a goggled pilot with a drone buddy ------------------------------------------------------
def sidecar() -> Look:
    pal = with_back_palettes({"body": (176, 128, 248), "skin": (246, 216, 186), "steel": (206, 210, 226), "scarf": (255, 200, 70),
                              "cap": (232, 236, 246), "brass": (214, 170, 70), "strap": (72, 56, 98), "lens": (214, 246, 255),
                              "fluff": (252, 252, 255)})

    def cap(s, r):
        draw.smooth(s, hp(r, 9, [(-10, -1.5), (-9, -8), (-3, -11.8), (5, -11), (10, -6.5), (10, -3.6), (3, -5), (-4, -4.5), (-8, -1)]))

    def flap(s, r):
        draw.smooth(s, hp(r, 9, [(-10, -1.5), (-6.5, -2.5), (-4.6, 2.5), (-6.5, 8), (-9.8, 6.5), (-10.8, 2)]))

    def fluff(s, r):
        draw.smooth(s, hp(r, 9, [(-8.5, -1.5), (-3, -4.2), (4, -4.4), (10, -3.4), (10.2, -1.6), (4, -2.6), (-3, -2.4)]))

    def strap(s, r):
        draw.poly(s, hp(r, 9, [(-10, -3.0), (0, -2.6), (0, -0.8), (-10, -1.2)]))

    def rims(s, r):
        for ex in (2.6, 8.8):
            draw.smooth(s, hp(r, 9, [(ex + math.cos(a) * 4.0, -0.6 + math.sin(a) * 4.2) for a in [i * math.pi / 5 for i in range(10)]]))

    def lenses(s, r):
        for ex in (2.6, 8.8):
            draw.smooth(s, hp(r, 9, [(ex + math.cos(a) * 3.0, -0.6 + math.sin(a) * 3.2) for a in [i * math.pi / 5 for i in range(10)]]))

    def collar(s, r):
        draw.smooth(s, [tp(r, 1.0, -0.7), tp(r, 1.14, -0.1), tp(r, 1.08, 0.7), tp(r, 0.9, 0.9), tp(r, 0.88, 0.2)])

    def scarf(s, r):
        sx, sy = r.shoulder
        flutter = math.sin(r.pose.lean + r.pose.bob * 3) * 2 + max(0.0, r.pose.lean) * 0.5
        draw.ribbon(s, [(sx + 1, sy - 1), (sx - 7, sy + 1 - flutter * 0.3), (sx - 14 - flutter * 0.5, sy + 5 + flutter), (sx - 20 - flutter, sy + 6 + flutter * 1.4)],
                    [4.6, 4.0, 3.2, 2.2])

    def drone_pos(r):
        return r.shoulder[0] + 24 - r.pose.lean * 0.3, r.shoulder[1] - 12 + math.sin(r.pose.bob * 2) * 2

    def drone(s, r):  # the sidecar itself: a hovering pod with spinning rotors
        x, y = drone_pos(r)
        draw.smooth(s, ring(x, y, 7.2, 5.6, 12))
        spin = 5.5 + 3.0 * abs(math.sin(r.pose.bob * 6))
        draw.smooth(s, [(x - spin, y - 6.4), (x + spin, y - 6.4), (x + spin * 0.9, y - 5.4), (x - spin * 0.9, y - 5.4)])
        draw.line(s, (x, y - 5.4), (x, y - 6.4), 1.2)
        draw.smooth(s, [(x - 9.6, y - 0.4), (x - 7, y - 1.6), (x - 7, y + 1.6), (x - 9.6, y + 1.0)])
        draw.smooth(s, [(x + 9.6, y - 0.4), (x + 7, y - 1.6), (x + 7, y + 1.6), (x + 9.6, y + 1.0)])
        draw.line(s, (x - 1, y + 5), (x - 2, y + 8), 1.0)

    def details(f, r):
        cx, cy = r.head
        k = r.look.head_r / 9
        e = r.pose.face
        glass = (214, 246, 255)
        eye_hi(f, cx + 2.6 * k, cy - 0.6 * k, e, True, 4.6, 4.9, iris=((20, 120, 170), (110, 214, 238)), ink=(60, 44, 90), sclera=glass, lash=False)
        eye_hi(f, cx + 8.8 * k, cy - 0.4 * k, e, False, 4.6, 4.9, iris=((20, 120, 170), (110, 214, 238)), ink=(60, 44, 90), sclera=glass, lash=False)
        wd.lines(f, (255, 255, 255), False, [(cx + 0.6 * k, cy - 2.4 * k), (cx + 1.4 * k, cy - 3.0 * k)], 0.6)  # glint on the glass
        mouth_hi(f, cx + 4.6 * k, cy + 5.2 * k, 4.6, e, ink=(150, 80, 70))
        bx, by = tp(r, 0.14, 0.2)
        wd.rect(f, (255, 215, 90), (bx - 1.8, by - 1, 3.8, 2.8))
        for t in (0.55,):
            a, b = tp(r, t, -0.6), tp(r, t, 0.2)
            wd.line(f, (120, 80, 190), a, b, 0.6)
        dx, dy = drone_pos(r)
        wd.circle(f, (30, 40, 70), (dx + 1.2, dy), 3.0)
        wd.circle(f, (110, 214, 238) if e not in ("angry", "hurt") else (255, 110, 100), (dx + 1.2, dy), 2.2)
        wd.circle(f, (255, 255, 255), (dx + 0.6, dy - 0.8), 0.6)
        wd.circle(f, (255, 120, 110), (dx - 1.4, dy - 8.4), 0.7)

    return Look("Sidecar", pal, torso_w=14, torso_h=15, leg_len=14, head_r=9, head_pal="skin", cartoon=0.5,
                textures={"steel": "metal"}, no_hue_shift=("skin", "steel", "cap", "brass", "strap", "lens", "fluff"),
                cel=("body", "skin", "scarf", "cap", "strap"), plain=("lens", "fluff"),
                head_fn=shapes.head([(-9, -1), (-7, -7), (-1, -9.5), (6, -8), (10, -3), (10.5, 3), (7.5, 7.5), (1, 9), (-5, 8), (-9, 4.5)], 9.0),
                torso_fn=shapes.torso([(-0.05, 0), (0.03, -0.85), (0.5, -0.9), (0.9, -1.0), (1.05, -0.3), (1.02, 0.55), (0.85, 1.0), (0.45, 0.95), (0.05, 0.8)]),
                arm_fn=shapes.arm("glove", (1.05, 0.9, 0.85)), leg_fn=shapes.leg("boot", (1.2, 0.95, 0.85)),
                back=[(scarf, "scarf"), (flap, "cap")],
                front=[(collar, "fluff"), (cap, "cap"), (fluff, "fluff"), (strap, "strap"), (rims, "brass"), (lenses, "lens"), (drone, "steel")],
                details=details)


# --- Ingress: a gate with a traffic cone on its head ---------------------------------------------------
def ingress() -> Look:
    pal = with_back_palettes({"body": (84, 206, 214), "steel": (196, 210, 224), "dark": (46, 64, 96), "cone": (255, 148, 40),
                              "visor": (22, 32, 52), "plate": (150, 168, 192), "white": (250, 250, 255)})

    def visor(s, r):
        draw.smooth(s, hp(r, 10, [(-2.6, -4.8), (9.5, -5.0), (11.4, -3.2), (10.8, 0.6), (-2.6, 1.0)]))

    def cheek(s, r):
        draw.smooth(s, hp(r, 10, [(1.5, 1.6), (10, 1.2), (9.2, 7), (4, 9)]))

    def crest(s, r):
        draw.smooth(s, hp(r, 10, [(-3.6, -9), (-1.4, -14), (0, -18.5), (1.4, -14), (3.6, -9)]))

    def stripe(s, r):
        draw.poly(s, hp(r, 10, [(-2.2, -13.6), (2.2, -13.6), (2.8, -11.4), (-2.8, -11.4)]))

    def chest(s, r):
        draw.smooth(s, [tp(r, 0.28, -0.7), tp(r, 0.28, 0.8), tp(r, 0.82, 0.88), tp(r, 0.9, 0.0), tp(r, 0.82, -0.8)])

    def shield(s, r):
        hx, hy = r.hand_f
        x, y = hx + 2, hy - 3
        draw.smooth(s, [(x - 7.5, y + 14), (x - 8, y - 4), (x - 5, y - 12), (x, y - 14), (x + 5, y - 12), (x + 8, y - 4), (x + 7.5, y + 14), (x, y + 17)])

    def shield_face(s, r):
        hx, hy = r.hand_f
        x, y = hx + 2, hy - 3
        draw.smooth(s, [(x - 5.2, y + 12), (x - 5.6, y - 3.4), (x - 3.4, y - 10), (x, y - 11.4), (x + 3.4, y - 10), (x + 5.6, y - 3.4), (x + 5.2, y + 12), (x, y + 14)])

    def details(f, r):
        cx, cy = r.head
        k = r.look.head_r / 10
        e = r.pose.face
        col = {"angry": (255, 96, 86), "effort": (255, 190, 90), "hurt": (255, 255, 255), "shock": (255, 255, 255),
               "happy": (150, 255, 210), "focus": (110, 220, 235), "blink": (60, 110, 130)}.get(e, (130, 245, 255))
        for ex in (1.4, 7.0):  # two glowing eyes behind the visor
            x, y = cx + ex * k, cy - 2.0 * k
            if e == "hurt":
                wd.line(f, col, (x - 1.2, y - 1.4), (x + 1.2, y + 1.4), 0.9)
                wd.line(f, col, (x + 1.2, y - 1.4), (x - 1.2, y + 1.4), 0.9)
            elif e == "happy":
                wd.lines(f, col, False, [(x - 1.6, y + 1.0), (x, y - 1.1), (x + 1.6, y + 1.0)], 1.0)
            elif e == "blink":
                wd.line(f, col, (x - 1.6, y), (x + 1.6, y), 0.8)
            else:
                h = 2.0 if e in ("angry", "effort") else 3.0
                wd.ellipse(f, tuple(int(c * 0.5) for c in col), (x - 1.9, y - h / 2 - 0.6, 3.8, h + 1.2))
                wd.ellipse(f, col, (x - 1.4, y - h / 2, 2.8, h))
                if e == "angry":
                    wd.line(f, col, (x - 2.4, y - 2.8 + (0.8 if ex < 4 else -0.8)), (x + 2.4, y - 1.8 - (0.8 if ex < 4 else -0.8)), 0.9)
        for i in range(3):  # grille slots on the cheek guard
            wd.line(f, (70, 84, 110), (cx + (4 + i * 2) * k, cy + 3.2 * k), (cx + (3.6 + i * 2) * k, cy + 6.6 * k), 0.6)
        for i in range(4):  # portcullis bars on the chest
            a, b = tp(r, 0.34, -0.5 + i * 0.4), tp(r, 0.8, -0.5 + i * 0.4)
            wd.line(f, (40, 110, 126), a, b, 0.9)
        for t in (0.45, 0.65):
            wd.line(f, (40, 110, 126), tp(r, t, -0.62), tp(r, t, 0.7), 0.7)
        hx, hy = r.hand_f
        x, y = hx + 2, hy - 3
        for i in range(-2, 3):  # the shield's gate bars and rivets
            wd.line(f, (150, 168, 192), (x + i * 2.2, y - 9), (x + i * 2.2, y + 11), 0.9)
        wd.line(f, (150, 168, 192), (x - 4.6, y + 1), (x + 4.6, y + 1), 0.9)
        for ox, oy in ((-6.4, -6), (6.4, -6), (-6.4, 12), (6.4, 12)):
            wd.circle(f, (240, 246, 255), (x + ox, y + oy), 0.7)

    return Look("Ingress", pal, torso_w=18, torso_h=16, leg_len=14, leg_w=6, arm_w=6, head_r=10, head_pal="steel", leg_pal="dark",
                cartoon=0.4, cel=("body", "steel", "dark", "cone", "plate", "white"), plain=("visor",),
                no_hue_shift=("steel", "dark", "cone", "visor", "plate", "white"),
                head_fn=shapes.head([(-8, -8), (-3, -11), (4, -11), (9, -8), (10, -1), (9, 6), (5, 9.5), (-3, 9.5), (-8, 6), (-9.5, -1)], 10.0),
                torso_fn=shapes.torso([(-0.05, 0), (0.0, -0.8), (0.4, -1.0), (0.85, -1.1), (1.05, -0.5), (1.05, 0.6), (0.85, 1.1), (0.4, 1.0), (0.0, 0.8)]),
                arm_fn=shapes.arm("glove", (1.2, 1.0, 0.95)), leg_fn=shapes.leg("greave", (1.15, 0.95, 0.9)),
                front=[(chest, "plate"), (cheek, "plate"), (visor, "visor"), (crest, "cone"), (stripe, "white"), (shield, "plate"),
                       (shield_face, "steel")], details=details)


# --- Operator: the switchboard operator ---------------------------------------------------------------------
def operator() -> Look:
    pal = with_back_palettes({"body": (255, 150, 190), "skin": (250, 215, 185), "coat": (242, 242, 252), "dark": (70, 70, 92),
                              "hair": (132, 70, 112), "panel": (52, 56, 84), "blush": (255, 150, 160), "gold": (250, 214, 110)})

    def coat(s, r):
        sx, sy = r.shoulder
        hx, hy = r.hip
        sw = max(0.0, r.pose.lean) * 0.8 + math.sin(r.pose.bob * 2) * 1.2
        draw.smooth(s, [(sx - 5, sy), (hx - 6, hy + 1), (hx - 15 - sw - abs(r.pose.lean) * 0.3, hy + 11), (hx - 9, hy + 12), (hx - 3, hy + 9)])

    def hair_back(s, r):
        draw.smooth(s, hp(r, 10, [(-11, -4), (-9, -11), (-2, -13.5), (6, -12.5), (9, -8), (3, -8.5), (-3, -7), (-6, 0), (-9, 6), (-12, 3)]))

    def bun(s, r):
        cx, cy = r.head
        k = r.look.head_r / 10
        bounce = math.sin(r.pose.bob * 2.5) * 1.0
        draw.smooth(s, ring(cx - 9 * k, cy - 11.5 * k + bounce, 4.2 * k, 4.0 * k, 10))

    def bangs(s, r):
        draw.smooth(s, hp(r, 10, [(-8.5, -3), (-5, -9.5), (3, -11), (9.5, -7.5), (10, -3.6), (5, -6.4), (0, -5), (-4, -2.4)]))

    def headset(s, r):
        cx, cy = r.head
        k = r.look.head_r / 10
        draw.ribbon(s, [(cx - 8.6 * k, cy - 3 * k), (cx - 7 * k, cy - 10.5 * k), (cx - 0.5 * k, cy - 13 * k), (cx + 5.5 * k, cy - 10.6 * k)], [1.3, 1.3, 1.3, 1.1])
        draw.smooth(s, ring(cx - 6.6 * k, cy + 1 * k, 3.2 * k, 3.6 * k, 10))
        draw.ribbon(s, [(cx - 5.4 * k, cy + 3.4 * k), (cx - 1 * k, cy + 8 * k), (cx + 5 * k, cy + 9 * k)], [1.0, 0.9, 0.9])
        draw.circle(s, (cx + 5.8 * k, cy + 9.2 * k), 1.6 * k)

    def cheeks(s, r):
        draw.ellipse(s, *hp(r, 10, [(1.0, 2.8)])[0], 3.2, 1.8)

    def panel(s, r):
        draw.smooth(s, [tp(r, 0.3, 0.1), tp(r, 0.3, 0.95), tp(r, 0.72, 0.98), tp(r, 0.72, 0.1)])

    def cord(s, r):  # a patch cord from the switchboard, swinging with every step
        hx, hy = r.hip
        sw = math.sin(r.pose.bob * 2 + r.pose.lean * 0.5) * 2 + r.pose.lean * 0.4
        draw.ribbon(s, [(hx - 4, hy - 2), (hx - 12, hy + 2), (hx - 17 - sw, hy - 5), (hx - 22 - sw, hy - 1), (hx - 25 - sw, hy - 8)], [2.0, 2.0, 1.8, 1.8, 1.8])
        draw.smooth(s, [(hx - 29 - sw, hy - 12), (hx - 22 - sw, hy - 12), (hx - 22 - sw, hy - 6.4), (hx - 29 - sw, hy - 6.4)])

    def details(f, r):
        cx, cy = r.head
        k = r.look.head_r / 10
        e = r.pose.face
        eye_hi(f, cx + 3.0 * k, cy - 1.2 * k, e, True, 4.6, 6.0, iris=((84, 36, 92), (186, 104, 176)), ink=(70, 36, 80))
        eye_hi(f, cx + 8.6 * k, cy - 1.0 * k, e, False, 4.6, 6.0, iris=((84, 36, 92), (186, 104, 176)), ink=(70, 36, 80))
        mouth_hi(f, cx + 4.2 * k, cy + 5.0 * k, 4.2, e, ink=(200, 70, 100), inside=(150, 40, 70))
        px, py = tp(r, 0.4, 0.35)
        for i in range(3):  # jacks on the switchboard apron
            for j in range(2):
                wd.circle(f, (250, 214, 110) if (i + j) % 2 == 0 else (110, 220, 200), (px + i * 2.1, py + j * 3.0), 0.7)

    return Look("Operator", pal, torso_w=14, torso_h=16, leg_len=15, leg_w=5, head_r=10, head_pal="skin", leg_pal="dark", cartoon=0.5,
                cel=("body", "skin", "coat", "dark", "hair", "panel"), plain=("blush",),
                no_hue_shift=("skin", "coat", "dark", "panel", "blush", "gold"),
                head_fn=shapes.head([(-8.5, -2), (-6, -8), (0, -10), (6, -8.5), (9.5, -3), (9, 2), (5, 7.5), (0, 10), (-4.5, 7.5), (-8, 3)], 10.0),
                torso_fn=shapes.torso([(-0.05, 0), (0.04, -0.8), (0.45, -0.75), (0.85, -0.95), (1.05, -0.3), (1.0, 0.5), (0.8, 0.95), (0.4, 0.85), (0.05, 0.7)]),
                arm_fn=shapes.arm("glove", (1.0, 0.85, 0.8)), leg_fn=shapes.leg("pump", (1.1, 0.9, 0.75)),
                back=[(coat, "coat"), (cord, "dark"), (hair_back, "hair")],
                front=[(panel, "panel"), (cheeks, "blush"), (bangs, "hair"), (bun, "hair"), (headset, "dark")], details=details)


# --- OOMKiller: a lanky, grinning reaper that floats on a ragged cloak --------------------------------------------
def _tatter_legs():
    """Legs drawn as the ragged hem of a cloak: tapering shreds that flutter as the reaper runs and hovers."""
    def fn(s, r, back: bool) -> None:
        hip = r.hip
        kn, ft = (r.knee_b, r.foot_b) if back else (r.knee_f, r.foot_f)
        w = r.look.leg_w
        flutter = math.sin(r.pose.bob * 3 + (1.7 if back else 0.0)) * 1.3
        draw.ribbon(s, [hip, kn, (ft[0] - 1.2 + flutter, ft[1] - 3)], [w * 1.5, w * 0.95, w * 0.2])
        fx, fy = ft
        draw.poly(s, [(fx - w * 0.9, fy - w * 1.4), (fx - w * 0.2 + flutter * 0.4, fy + w * 0.6), (fx + w * 0.5, fy - w * 1.2)])
        draw.poly(s, [(fx + w * 0.1, fy - w * 1.3), (fx + w * 1.2 + flutter * 0.6, fy + w * 0.2), (fx + w * 1.1, fy - w * 1.4)])
    return fn


def oomkiller() -> Look:
    pal = with_back_palettes({"body": (206, 52, 72), "hood": (72, 30, 78), "bone": (240, 234, 216), "steel": (186, 196, 216),
                              "wood": (132, 88, 54), "pcb": (50, 168, 104), "socket": (34, 12, 30), "gold": (240, 200, 80),
                              "cape": (112, 30, 70), "chip": (30, 40, 48)})

    def skull(s, r):
        open_ = 2.2 if r.pose.face in ("hurt", "shock", "effort", "angry") else 0.0
        draw.smooth(s, hp(r, 10, [(-1, -7.8), (5.5, -9.6), (11, -6.4), (12, -0.4), (10.6, 4.4), (10, 9.4 + open_), (3.6, 11.4 + open_),
                                  (-1.4, 8.6), (-3.2, 2.4), (-3, -4.4)]))

    def hood_peak(s, r):  # the hood's drooping tip, flopping behind with the motion
        cx, cy = r.head
        k = r.look.head_r / 10
        flop = r.pose.lean * -0.5 + math.sin(r.pose.bob * 2) * 1.2
        draw.smooth(s, [(cx - 9 * k, cy - 8 * k), (cx - 15 * k + flop, cy - 12 * k), (cx - 21 * k + flop * 1.6, cy - 6 * k + flop), (cx - 14 * k, cy - 3 * k)])

    def horn_front(s, r):
        draw.smooth(s, hp(r, 10, [(3.6, -10.6), (8, -15.6), (13.6, -23), (13.6, -14.4), (10.2, -8.8)]))

    def horn_back(s, r):
        draw.smooth(s, hp(r, 10, [(-6, -10), (-9.6, -15), (-12.6, -22), (-8.4, -16.4), (-3.6, -10.4)]))

    def cape(s, r):  # a long ragged cloak streaming out behind
        sx, sy = r.shoulder
        hx, hy = r.hip
        sw = math.sin(r.pose.bob * 2 + r.pose.lean * 0.4) * 2.2 + r.pose.lean * 0.6
        pts = [(sx - 4, sy - 2), (sx - 11 - sw * 0.4, sy + 3), (hx - 18 - sw, hy + 8), (hx - 22 - sw * 1.3, hy + 15), (hx - 15 - sw, hy + 12),
               (hx - 13 - sw * 0.8, hy + 18), (hx - 8, hy + 12), (hx - 5, hy + 16), (hx - 1, hy + 4), (hx - 4, hy - 4)]
        draw.smooth(s, pts)

    def belt(s, r):
        draw.poly(s, [tp(r, 0.04, -0.98), tp(r, 0.04, 1.0), tp(r, 0.17, 1.02), tp(r, 0.17, -1.0)])

    def sticks(s, r):  # RAM sticks hanging off the belt on chains
        sw = math.sin(r.pose.bob * 3) * 1.4 + r.pose.lean * 0.3
        for i, t in enumerate((-0.4, 0.2, 0.7)):
            x, y = tp(r, 0.08, t)
            draw.smooth(s, [(x - 1.6 + sw * 0.3 * i, y), (x + 1.6 + sw * 0.3 * i, y), (x + 1.8 + sw * 0.7, y + 7 + i), (x - 1.8 + sw * 0.7, y + 7 + i)])

    def scythe(s, r):
        hx, hy = r.hand_f
        draw.ribbon(s, [(hx - 3, hy + 17), (hx, hy - 8), (hx + 2, hy - 44)], [3.0, 2.8, 2.6])

    def blade(s, r):
        hx, hy = r.hand_f
        draw.smooth(s, [(hx + 2, hy - 46), (hx + 12, hy - 51), (hx + 24, hy - 46), (hx + 31, hy - 35), (hx + 24, hy - 38), (hx + 13, hy - 41), (hx + 2, hy - 39)])

    def details(f, r):
        cx, cy = r.head
        k = r.look.head_r / 10
        e = r.pose.face
        glow = {"angry": (255, 196, 90), "effort": (255, 150, 80), "happy": (150, 255, 160), "shock": (255, 255, 255),
                "hurt": (255, 255, 255), "focus": (255, 70, 70), "blink": (90, 30, 50)}.get(e, (255, 96, 84))
        for ex, big in ((2.8, 1.18), (8.6, 0.98)):  # big hollow sockets with embers burning inside
            x, y = cx + ex * k, cy - 2.0 * k
            wd.ellipse(f, (34, 12, 30), (x - 3.0 * big, y - 3.4 * big, 6.0 * big, 6.8 * big))
            if e == "hurt":
                wd.line(f, glow, (x - 1.4, y - 1.4), (x + 1.4, y + 1.4), 1.0)
                wd.line(f, glow, (x + 1.4, y - 1.4), (x - 1.4, y + 1.4), 1.0)
            elif e == "happy":
                wd.lines(f, glow, False, [(x - 1.6, y + 1.0), (x, y - 1.2), (x + 1.6, y + 1.0)], 1.0)
            elif e == "blink":
                wd.line(f, glow, (x - 1.6, y), (x + 1.6, y), 0.8)
            else:
                rr = 1.3 if e in ("angry", "effort") else 1.9
                wd.circle(f, glow, (x + 0.3, y), rr * big)
                wd.circle(f, (255, 255, 255), (x - 0.2, y - 0.6), 0.55)
        if e in ("angry", "effort", "focus"):
            wd.line(f, (70, 40, 56), (cx + 0.2 * k, cy - 6.6 * k), (cx + 5.6 * k, cy - 4.2 * k), 1.5)
            wd.line(f, (70, 40, 56), (cx + 6.8 * k, cy - 4.4 * k), (cx + 11.4 * k, cy - 6.4 * k), 1.5)
        wd.polygon(f, (50, 24, 42), [(cx + 6.0 * k, cy + 1.8 * k), (cx + 8.4 * k, cy + 1.8 * k), (cx + 7.2 * k, cy + 4.2 * k)])
        jaw = 2.2 if e in ("hurt", "shock", "effort", "angry") else 0.0
        wd.rect(f, (60, 24, 44), (cx + 1.0 * k, cy + 5.6 * k, 10.4 * k, (3.2 + jaw) * k))  # the dark mouth, a huge grin
        for i in range(6):  # a row of big teeth
            x = cx + (1.2 + i * 1.75) * k
            wd.rect(f, (252, 248, 236), (x, cy + 5.6 * k, 1.4 * k, (2.6 + jaw * 0.6) * k))
            if jaw:
                wd.rect(f, (252, 248, 236), (x, cy + (8.4 + jaw * 0.2) * k, 1.4 * k, 1.8 * k))
        bx, by = r.hand_f
        for i in range(3):
            wd.rect(f, (22, 28, 32), (bx + 7 + i * 4.6, by - 45 + i * 2.2, 3.4, 2.4))
        wd.line(f, (240, 200, 80), (bx + 6, by - 40.4), (bx + 22, by - 38.2), 1.0)
        for i in range(6):
            wd.line(f, (240, 200, 80), (bx + 7 + i * 2.8, by - 41.2 + i * 0.5), (bx + 7 + i * 2.8, by - 38.8 + i * 0.4), 0.5)
        x, y = tp(r, 0.58, 0.0)
        wd.line(f, (252, 240, 222), (x - 2.4, y - 2.4), (x + 2.4, y + 2.4), 1.0)
        wd.line(f, (252, 240, 222), (x + 2.4, y - 2.4), (x - 2.4, y + 2.4), 1.0)

    return Look("OOMKiller", pal, torso_w=15, torso_h=21, leg_len=15, leg_w=6, arm_w=5, arm_len=19, head_r=11, head_pal="hood", limb_pal="bone",
                leg_pal="body", cartoon=0.7, cel=("body", "hood", "bone", "wood", "pcb", "cape", "chip"), plain=("socket",),
                no_hue_shift=("bone", "steel", "wood", "pcb", "socket", "gold", "chip"),
                head_fn=shapes.head([(-10, -2), (-9, -9), (-3, -13.4), (5, -13), (11.6, -6.6), (13, 0), (11.2, 7), (5.4, 11), (-4.4, 11.4), (-9.6, 7)], 10.0),
                torso_fn=shapes.torso([(-0.05, 0), (0.0, -0.8), (0.4, -0.85), (0.85, -1.15), (1.08, -0.6), (1.0, 0.5), (0.8, 0.9), (0.4, 0.82), (0.0, 0.72)]),
                arm_fn=shapes.arm("bone", (1.1, 0.85, 0.7)), leg_fn=_tatter_legs(),
                back=[(cape, "cape"), (hood_peak, "hood"), (scythe, "wood"), (horn_back, "bone")],
                front=[(belt, "hood"), (sticks, "pcb"), (skull, "bone"), (horn_front, "bone"), (blade, "pcb")], details=details)

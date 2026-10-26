"""The eight fighter designs: palettes, proportions, accessories, materials and expressive faces."""
from __future__ import annotations

import math

import pygame

from k8ssmash.art import draw, shapes
from k8ssmash.art.rig import Look, Rig, with_back_palettes
from k8ssmash.ui import wd

LASH = (30, 24, 50)


def pt(p, dx: float = 0, dy: float = 0) -> tuple[int, int]:
    return round(p[0] + dx), round(p[1] + dy)


# --- expressive face parts -------------------------------------------------------------------
def eye(f: pygame.Surface, x: int, y: int, w: int = 4, h: int = 5, iris=(70, 100, 210)) -> None:
    """A little glossy eye: white, colored iris looking forward, dark pupil and a glint."""
    wd.rect(f, (252, 252, 255), (x, y, w, h))
    wd.rect(f, iris, (x + w // 2 - 1, y + 1, w - w // 2 + 1, h - 1))
    wd.rect(f, (18, 16, 40), (x + w - 2, y + 2, 2, h - 2))
    wd.set_at(f, (x + w // 2, y + 1), (255, 255, 255))
    wd.line(f, LASH, (x, y - 1), (x + w - 1, y - 1))  # lash line


def eye_expr(f: pygame.Surface, x: int, y: int, w: int, h: int, face: str, iris, side: int) -> None:
    """One eye that changes with the expression. side 0 is the far eye, 1 the near eye."""
    if face == "blink":
        wd.line(f, LASH, (x, y + h // 2), (x + w - 1, y + h // 2))
    elif face == "happy":  # a joyful upside-down V
        wd.lines(f, LASH, False, [(x, y + h - 1), (x + w // 2, y + 1), (x + w - 1, y + h - 1)])
    elif face == "hurt":  # squeezed > <
        if side == 0:
            wd.lines(f, LASH, False, [(x, y), (x + w - 1, y + h // 2), (x, y + h - 1)])
        else:
            wd.lines(f, LASH, False, [(x + w - 1, y), (x, y + h // 2), (x + w - 1, y + h - 1)])
    elif face == "shock":  # wide eyes with pinprick pupils
        wd.rect(f, (252, 252, 255), (x - 1, y - 1, w + 2, h + 2))
        wd.rect(f, LASH, (x - 1, y - 2, w + 2, 1))
        wd.set_at(f, (x + w - 1, y + h // 2), (18, 16, 40))
    elif face in ("effort", "focus", "angry"):
        eye(f, x, y + 1, w, h - 1 if face == "angry" else h - 2, iris)
        wd.line(f, LASH, (x - 1, y), (x + w, y))  # heavy lid
        if face in ("angry", "effort"):  # brows slope in toward the nose
            if side == 0:
                wd.line(f, LASH, (x - 1, y - 2), (x + w, y))
            else:
                wd.line(f, LASH, (x, y), (x + w + 1, y - 2))
    else:
        eye(f, x, y, w, h, iris)


def mouth_expr(f: pygame.Surface, x: int, y: int, w: int, face: str, color=(150, 70, 80)) -> None:
    if face == "happy":
        wd.lines(f, color, False, [(x, y), (x + 1, y + 1), (x + w - 2, y + 1), (x + w - 1, y)])
    elif face in ("hurt", "shock"):
        wd.ellipse(f, (40, 12, 24), (x + w // 2 - 1, y - 1, 3, 4))
    elif face == "effort":
        wd.rect(f, (40, 12, 24), (x + 1, y - 1, max(2, w - 2), 3))
        wd.line(f, (250, 244, 240), (x + 1, y - 1), (x + w - 2, y - 1))  # clenched teeth
    elif face == "angry":
        wd.lines(f, color, False, [(x, y + 1), (x + 1, y), (x + w - 2, y), (x + w - 1, y + 1)])
    else:
        wd.line(f, color, (x, y), (x + w - 1, y))


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
    """A whale-kid built from hand-shaped contours: a wedge head with a melon and a snout, paddle flippers, a potbelly,
    webbed foot-flippers, crescent flukes and a dorsal fin; no circles or capsules in the silhouette."""
    pal = with_back_palettes({"body": (62, 138, 240), "fin": (34, 92, 196), "cream": (242, 247, 255), "sheen": (178, 220, 255),
                              "blush": (255, 150, 172), "leaf": (150, 225, 255)})

    def head(s, r: Rig) -> None:
        cx, cy = r.head
        k = r.look.head_r / 10.0
        pts = [(-9, -2), (-6.5, -8), (0, -10.5), (6, -9), (11, -4.5), (14, 0.5), (11.5, 4.5), (6, 7.5), (-1, 8.5), (-7, 6.5), (-9.5, 1.5)]
        draw.smooth(s, [(cx + x * k, cy + y * k) for x, y in pts])

    def sheen(s, r: Rig) -> None:  # a hand-placed gloss on the melon, and a small one on the belly
        cx, cy = r.head
        k = r.look.head_r / 10.0
        draw.smooth(s, [(cx + x * k, cy + y * k) for x, y in ((-5.5, -6.2), (-2.5, -8.6), (2, -8.8), (4.2, -7.6), (0.5, -7.0), (-3, -4.8))])

    def blush(s, r: Rig) -> None:
        cx, cy = r.head
        k = r.look.head_r / 10.0
        draw.ellipse(s, cx - 3.6 * k, cy + 1.0 * k, 3.2 * k, 2.0 * k)

    def muzzle(s, r: Rig) -> None:  # the pale lower jaw and throat: countershading like a real whale
        cx, cy = r.head
        k = r.look.head_r / 10.0
        pts = [(-5, 3.5), (2, 2.2), (9, 1.2), (13, 2.2), (11.5, 4.8), (6, 7.6), (-1, 8.4), (-6, 6.5)]
        draw.smooth(s, [(cx + x * k, cy + y * k) for x, y in pts])

    def torso(s, r: Rig) -> None:  # barrel chest, a hump at the shoulders and a belly that bulges forward
        w = r.look.torso_w
        hx, hy = r.hip
        sx, sy = r.shoulder
        ux, uy = sx - hx, sy - hy

        def at(t, side):
            return (hx + ux * t + side * w * 0.5, hy + uy * t)
        draw.smooth(s, [at(-0.1, 0), at(0.02, -0.82), at(0.4, -0.95), at(0.82, -0.9), at(1.06, -0.2), at(1.0, 0.7), at(0.7, 1.22),
                        at(0.32, 1.24), at(0.04, 0.85)])

    def belly(s, r: Rig) -> None:  # the pale belly with its throat pleats
        w = r.look.torso_w
        hx, hy = r.hip
        sx, sy = r.shoulder
        ux, uy = sx - hx, sy - hy

        def at(t, side):
            return (hx + ux * t + side * w * 0.5, hy + uy * t)
        draw.smooth(s, [at(0.08, 0.35), at(0.3, 0.5), at(0.7, 0.5), at(0.92, 0.28), at(0.85, 0.82), at(0.55, 1.1), at(0.22, 1.1)])

    def dorsal(s, r: Rig) -> None:  # a small dorsal fin on the upper back
        sx, sy = r.shoulder
        hx, hy = r.hip
        mx, my = hx + (sx - hx) * 0.55 - r.look.torso_w * 0.5, hy + (sy - hy) * 0.55
        draw.smooth(s, [(mx + 1, my - 2), (mx - 4.5, my - 6), (mx - 8, my - 10.5), (mx - 6.5, my - 3.5), (mx - 8.5, my + 1.5), (mx - 2, my + 2.5)])

    def arm(s, r: Rig, back: bool) -> None:  # a paddle flipper: slim at the shoulder, widening toward a rounded tip
        sh, el, hd = r.shoulder, (r.elbow_b if back else r.elbow_f), (r.hand_b if back else r.hand_f)
        w = r.look.arm_w
        tip = (hd[0] + (hd[0] - el[0]) * 0.18, hd[1] + (hd[1] - el[1]) * 0.18)
        draw.ribbon(s, [sh, el, hd, tip], [w * 1.0, w * 0.85, w * 1.45, w * 0.7])

    def leg(s, r: Rig, back: bool) -> None:  # a short thigh and a webbed flipper foot with a scalloped tip
        hip, kn, ft = r.hip, (r.knee_b if back else r.knee_f), (r.foot_b if back else r.foot_f)
        w = r.look.leg_w
        draw.ribbon(s, [hip, kn, ft], [w * 1.2, w * 0.9, w * 0.7])
        fx, fy = ft
        draw.smooth(s, [(fx - w * 0.7, fy - w * 0.4), (fx + w * 0.2, fy - w * 0.55), (fx + w * 1.1, fy - w * 0.3), (fx + w * 1.8, fy + w * 0.05),
                        (fx + w * 1.5, fy + w * 0.35), (fx + w * 1.7, fy + w * 0.7), (fx + w * 0.8, fy + w * 0.62), (fx - w * 0.5, fy + w * 0.5)])

    def tail_fin(s, r: Rig) -> None:  # a tapered tail stalk ending in crescent flukes that swish with the motion
        hx, hy = r.hip
        sw = math.sin(r.pose.lean * 0.7 + r.pose.bob) * 2.0 + r.pose.lean * 0.3
        draw.ribbon(s, [(hx - 4, hy - 1), (hx - 11, hy + 1), (hx - 16 - sw, hy - 5), (hx - 16 - sw, hy - 11)], [5.0, 3.8, 2.8, 2.2])
        tx, ty = hx - 16 - sw, hy - 11
        draw.smooth(s, [(tx + 1, ty + 1), (tx - 2, ty - 3), (tx - 6, ty - 9), (tx - 10.5, ty - 8), (tx - 8, ty - 3.5), (tx - 4, ty - 0.5),
                        (tx - 9, ty + 2.5), (tx - 10, ty + 6), (tx - 5.5, ty + 5), (tx - 1.5, ty + 3.5)])

    def spout(s, r: Rig) -> None:  # the water spout from the blowhole
        cx, cy = r.head
        k = r.look.head_r / 10.0
        sway = math.sin(r.pose.lean * 0.5 + r.pose.bob) * 1.5
        draw.line(s, (cx + 1 * k, cy - 10 * k), (cx + 1.5 * k + sway, cy - 15 * k), 1.8)
        for dx, dy, rad in ((-3, -17, 1.4), (2, -20, 1.8), (7, -17, 1.4)):
            draw.circle(s, (cx + dx * k + sway * 1.4, cy + dy * k), rad)

    def eye(f: pygame.Surface, x: float, y: float, expr: str, near: bool) -> None:
        """A hand-shaped eye: glossy sclera, a blue iris looking forward, pupil, glint, and lids that follow the expression."""
        ink = (24, 36, 96)
        w, h = (5.8, 6.8) if near else (4.6, 5.6)
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
        wd.ellipse(f, (252, 253, 255), (x - w / 2, y - h / 2, w, h))
        wd.ellipse(f, (20, 50, 138), (x - w / 2 + w * 0.36, y - h / 2 + h * 0.16, w * 0.6, h * 0.74))  # a deep iris, forward in the eye
        wd.ellipse(f, (74, 134, 232), (x - w / 2 + w * 0.42, y + h * 0.08, w * 0.48, h * 0.3))  # lighter lower iris
        pr = 0.7 if expr == "shock" else 1.4
        wd.ellipse(f, (6, 10, 36), (x + w * 0.16, y - h * 0.16, pr, pr * 1.45))
        wd.circle(f, (255, 255, 255), (x + w * 0.12, y - h * 0.28), 0.6)
        wd.circle(f, (255, 255, 255), (x + w * 0.4, y + h * 0.14), 0.28)
        wd.ellipse(f, ink, (x - w / 2, y - h / 2, w, h), 0.6)
        if expr in ("angry", "effort", "focus"):  # a heavy lid, slanting in toward the snout
            tilt = -1.1 if expr == "angry" else (-0.5 if near else 0.2)
            wd.line(f, ink, (x - w / 2 - 0.4, y - h / 2 + 0.7), (x + w / 2 + 0.4, y - h / 2 + 0.7 + tilt), 1.1)
        else:  # a thick upper lash line that flicks outward
            wd.lines(f, ink, False, [(x - w / 2 - 0.3, y - h / 2 + 0.5), (x, y - h / 2 - 0.2), (x + w / 2 + 0.4, y - h / 2 + 0.3)], 1.0)

    def details(f: pygame.Surface, r: Rig) -> None:
        k = r.look.head_r / 10.0
        cx, cy = r.head
        expr = r.pose.face
        eye(f, cx + 1.6 * k, cy - 1.4 * k, expr, True)
        eye(f, cx + 9.8 * k, cy - 1.2 * k, expr, False)
        wd.line(f, (30, 70, 160), (cx - 0.5 * k, cy - 5.8 * k), (cx + 11.5 * k, cy - 4.4 * k), 0.8)  # a heavy brow ridge
        if expr in ("hurt", "shock"):  # mouth open: a dark oval under the snout
            wd.ellipse(f, (40, 14, 38), (cx + 8 * k, cy + 2.2 * k, 4.2 * k, 3.4 * k))
        else:
            lift = 0.9 if expr in ("happy", "effort", "angry") else 0.0
            wd.lines(f, (30, 60, 150), False, [(cx + 14 * k, cy + 0.2 * k), (cx + 10.5 * k, cy + (2.6 + lift) * k), (cx + 6 * k, cy + 3.4 * k)], 0.8)
        hx, hy = r.hip
        sx, sy = r.shoulder
        w = r.look.torso_w

    return Look("Pod", pal, head_r=9.2, torso_w=17, torso_h=16, leg_len=11.5, leg_w=5.8, arm_len=16, arm_w=4.6,
                no_hue_shift=("cream", "sheen", "blush", "leaf"), head_pal="body", limb_pal="fin", leg_pal="fin",
                back=[(tail_fin, "fin"), (dorsal, "fin")],
                front=[(belly, "cream"), (muzzle, "cream"), (sheen, "sheen"), (spout, "leaf")], details=details,
                head_fn=head, torso_fn=torso, arm_fn=arm, leg_fn=leg, cartoon=0.3,
                cel=("body", "fin", "cream"), plain=("sheen", "blush"))


from k8ssmash.art import cast  # noqa: E402  (the supporting cast lives next door)


LOOKS = {"Pod": pod, "StatefulSet": cast.statefulset, "Kubectl": cast.kubectl, "CronJob": cast.cronjob, "Sidecar": cast.sidecar,
         "Ingress": cast.ingress, "Operator": cast.operator, "OOMKiller": cast.oomkiller}

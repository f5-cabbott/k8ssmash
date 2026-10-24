"""Pose generators for every animation. Poses carry expression, squash-and-stretch and smear, so a punch has
anticipation (squash, brow down), a strike (stretch, smear) and a recovery. Attack styles have three phases."""
from __future__ import annotations

import math
from dataclasses import replace

from k8ssmash.art.rig import Pose

# name -> (frame count, fps, loops)
ANIMS: dict[str, tuple[int, int, bool]] = {
    "idle": (8, 6, True),  # 6 breathing frames + 2 blink frames
    "run": (8, 16, True),
    "jump": (3, 1, False),  # rise (stretched), apex, early fall
    "fall": (2, 1, False),
    "djump": (4, 18, False),
    "land": (3, 14, False),
    "shield": (1, 1, False),
    "duck": (1, 1, False),
    "hurt": (3, 8, True),
    "win": (4, 7, True),
    "lose": (1, 1, False),
    "jab": (3, 0, False),
    "side": (3, 0, False),
    "up": (3, 0, False),
    "down": (3, 0, False),
    "cast": (3, 0, False),
    "dash": (3, 0, False),
    "rise": (3, 0, False),
    "counter": (3, 0, False),
    "buff": (3, 0, False),
}


def pose_for(anim: str, i: int) -> Pose:
    return _POSES[anim](i)


def _with(p: Pose, **kw) -> Pose:
    return replace(p, **kw)


def idle(i: int) -> Pose:
    ph = (i % 6) / 6 * 2 * math.pi
    breathe = math.sin(ph)
    p = Pose(bob=-0.8 * breathe, squash=1 + 0.018 * breathe, head_dy=0.4 * breathe,
             arm_f=(14 + 3 * breathe, 10 + 2 * breathe), arm_b=(-12 - 2 * breathe, -4), lean=0.6 * math.sin(ph + 1))
    return _with(p, face="blink") if i >= 6 else p


def run(i: int) -> Pose:
    ph = i / 8 * 2 * math.pi
    sw = lambda q: (math.sin(q) * 12, max(0.0, -math.cos(q)) * 9)
    contact = abs(math.cos(ph * 2))  # the body dips as each foot lands and rises as it passes
    return Pose(lean=5, bob=-(1 - contact) * 2.4, crouch=1 + contact * 1.2, squash=0.97 + 0.05 * (1 - contact),
                f_foot=sw(ph), b_foot=sw(ph + math.pi), head_dx=1.0, head_dy=-0.5 * (1 - contact),
                arm_f=(-math.sin(ph) * 58, -math.sin(ph) * 58 + 40), arm_b=(math.sin(ph) * 58, math.sin(ph) * 58 + 40),
                face="happy" if i % 8 in (2, 6) else "neutral")


def jump(i: int) -> Pose:
    return [
        Pose(lean=1, squash=1.09, f_foot=(3, 5), b_foot=(-2, 7), arm_f=(160, 172), arm_b=(-160, -172), face="effort"),
        Pose(lean=1, squash=1.0, crouch=1, f_foot=(7, 8), b_foot=(-3, 10), arm_f=(125, 150), arm_b=(-125, -150), face="happy"),
        Pose(lean=0, squash=1.03, f_foot=(8, 5), b_foot=(-6, 6), arm_f=(115, 140), arm_b=(-115, -140), head_dy=1, face="neutral"),
    ][i]


def fall(i: int) -> Pose:
    return [
        Pose(squash=1.04, f_foot=(9, 3), b_foot=(-9, 3), arm_f=(125, 150), arm_b=(-125, -150), head_dy=1, face="shock"),
        Pose(squash=1.1, f_foot=(5, 1), b_foot=(-5, 1), arm_f=(150, 168), arm_b=(-150, -168), head_dy=2, face="shock"),
    ][i]


def djump(i: int) -> Pose:
    return [
        Pose(crouch=5, squash=0.9, lean=2, f_foot=(6, 4), b_foot=(-4, 5), arm_f=(40, 80), arm_b=(-40, -80), face="effort"),
        Pose(crouch=6, squash=0.88, lean=3, f_foot=(5, 11), b_foot=(-3, 12), arm_f=(60, 125), arm_b=(40, 120), face="effort"),
        Pose(crouch=2, squash=1.06, lean=2, f_foot=(5, 9), b_foot=(-4, 10), arm_f=(95, 100), arm_b=(-95, -100), face="happy"),
        Pose(squash=1.08, f_foot=(4, 4), b_foot=(-3, 5), arm_f=(155, 170), arm_b=(-155, -170), face="happy"),
    ][i]


def land(i: int) -> Pose:
    return [
        Pose(crouch=8, squash=0.8, lean=2, f_foot=(9, 0), b_foot=(-9, 0), arm_f=(55, 70), arm_b=(-55, -60), head_dy=3, face="effort"),
        Pose(crouch=5, squash=0.9, lean=1, f_foot=(8, 0), b_foot=(-8, 0), arm_f=(35, 50), arm_b=(-35, -40), head_dy=1, face="neutral"),
        Pose(crouch=1.5, squash=0.98, f_foot=(6, 0), b_foot=(-6, 0), face="neutral"),
    ][i]


def shield(i: int) -> Pose:
    return Pose(crouch=3, lean=2, squash=0.96, arm_f=(60, 150), arm_b=(30, 170), f_foot=(7, 0), b_foot=(-6, 0), face="focus")


def duck(i: int) -> Pose:
    return Pose(crouch=11, lean=3, head_dy=2, squash=0.95, arm_f=(40, 70), arm_b=(-25, 0), f_foot=(9, 0), b_foot=(-9, 0), face="focus")


def hurt(i: int) -> Pose:
    return [
        Pose(lean=-6, squash=0.9, head_dx=-3, head_dy=2, arm_f=(-120, -150), arm_b=(-95, -110), f_foot=(4, 0), b_foot=(-8, 3), face="hurt"),
        Pose(lean=-8, squash=1.07, head_dx=-4, head_dy=1, arm_f=(-150, -170), arm_b=(-130, -160), f_foot=(3, 3), b_foot=(-9, 5), face="hurt"),
        Pose(lean=-4, squash=0.97, head_dx=-2, head_dy=3, arm_f=(-80, -120), arm_b=(-60, -100), f_foot=(5, 0), b_foot=(-7, 2), face="shock"),
    ][i]


def win(i: int) -> Pose:
    return [
        Pose(crouch=6, squash=0.88, arm_f=(30, 40), arm_b=(-30, -40), f_foot=(7, 0), b_foot=(-7, 0), face="happy"),
        Pose(squash=1.1, lean=1, arm_f=(165, 175), arm_b=(-165, -175), f_foot=(3, 8), b_foot=(-3, 9), face="happy"),
        Pose(squash=1.04, arm_f=(150, 168), arm_b=(-150, -168), f_foot=(6, 5), b_foot=(-6, 6), head_dy=-1, face="happy"),
        Pose(crouch=3, squash=0.95, arm_f=(120, 150), arm_b=(-120, -150), f_foot=(7, 0), b_foot=(-7, 0), face="happy"),
    ][i]


def lose(i: int) -> Pose:
    return Pose(crouch=5, lean=-2, head_dy=4, squash=0.95, arm_f=(8, 4), arm_b=(-8, -4), f_foot=(6, 0), b_foot=(-6, 0), face="hurt")


def _phases(startup: Pose, active: Pose, recover: Pose, swing: float) -> list[Pose]:
    """Anticipation (squash, strained face), strike (stretch, smear, fierce face), then ease back."""
    return [_with(startup, squash=startup.squash * 0.93, face="effort"),
            _with(active, squash=active.squash * 1.05, smear=swing, face="angry"),
            _with(recover, face="neutral")]


def jab(i: int) -> Pose:
    return _phases(
        Pose(lean=-2, arm_f=(-30, -10), arm_b=(30, 40), f_foot=(6, 0), b_foot=(-7, 0)),
        Pose(lean=5, arm_f=(88, 92), arm_b=(-20, 15), f_foot=(9, 0), b_foot=(-6, 0)),
        Pose(lean=2, arm_f=(60, 80), arm_b=(-12, 10), f_foot=(7, 0), b_foot=(-5, 0)), 34)[i]


def side(i: int) -> Pose:
    return _phases(
        Pose(lean=-5, crouch=2, arm_f=(-60, -110), arm_b=(-40, -90), f_foot=(4, 0), b_foot=(-10, 0)),
        Pose(lean=8, crouch=3, arm_f=(95, 100), arm_b=(30, 60), f_foot=(13, 0), b_foot=(-9, 0)),
        Pose(lean=4, crouch=2, arm_f=(70, 90), arm_b=(0, 20), f_foot=(10, 0), b_foot=(-7, 0)), 50)[i]


def up(i: int) -> Pose:
    return _phases(
        Pose(crouch=4, lean=-1, arm_f=(30, 10), arm_b=(-30, -10), f_foot=(6, 0), b_foot=(-6, 0)),
        Pose(lean=1, crouch=-1, arm_f=(172, 178), arm_b=(150, 170), f_foot=(4, 2), b_foot=(-4, 2), head_dy=1),
        Pose(lean=0, arm_f=(120, 150), arm_b=(100, 130), f_foot=(5, 0), b_foot=(-5, 0)), 46)[i]


def down(i: int) -> Pose:
    return _phases(
        Pose(crouch=5, lean=-2, arm_f=(40, 20), arm_b=(-40, -20), f_foot=(4, 0), b_foot=(-9, 0)),
        Pose(crouch=7, lean=5, arm_f=(60, 40), arm_b=(-60, -20), f_foot=(17, 1), b_foot=(-9, 0)),
        Pose(crouch=4, lean=2, arm_f=(30, 20), arm_b=(-30, -10), f_foot=(10, 0), b_foot=(-7, 0)), 22)[i]


def cast(i: int) -> Pose:
    p = _phases(
        Pose(lean=-3, arm_f=(40, 100), arm_b=(30, 110), f_foot=(6, 0), b_foot=(-7, 0)),
        Pose(lean=3, arm_f=(88, 90), arm_b=(84, 90), f_foot=(8, 0), b_foot=(-7, 0)),
        Pose(lean=1, arm_f=(70, 85), arm_b=(60, 80), f_foot=(7, 0), b_foot=(-6, 0)), 0)
    return _with(p[i], face=("focus", "shock", "happy")[i], smear=0)


def dash(i: int) -> Pose:
    return _phases(
        Pose(lean=-4, crouch=3, arm_f=(-50, -80), arm_b=(-70, -100), f_foot=(5, 0), b_foot=(-10, 0)),
        Pose(lean=11, crouch=5, arm_f=(100, 95), arm_b=(-60, -50), f_foot=(14, 1), b_foot=(-12, 5)),
        Pose(lean=5, crouch=3, arm_f=(60, 70), arm_b=(-20, -10), f_foot=(9, 0), b_foot=(-8, 0)), 40)[i]


def rise(i: int) -> Pose:
    return _phases(
        Pose(crouch=5, lean=-1, arm_f=(20, 10), arm_b=(-20, -10), f_foot=(5, 0), b_foot=(-5, 0)),
        Pose(crouch=-2, lean=1, arm_f=(170, 175), arm_b=(165, 175), f_foot=(2, 7), b_foot=(-2, 8), head_dy=1),
        Pose(lean=0, arm_f=(135, 160), arm_b=(125, 150), f_foot=(4, 5), b_foot=(-4, 6)), 30)[i]


def counter(i: int) -> Pose:
    return [
        Pose(crouch=4, lean=-2, arm_f=(70, 160), arm_b=(40, 170), f_foot=(7, 0), b_foot=(-7, 0), squash=0.94, face="focus"),
        Pose(crouch=5, lean=-1, arm_f=(75, 165), arm_b=(45, 175), f_foot=(8, 0), b_foot=(-8, 0), flash=True, face="angry"),
        Pose(crouch=2, lean=1, arm_f=(40, 80), arm_b=(0, 30), f_foot=(6, 0), b_foot=(-6, 0), squash=1.03, face="neutral"),
    ][i]


def buff(i: int) -> Pose:
    return [
        Pose(crouch=3, arm_f=(30, 10), arm_b=(-30, -10), f_foot=(6, 0), b_foot=(-6, 0), squash=0.93, face="effort"),
        Pose(crouch=-1, arm_f=(120, 150), arm_b=(-120, -150), f_foot=(8, 0), b_foot=(-8, 0), flash=True, squash=1.07, face="happy"),
        Pose(arm_f=(60, 90), arm_b=(-60, -90), f_foot=(7, 0), b_foot=(-7, 0), face="happy"),
    ][i]


_POSES = {"idle": idle, "run": run, "jump": jump, "fall": fall, "djump": djump, "land": land, "shield": shield,
          "duck": duck, "hurt": hurt, "win": win, "lose": lose, "jab": jab, "side": side, "up": up, "down": down,
          "cast": cast, "dash": dash, "rise": rise, "counter": counter, "buff": buff}
